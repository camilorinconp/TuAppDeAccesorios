"""
Sistema de backup automático cifrado para TuAppDeAccesorios
"""
import os
import gzip
import shutil
import subprocess
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import asyncio
import aiofiles
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


@dataclass
class BackupMetadata:
    """Metadatos del backup"""
    backup_id: str
    timestamp: datetime
    database_name: str
    backup_type: str  # full, incremental, differential
    compression: str  # gzip, none
    encryption: bool
    file_size: int
    file_hash: str
    retention_days: int
    s3_location: Optional[str] = None
    local_path: Optional[str] = None
    status: str = "created"  # created, uploaded, verified, expired, deleted


class BackupEncryption:
    """Gestor de cifrado para backups"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        
    def _derive_key(self, salt: bytes) -> bytes:
        """Derivar clave de cifrado usando PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key))
    
    def encrypt_file(self, input_path: str, output_path: str) -> Dict[str, str]:
        """Cifrar archivo"""
        # Generar salt aleatorio
        salt = os.urandom(16)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        # Cifrar archivo
        with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            # Escribir salt al inicio del archivo
            outfile.write(salt)
            
            # Cifrar y escribir datos en chunks
            while True:
                chunk = infile.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                
                encrypted_chunk = fernet.encrypt(chunk)
                outfile.write(len(encrypted_chunk).to_bytes(4, byteorder='big'))
                outfile.write(encrypted_chunk)
        
        # Calcular hash del archivo cifrado
        file_hash = self._calculate_file_hash(output_path)
        
        return {
            "encrypted_file": output_path,
            "salt": base64.b64encode(salt).decode(),
            "file_hash": file_hash
        }
    
    def decrypt_file(self, input_path: str, output_path: str, salt_b64: str) -> bool:
        """Descifrar archivo"""
        try:
            salt = base64.b64decode(salt_b64.encode())
            key = self._derive_key(salt)
            fernet = Fernet(key)
            
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                # Leer y validar salt
                file_salt = infile.read(16)
                if file_salt != salt:
                    raise ValueError("Salt mismatch - archivo corrupto o clave incorrecta")
                
                # Descifrar datos
                while True:
                    # Leer tamaño del chunk
                    size_bytes = infile.read(4)
                    if not size_bytes:
                        break
                    
                    chunk_size = int.from_bytes(size_bytes, byteorder='big')
                    encrypted_chunk = infile.read(chunk_size)
                    
                    if not encrypted_chunk:
                        break
                    
                    decrypted_chunk = fernet.decrypt(encrypted_chunk)
                    outfile.write(decrypted_chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"Error decrypting file: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcular hash SHA256 del archivo"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class S3BackupStorage:
    """Gestor de almacenamiento en S3"""
    
    def __init__(self):
        self.bucket_name = getattr(settings, 'backup_s3_bucket', None)
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        self.s3_client = None
        if all([self.bucket_name, self.aws_access_key, self.aws_secret_key]):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                # Verificar acceso
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"S3 backup storage initialized: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
    
    def upload_backup(self, local_path: str, s3_key: str, metadata: Dict[str, str] = None) -> bool:
        """Subir backup a S3"""
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False
        
        try:
            # Configurar metadatos
            upload_metadata = {
                'ContentType': 'application/octet-stream',
                'ServerSideEncryption': 'AES256'
            }
            
            if metadata:
                upload_metadata['Metadata'] = metadata
            
            # Subir archivo
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=upload_metadata
            )
            
            logger.info(f"Backup uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload backup to S3: {e}")
            return False
    
    def download_backup(self, s3_key: str, local_path: str) -> bool:
        """Descargar backup desde S3"""
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False
        
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Backup downloaded from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download backup from S3: {e}")
            return False
    
    def list_backups(self, prefix: str = "") -> List[Dict[str, Any]]:
        """Listar backups en S3"""
        if not self.s3_client:
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            backups = []
            for obj in response.get('Contents', []):
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list S3 backups: {e}")
            return []
    
    def delete_backup(self, s3_key: str) -> bool:
        """Eliminar backup de S3"""
        if not self.s3_client:
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Backup deleted from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup from S3: {e}")
            return False


