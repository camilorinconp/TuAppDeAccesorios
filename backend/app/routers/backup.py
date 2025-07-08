"""
Endpoints para gestión de backups cifrados
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import get_current_admin_user
from ..security.backup_manager import backup_manager
from ..security.audit_logger import (
    audit_logger,
    AuditEventType,
    AuditSeverity,
    AuditContext,
    log_system_event
)
from ..security.endpoint_security import secure_endpoint, admin_required
from ..logging_config import get_secure_logger

router = APIRouter(prefix="/api/backup", tags=["Backup Management"])
logger = get_secure_logger(__name__)


class BackupCreateRequest(BaseModel):
    """Request para crear backup"""
    backup_type: str = "full"  # full, incremental, differential
    compress: bool = True
    encrypt: bool = True
    upload_to_s3: bool = True


class BackupRestoreRequest(BaseModel):
    """Request para restaurar backup"""
    backup_id: str
    download_from_s3: bool = True
    target_database: Optional[str] = None
    confirm_restore: bool = False


@router.post("/create")
@secure_endpoint(max_requests_per_hour=5, require_admin=True)
@admin_required
async def create_backup(
    request: Request,
    backup_request: BackupCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Crear backup de la base de datos"""
    try:
        # Crear contexto de auditoría
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log inicio de backup
        await log_system_event(
            event_type=AuditEventType.BACKUP_CREATE,
            action="backup_start",
            description=f"Starting {backup_request.backup_type} backup",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "backup_type": backup_request.backup_type,
                "compress": backup_request.compress,
                "encrypt": backup_request.encrypt,
                "upload_to_s3": backup_request.upload_to_s3
            }
        )
        
        # Crear backup
        metadata = await backup_manager.create_database_backup(
            backup_type=backup_request.backup_type,
            compress=backup_request.compress,
            encrypt=backup_request.encrypt,
            upload_to_s3=backup_request.upload_to_s3
        )
        
        if not metadata:
            # Log error
            await log_system_event(
                event_type=AuditEventType.ERROR_OCCURRED,
                action="backup_failed",
                description="Database backup creation failed",
                user_id=current_user.id,
                username=current_user.username,
                context=context
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create database backup"
            )
        
        # Log éxito
        await log_system_event(
            event_type=AuditEventType.BACKUP_CREATE,
            action="backup_success",
            description=f"Backup {metadata.backup_id} created successfully",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "backup_id": metadata.backup_id,
                "file_size": metadata.file_size,
                "s3_location": metadata.s3_location
            }
        )
        
        return {
            "success": True,
            "backup_id": metadata.backup_id,
            "timestamp": metadata.timestamp.isoformat(),
            "backup_type": metadata.backup_type,
            "file_size": metadata.file_size,
            "file_size_mb": round(metadata.file_size / (1024 * 1024), 2),
            "encrypted": metadata.encryption,
            "compressed": metadata.compression != "none",
            "s3_uploaded": bool(metadata.s3_location),
            "retention_days": metadata.retention_days,
            "created_by": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error creating backup"
        )


