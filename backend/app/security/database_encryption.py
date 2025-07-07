"""
Sistema de cifrado para datos sensibles en base de datos
"""
import os
import base64
import hashlib
from typing import Optional, Union, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import TypeDecorator, String, Text
import json

from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class DatabaseEncryption:
    """Gestor de cifrado para datos sensibles en base de datos"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._get_master_key()
        self._cipher_cache = {}
        
    def _get_master_key(self) -> str:
        """Obtener master key desde variables de entorno o Vault"""
        # Intentar obtener desde Vault primero
        try:
            from ..vault import get_vault_secret
            master_key = get_vault_secret('DATABASE_MASTER_KEY')
            if master_key:
                return master_key
        except ImportError:
            pass
        
        # Fallback a variable de entorno
        master_key = os.getenv('DATABASE_MASTER_KEY')
        if not master_key:
            # Generar clave temporal para desarrollo (NO usar en producción)
            if settings.environment.lower() == 'development':
                logger.warning("Using temporary master key for development")
                master_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            else:
                raise ValueError("DATABASE_MASTER_KEY must be set in production")
        
        return master_key
    
    def _derive_key(self, context: str, salt: Optional[bytes] = None) -> bytes:
        """Derivar clave específica para un contexto"""
        if salt is None:
            salt = hashlib.sha256(context.encode()).digest()[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return key
    
    def _get_cipher(self, context: str) -> Fernet:
        """Obtener cipher para un contexto específico"""
        if context not in self._cipher_cache:
            key = self._derive_key(context)
            self._cipher_cache[context] = Fernet(key)
        return self._cipher_cache[context]
    
    def encrypt(self, data: str, context: str = "default") -> str:
        """Cifrar datos"""
        if not data:
            return data
        
        try:
            cipher = self._get_cipher(context)
            encrypted_data = cipher.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt(self, encrypted_data: str, context: str = "default") -> str:
        """Descifrar datos"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            cipher = self._get_cipher(context)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = cipher.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> str:
        """Hash irreversible para datos sensibles (para búsquedas)"""
        if salt is None:
            salt = "tuapp_hash_salt"
        
        combined = f"{data}{salt}".encode('utf-8')
        return hashlib.sha256(combined).hexdigest()


# Instancia global
db_encryption = DatabaseEncryption()


# Tipos de columna con cifrado automático
class EncryptedType(TypeDecorator):
    """Tipo de columna que cifra automáticamente los datos"""
    
    impl = Text
    cache_ok = True
    
    def __init__(self, context: str = "default", **kwargs):
        self.context = context
        super().__init__(**kwargs)
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Cifrar al guardar en DB"""
        if value is None:
            return value
        
        if not isinstance(value, str):
            value = str(value)
        
        return db_encryption.encrypt(value, self.context)
    
    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """Descifrar al leer de DB"""
        if value is None:
            return value
        
        return db_encryption.decrypt(value, self.context)


class EncryptedJSON(TypeDecorator):
    """Tipo para cifrar datos JSON"""
    
    impl = Text
    cache_ok = True
    
    def __init__(self, context: str = "json", **kwargs):
        self.context = context
        super().__init__(**kwargs)
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Serializar y cifrar JSON"""
        if value is None:
            return value
        
        json_str = json.dumps(value)
        return db_encryption.encrypt(json_str, self.context)
    
    def process_result_value(self, value: Any, dialect) -> Any:
        """Descifrar y deserializar JSON"""
        if value is None:
            return value
        
        decrypted_str = db_encryption.decrypt(value, self.context)
        return json.loads(decrypted_str)


class HashedType(TypeDecorator):
    """Tipo para datos que se hashean irreversiblemente"""
    
    impl = String(64)  # SHA256 hash
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Hash al guardar"""
        if value is None:
            return value
        
        if not isinstance(value, str):
            value = str(value)
        
        return db_encryption.hash_sensitive_data(value)
    
    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """Retornar hash (no se puede revertir)"""
        return value


# Funciones helper para cifrado manual
def encrypt_sensitive_data(data: str, context: str = "manual") -> str:
    """Cifrar datos sensibles manualmente"""
    return db_encryption.encrypt(data, context)


def decrypt_sensitive_data(encrypted_data: str, context: str = "manual") -> str:
    """Descifrar datos sensibles manualmente"""
    return db_encryption.decrypt(encrypted_data, context)


def hash_for_search(data: str) -> str:
    """Hash para permitir búsquedas sin revelar datos"""
    return db_encryption.hash_sensitive_data(data)


# Funciones de utilidad para backups cifrados
def encrypt_backup_data(data: bytes, backup_key: Optional[str] = None) -> bytes:
    """Cifrar datos de backup"""
    if backup_key is None:
        backup_key = os.getenv('BACKUP_ENCRYPTION_KEY')
        if not backup_key:
            raise ValueError("BACKUP_ENCRYPTION_KEY must be set")
    
    # Usar clave específica para backups
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'backup_salt_tuapp_2024',
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(backup_key.encode()))
    cipher = Fernet(key)
    
    return cipher.encrypt(data)


def decrypt_backup_data(encrypted_data: bytes, backup_key: Optional[str] = None) -> bytes:
    """Descifrar datos de backup"""
    if backup_key is None:
        backup_key = os.getenv('BACKUP_ENCRYPTION_KEY')
        if not backup_key:
            raise ValueError("BACKUP_ENCRYPTION_KEY must be set")
    
    # Usar la misma clave que para cifrar
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'backup_salt_tuapp_2024',
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(backup_key.encode()))
    cipher = Fernet(key)
    
    return cipher.decrypt(encrypted_data)


# Funciones de rotación de claves
def rotate_encryption_key(new_master_key: str) -> bool:
    """Rotar master key (requiere re-cifrar todos los datos)"""
    try:
        # Esta función debe implementarse con cuidado en producción
        # Requiere:
        # 1. Descifrar todos los datos con la clave antigua
        # 2. Cifrar con la nueva clave
        # 3. Actualizar en base de datos
        # 4. Verificar integridad
        
        logger.warning("Key rotation initiated - this is a critical operation")
        
        # TODO: Implementar rotación completa
        # Por ahora, solo actualizar la instancia
        global db_encryption
        db_encryption = DatabaseEncryption(new_master_key)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during key rotation: {e}")
        return False


# Verificación de integridad
def verify_encryption_integrity() -> Dict[str, Any]:
    """Verificar que el cifrado funciona correctamente"""
    try:
        test_data = "test_encryption_data_123"
        
        # Test cifrado/descifrado básico
        encrypted = db_encryption.encrypt(test_data)
        decrypted = db_encryption.decrypt(encrypted)
        
        basic_test = test_data == decrypted
        
        # Test con diferentes contextos
        context_test = True
        for context in ["users", "products", "financial"]:
            enc = db_encryption.encrypt(test_data, context)
            dec = db_encryption.decrypt(enc, context)
            if test_data != dec:
                context_test = False
                break
        
        # Test hashing
        hash1 = db_encryption.hash_sensitive_data(test_data)
        hash2 = db_encryption.hash_sensitive_data(test_data)
        hash_test = hash1 == hash2  # Mismo input = mismo hash
        
        return {
            "basic_encryption": basic_test,
            "context_encryption": context_test,
            "hashing": hash_test,
            "overall_status": basic_test and context_test and hash_test
        }
        
    except Exception as e:
        logger.error(f"Encryption integrity check failed: {e}")
        return {
            "basic_encryption": False,
            "context_encryption": False,
            "hashing": False,
            "overall_status": False,
            "error": str(e)
        }