class DatabaseBackupManager:
    """Gestor de backups de base de datos"""
    
    def __init__(self):
        self.backup_dir = Path(getattr(settings, 'backup_local_dir', './backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption = BackupEncryption(
            getattr(settings, 'backup_encryption_key', 'default-key-change-in-production')
        )
        
        self.s3_storage = S3BackupStorage()
        self.retention_days = getattr(settings, 'backup_retention_days', 30)
        
        # Archivo de metadatos
        self.metadata_file = self.backup_dir / 'backup_metadata.json'
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, BackupMetadata]:
        """Cargar metadatos de backups"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            metadata = {}
            for backup_id, meta_dict in data.items():
                # Convertir timestamp string a datetime
                meta_dict['timestamp'] = datetime.fromisoformat(meta_dict['timestamp'])
                metadata[backup_id] = BackupMetadata(**meta_dict)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error loading backup metadata: {e}")
            return {}
    
    def _save_metadata(self):
        """Guardar metadatos de backups"""
        try:
            data = {}
            for backup_id, metadata in self.metadata.items():
                meta_dict = asdict(metadata)
                # Convertir datetime a string
                meta_dict['timestamp'] = metadata.timestamp.isoformat()
                data[backup_id] = meta_dict
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving backup metadata: {e}")
    
    async def create_database_backup(
        self,
        backup_type: str = "full",
        compress: bool = True,
        encrypt: bool = True,
        upload_to_s3: bool = True
    ) -> Optional[BackupMetadata]:
        """Crear backup de la base de datos"""
        
        backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.utcnow()
        
        try:
            # Determinar comando de backup según el tipo de base de datos
            if 'postgresql' in settings.database_url:
                backup_file = await self._create_postgres_backup(backup_id, backup_type)
            elif 'sqlite' in settings.database_url:
                backup_file = await self._create_sqlite_backup(backup_id)
            else:
                raise ValueError(f"Unsupported database type: {settings.database_url}")
            
            if not backup_file:
                return None
            
            # Comprimir si está habilitado
            compressed_file = backup_file
            if compress:
                compressed_file = await self._compress_file(backup_file)
                os.remove(backup_file)  # Eliminar archivo sin comprimir
            
            # Cifrar si está habilitado
            final_file = compressed_file
            encryption_info = {}
            if encrypt:
                encrypted_file = f"{compressed_file}.enc"
                encryption_info = self.encryption.encrypt_file(compressed_file, encrypted_file)
                os.remove(compressed_file)  # Eliminar archivo sin cifrar
                final_file = encrypted_file
            
            # Calcular tamaño y hash del archivo final
            file_size = os.path.getsize(final_file)
            file_hash = self.encryption._calculate_file_hash(final_file)
            
            # Crear metadatos
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=timestamp,
                database_name=self._get_database_name(),
                backup_type=backup_type,
                compression="gzip" if compress else "none",
                encryption=encrypt,
                file_size=file_size,
                file_hash=file_hash,
                retention_days=self.retention_days,
                local_path=str(final_file)
            )
            
            # Subir a S3 si está habilitado
            if upload_to_s3 and self.s3_storage.s3_client:
                s3_key = f"backups/{backup_id}/{os.path.basename(final_file)}"
                s3_metadata = {
                    'backup-id': backup_id,
                    'backup-type': backup_type,
                    'database': metadata.database_name,
                    'compressed': str(compress).lower(),
                    'encrypted': str(encrypt).lower(),
                    'retention-days': str(self.retention_days)
                }
                
                if encryption_info:
                    s3_metadata.update({
                        'encryption-salt': encryption_info.get('salt', ''),
                        'file-hash': file_hash
                    })
                
                if self.s3_storage.upload_backup(final_file, s3_key, s3_metadata):
                    metadata.s3_location = f"s3://{self.s3_storage.bucket_name}/{s3_key}"
                    metadata.status = "uploaded"
            
            # Guardar metadatos
            self.metadata[backup_id] = metadata
            self._save_metadata()
            
            logger.info(
                f"Database backup created successfully",
                backup_id=backup_id,
                file_size=file_size,
                compressed=compress,
                encrypted=encrypt,
                s3_uploaded=bool(metadata.s3_location)
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return None
    
    async def _create_postgres_backup(self, backup_id: str, backup_type: str) -> Optional[str]:
        """Crear backup de PostgreSQL"""
        try:
            # Parsear URL de conexión
            db_url = settings.database_url
            if '@' in db_url:
                # Formato: postgresql://user:pass@host:port/db
                auth_part, host_part = db_url.split('@')
                user_pass = auth_part.split('://')[-1]
                
                if ':' in user_pass:
                    username, password = user_pass.split(':', 1)
                else:
                    username = user_pass
                    password = ""
                
                if ':' in host_part:
                    host, port_db = host_part.split(':', 1)
                    if '/' in port_db:
                        port, database = port_db.split('/', 1)
                    else:
                        port = port_db
                        database = "postgres"
                else:
                    host = host_part.split('/')[0]
                    database = host_part.split('/')[-1] if '/' in host_part else "postgres"
                    port = "5432"
            else:
                raise ValueError("Invalid PostgreSQL URL format")
            
            # Archivo de salida
            backup_file = self.backup_dir / f"{backup_id}.sql"
            
            # Configurar variables de entorno para pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Comando pg_dump
            cmd = [
                'pg_dump',
                f'--host={host}',
                f'--port={port}',
                f'--username={username}',
                f'--dbname={database}',
                '--verbose',
                '--no-password',
                '--format=custom' if backup_type == 'full' else '--format=plain',
                f'--file={backup_file}'
            ]
            
            # Ejecutar comando
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"PostgreSQL backup completed: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"pg_dump failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating PostgreSQL backup: {e}")
            return None
    
    async def _create_sqlite_backup(self, backup_id: str) -> Optional[str]:
        """Crear backup de SQLite"""
        try:
            # Extraer path de la base de datos
            db_path = settings.database_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_path):
                logger.error(f"SQLite database not found: {db_path}")
                return None
            
            # Archivo de salida
            backup_file = self.backup_dir / f"{backup_id}.db"
            
            # Copiar archivo de base de datos
            shutil.copy2(db_path, backup_file)
            
            logger.info(f"SQLite backup completed: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Error creating SQLite backup: {e}")
            return None
    
    async def _compress_file(self, file_path: str) -> str:
        """Comprimir archivo con gzip"""
        compressed_path = f"{file_path}.gz"
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.info(f"File compressed: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"Error compressing file: {e}")
            return file_path
    
    def _get_database_name(self) -> str:
        """Obtener nombre de la base de datos"""
        db_url = settings.database_url
        
        if 'postgresql' in db_url:
            return db_url.split('/')[-1]
        elif 'sqlite' in db_url:
            return os.path.basename(db_url.replace('sqlite:///', ''))
        else:
            return "unknown"
    
    async def restore_backup(
        self,
        backup_id: str,
        download_from_s3: bool = True,
        target_database: Optional[str] = None
    ) -> bool:
        """Restaurar backup"""
        
        if backup_id not in self.metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        metadata = self.metadata[backup_id]
        
        try:
            # Descargar desde S3 si es necesario
            local_file = metadata.local_path
            if download_from_s3 and metadata.s3_location:
                s3_key = metadata.s3_location.split('/')[-2:]
                s3_key = '/'.join(s3_key)
                
                local_file = self.backup_dir / f"restore_{backup_id}"
                if not self.s3_storage.download_backup(s3_key, str(local_file)):
                    return False
            
            if not local_file or not os.path.exists(local_file):
                logger.error(f"Backup file not found: {local_file}")
                return False
            
            # Proceso de restauración inverso
            current_file = local_file
            
            # Descifrar si está cifrado
            if metadata.encryption:
                decrypted_file = f"{current_file}.decrypted"
                
                # Obtener salt desde metadatos de S3 o calcular
                salt_b64 = ""  # Necesitaríamos obtener esto de los metadatos
                
                if not self.encryption.decrypt_file(current_file, decrypted_file, salt_b64):
                    logger.error("Failed to decrypt backup file")
                    return False
                
                current_file = decrypted_file
            
            # Descomprimir si está comprimido
            if metadata.compression == "gzip":
                decompressed_file = current_file.replace('.gz', '').replace('.enc', '')
                
                with gzip.open(current_file, 'rb') as f_in:
                    with open(decompressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                current_file = decompressed_file
            
            # Restaurar base de datos
            if 'postgresql' in settings.database_url:
                success = await self._restore_postgres_backup(current_file, target_database)
            elif 'sqlite' in settings.database_url:
                success = await self._restore_sqlite_backup(current_file, target_database)
            else:
                logger.error("Unsupported database type for restore")
                success = False
            
            # Limpiar archivos temporales
            for temp_file in [local_file, current_file]:
                if temp_file != metadata.local_path and os.path.exists(temp_file):
                    os.remove(temp_file)
            
            if success:
                logger.info(f"Backup restored successfully: {backup_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    async def _restore_postgres_backup(self, backup_file: str, target_database: Optional[str]) -> bool:
        """Restaurar backup de PostgreSQL"""
        try:
            # Similar a create_postgres_backup pero con pg_restore
            db_url = settings.database_url
            # ... parsear URL ...
            
            # Comando pg_restore
            cmd = [
                'pg_restore',
                '--verbose',
                '--clean',
                '--no-acl',
                '--no-owner',
                f'--dbname={target_database or database}',
                backup_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error restoring PostgreSQL backup: {e}")
            return False
    
    async def _restore_sqlite_backup(self, backup_file: str, target_database: Optional[str]) -> bool:
        """Restaurar backup de SQLite"""
        try:
            target_path = target_database or settings.database_url.replace('sqlite:///', '')
            
            # Hacer backup del archivo actual
            if os.path.exists(target_path):
                backup_current = f"{target_path}.backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(target_path, backup_current)
            
            # Restaurar archivo
            shutil.copy2(backup_file, target_path)
            
            logger.info(f"SQLite backup restored to: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring SQLite backup: {e}")
            return False
    
    async def cleanup_old_backups(self) -> Dict[str, int]:
        """Limpiar backups antiguos"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        local_deleted = 0
        s3_deleted = 0
        
        backups_to_remove = []
        
        for backup_id, metadata in self.metadata.items():
            if metadata.timestamp < cutoff_date:
                # Eliminar archivo local
                if metadata.local_path and os.path.exists(metadata.local_path):
                    try:
                        os.remove(metadata.local_path)
                        local_deleted += 1
                        logger.info(f"Deleted local backup: {metadata.local_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete local backup: {e}")
                
                # Eliminar de S3
                if metadata.s3_location:
                    s3_key = metadata.s3_location.split('/')[-2:]
                    s3_key = '/'.join(s3_key)
                    
                    if self.s3_storage.delete_backup(s3_key):
                        s3_deleted += 1
                
                backups_to_remove.append(backup_id)
        
        # Actualizar metadatos
        for backup_id in backups_to_remove:
            del self.metadata[backup_id]
        
        self._save_metadata()
        
        logger.info(
            f"Backup cleanup completed",
            local_deleted=local_deleted,
            s3_deleted=s3_deleted,
            total_removed=len(backups_to_remove)
        )
        
        return {
            "local_deleted": local_deleted,
            "s3_deleted": s3_deleted,
            "total_removed": len(backups_to_remove)
        }
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Obtener estado de los backups"""
        now = datetime.utcnow()
        
        total_backups = len(self.metadata)
        total_size = sum(m.file_size for m in self.metadata.values())
        
        recent_backups = [
            m for m in self.metadata.values()
            if (now - m.timestamp).days <= 7
        ]
        
        oldest_backup = min(
            (m.timestamp for m in self.metadata.values()),
            default=now
        )
        
        return {
            "total_backups": total_backups,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "recent_backups_7d": len(recent_backups),
            "oldest_backup": oldest_backup.isoformat() if oldest_backup != now else None,
            "s3_enabled": bool(self.s3_storage.s3_client),
            "encryption_enabled": True,
            "retention_days": self.retention_days,
            "backup_directory": str(self.backup_dir)
        }


# Instancia global
backup_manager = DatabaseBackupManager()