@router.get("/list")
@secure_endpoint(max_requests_per_hour=20, require_admin=True)
@admin_required
async def list_backups(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Listar backups disponibles"""
    try:
        # Obtener todos los backups
        all_backups = list(backup_manager.metadata.values())
        
        # Ordenar por timestamp descendente
        all_backups.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Aplicar paginación
        total_backups = len(all_backups)
        paginated_backups = all_backups[offset:offset + limit]
        
        # Serializar backups
        backup_list = []
        for backup in paginated_backups:
            backup_info = {
                "backup_id": backup.backup_id,
                "timestamp": backup.timestamp.isoformat(),
                "database_name": backup.database_name,
                "backup_type": backup.backup_type,
                "file_size": backup.file_size,
                "file_size_mb": round(backup.file_size / (1024 * 1024), 2),
                "compressed": backup.compression != "none",
                "encrypted": backup.encryption,
                "retention_days": backup.retention_days,
                "s3_location": backup.s3_location,
                "local_available": bool(backup.local_path and os.path.exists(backup.local_path)),
                "status": backup.status,
                "file_hash": backup.file_hash,
                "age_days": (datetime.utcnow() - backup.timestamp).days
            }
            backup_list.append(backup_info)
        
        # Crear contexto de auditoría
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log acceso a lista de backups
        await log_system_event(
            event_type=AuditEventType.DATA_EXPORT,
            action="backup_list",
            description="Backup list accessed",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "total_backups": total_backups,
                "returned_backups": len(backup_list),
                "offset": offset,
                "limit": limit
            }
        )
        
        return {
            "backups": backup_list,
            "total": total_backups,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_backups
        }
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving backup list"
        )


@router.get("/status")
@secure_endpoint(max_requests_per_hour=30, require_admin=True)
@admin_required
async def get_backup_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Obtener estado general del sistema de backups"""
    try:
        status_info = backup_manager.get_backup_status()
        
        # Agregar información adicional
        status_info.update({
            "last_backup": None,
            "next_scheduled_backup": None,  # Se implementaría con cron
            "backup_frequency": "manual",  # Se configuraría
            "storage_locations": {
                "local": bool(backup_manager.backup_dir),
                "s3": bool(backup_manager.s3_storage.s3_client)
            },
            "s3_bucket": backup_manager.s3_storage.bucket_name if backup_manager.s3_storage.s3_client else None
        })
        
        # Obtener último backup
        if backup_manager.metadata:
            latest_backup = max(
                backup_manager.metadata.values(),
                key=lambda x: x.timestamp
            )
            status_info["last_backup"] = {
                "backup_id": latest_backup.backup_id,
                "timestamp": latest_backup.timestamp.isoformat(),
                "type": latest_backup.backup_type,
                "size_mb": round(latest_backup.file_size / (1024 * 1024), 2)
            }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving backup status"
        )


@router.post("/restore")
@secure_endpoint(max_requests_per_hour=2, require_admin=True)
@admin_required
async def restore_backup(
    request: Request,
    restore_request: BackupRestoreRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Restaurar backup de base de datos"""
    try:
        # Validación de seguridad
        if not restore_request.confirm_restore:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database restore requires explicit confirmation (confirm_restore: true)"
            )
        
        # Verificar que el backup existe
        if restore_request.backup_id not in backup_manager.metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup not found: {restore_request.backup_id}"
            )
        
        backup_metadata = backup_manager.metadata[restore_request.backup_id]
        
        # Crear contexto de auditoría
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log inicio de restore (CRÍTICO)
        await log_system_event(
            event_type=AuditEventType.BACKUP_RESTORE,
            action="restore_start",
            description=f"Starting database restore from backup {restore_request.backup_id}",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "backup_id": restore_request.backup_id,
                "backup_timestamp": backup_metadata.timestamp.isoformat(),
                "target_database": restore_request.target_database,
                "download_from_s3": restore_request.download_from_s3
            }
        )
        
        # ADVERTENCIA CRÍTICA
        logger.critical(
            f"DATABASE RESTORE INITIATED",
            backup_id=restore_request.backup_id,
            admin_user=current_user.username,
            admin_id=current_user.id,
            ip_address=request.client.host,
            backup_timestamp=backup_metadata.timestamp.isoformat()
        )
        
        # Ejecutar restore
        success = await backup_manager.restore_backup(
            backup_id=restore_request.backup_id,
            download_from_s3=restore_request.download_from_s3,
            target_database=restore_request.target_database
        )
        
        if success:
            # Log éxito
            await log_system_event(
                event_type=AuditEventType.BACKUP_RESTORE,
                action="restore_success",
                description=f"Database restore completed successfully from backup {restore_request.backup_id}",
                user_id=current_user.id,
                username=current_user.username,
                context=context
            )
            
            logger.critical(
                f"DATABASE RESTORE COMPLETED SUCCESSFULLY",
                backup_id=restore_request.backup_id,
                admin_user=current_user.username
            )
            
            return {
                "success": True,
                "backup_id": restore_request.backup_id,
                "backup_timestamp": backup_metadata.timestamp.isoformat(),
                "restored_by": current_user.username,
                "restore_timestamp": datetime.utcnow().isoformat(),
                "target_database": restore_request.target_database,
                "message": "Database restored successfully. Application restart may be required."
            }
        else:
            # Log fallo
            await log_system_event(
                event_type=AuditEventType.ERROR_OCCURRED,
                action="restore_failed",
                description=f"Database restore failed for backup {restore_request.backup_id}",
                user_id=current_user.id,
                username=current_user.username,
                context=context
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database restore failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during backup restore"
        )


@router.delete("/cleanup")
@secure_endpoint(max_requests_per_hour=3, require_admin=True)
@admin_required
async def cleanup_old_backups(
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Limpiar backups antiguos según política de retención"""
    try:
        # Crear contexto de auditoría
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log inicio de limpieza
        await log_system_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGE,
            action="backup_cleanup_start",
            description="Starting backup cleanup",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "retention_days": backup_manager.retention_days,
                "force": force
            }
        )
        
        # Ejecutar limpieza
        cleanup_result = await backup_manager.cleanup_old_backups()
        
        # Log resultado
        await log_system_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGE,
            action="backup_cleanup_complete",
            description="Backup cleanup completed",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata=cleanup_result
        )
        
        return {
            "success": True,
            "cleaned_up": cleanup_result,
            "retention_days": backup_manager.retention_days,
            "cleaned_by": current_user.username,
            "cleanup_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during backup cleanup"
        )


@router.get("/download/{backup_id}")
@secure_endpoint(max_requests_per_hour=3, require_admin=True)
async def download_backup(
    request: Request,
    backup_id: str,
    from_s3: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Descargar backup (solo información, no archivo real por seguridad)"""
    try:
        # Verificar que el backup existe
        if backup_id not in backup_manager.metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup not found: {backup_id}"
            )
        
        backup_metadata = backup_manager.metadata[backup_id]
        
        # Crear contexto de auditoría
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log acceso de descarga (CRÍTICO)
        await log_system_event(
            event_type=AuditEventType.DATA_EXPORT,
            action="backup_download_info",
            description=f"Backup download information accessed: {backup_id}",
            user_id=current_user.id,
            username=current_user.username,
            context=context,
            metadata={
                "backup_id": backup_id,
                "from_s3": from_s3,
                "backup_size": backup_metadata.file_size
            }
        )
        
        # Por seguridad, no permitir descarga directa
        # En su lugar, proporcionar información para descarga manual
        download_info = {
            "backup_id": backup_id,
            "timestamp": backup_metadata.timestamp.isoformat(),
            "file_size": backup_metadata.file_size,
            "file_size_mb": round(backup_metadata.file_size / (1024 * 1024), 2),
            "encrypted": backup_metadata.encryption,
            "compressed": backup_metadata.compression != "none",
            "download_instructions": {
                "local_path": backup_metadata.local_path if backup_metadata.local_path else None,
                "s3_location": backup_metadata.s3_location if backup_metadata.s3_location else None,
                "note": "For security reasons, direct download via API is not supported. Use secure file transfer methods."
            },
            "security_note": "This backup contains sensitive database information and should be handled according to data protection policies.",
            "accessed_by": current_user.username,
            "access_timestamp": datetime.utcnow().isoformat()
        }
        
        return download_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backup download info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving backup download information"
        )


@router.get("/health")
async def get_backup_health(request: Request):
    """Health check del sistema de backups"""
    try:
        health_data = {
            "backup_system_enabled": True,
            "local_storage_available": backup_manager.backup_dir.exists(),
            "s3_storage_available": bool(backup_manager.s3_storage.s3_client),
            "encryption_enabled": True,
            "retention_days": backup_manager.retention_days,
            "total_backups": len(backup_manager.metadata),
            "backup_directory": str(backup_manager.backup_dir),
            "s3_bucket": backup_manager.s3_storage.bucket_name,
            "status": "healthy"
        }
        
        # Verificar problemas
        issues = []
        
        if not backup_manager.backup_dir.exists():
            issues.append("Local backup directory not accessible")
        
        if not backup_manager.s3_storage.s3_client:
            issues.append("S3 storage not configured")
        
        if len(backup_manager.metadata) == 0:
            issues.append("No backups found")
        
        if issues:
            health_data["status"] = "warning"
            health_data["issues"] = issues
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting backup health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving backup health"
        )