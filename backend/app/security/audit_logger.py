"""
Sistema de auditoría completa para seguimiento de accesos y acciones
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from ..database import Base, get_db
from ..config import settings
from ..logging_config import get_secure_logger
from ..models.audit_models import AuditLogEntry

logger = get_secure_logger(__name__)

class AuditEventType(Enum):
    """Tipos de eventos de auditoría"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # Gestión de usuarios
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_CHANGE = "user_role_change"
    USER_STATUS_CHANGE = "user_status_change"
    
    # Gestión de productos
    PRODUCT_CREATE = "product_create"
    PRODUCT_UPDATE = "product_update"
    PRODUCT_DELETE = "product_delete"
    PRODUCT_VIEW = "product_view"
    PRODUCT_SEARCH = "product_search"
    
    # Operaciones POS
    SALE_CREATE = "sale_create"
    SALE_UPDATE = "sale_update"
    SALE_DELETE = "sale_delete"
    SALE_REFUND = "sale_refund"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_CLEAR = "cart_clear"
    
    # Inventario
    INVENTORY_UPDATE = "inventory_update"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"
    INVENTORY_TRANSFER = "inventory_transfer"
    
    # Distribuidores
    DISTRIBUTOR_CREATE = "distributor_create"
    DISTRIBUTOR_UPDATE = "distributor_update"
    DISTRIBUTOR_DELETE = "distributor_delete"
    
    # Sistema
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    CACHE_CLEAR = "cache_clear"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    
    # Seguridad
    SECURITY_ALERT = "security_alert"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BLOCKED_IP = "blocked_ip"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # Acceso a datos
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    REPORT_GENERATE = "report_generate"
    
    # Errores
    ERROR_OCCURRED = "error_occurred"
    EXCEPTION_RAISED = "exception_raised"


class AuditSeverity(Enum):
    """Niveles de severidad de auditoría"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditContext:
    """Contexto adicional para eventos de auditoría"""
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    response_code: Optional[int] = None
    response_time: Optional[float] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


# AuditLogEntry model is imported from models.audit_models


class AuditLogger:
    """Sistema de auditoría completo"""
    
    def __init__(self):
        self.enabled = settings.audit_enabled if hasattr(settings, 'audit_enabled') else True
        self.retention_days = getattr(settings, 'audit_retention_days', 365)
        self.log_sensitive_data = getattr(settings, 'audit_log_sensitive_data', False)
        self.async_logging = getattr(settings, 'audit_async_logging', True)
        
        # Buffer para logging asíncrono
        self.log_buffer = []
        self.buffer_size = 100
        self.flush_interval = 30  # segundos
        
        # Configuración de eventos sensibles
        self.sensitive_events = {
            AuditEventType.LOGIN,
            AuditEventType.LOGIN_FAILED,
            AuditEventType.PASSWORD_CHANGE,
            AuditEventType.USER_DELETE,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.DATA_EXPORT,
            AuditEventType.BACKUP_CREATE,
            AuditEventType.BACKUP_RESTORE
        }
        
        # Configuración de campos sensibles
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'credential',
            'authorization', 'cookie', 'session', 'ssn', 'credit_card'
        }
        
        # Iniciar flush automático si está habilitado
        if self.async_logging:
            asyncio.create_task(self._periodic_flush())
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizar datos sensibles"""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Verificar si el campo es sensible
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                if self.log_sensitive_data:
                    sanitized[key] = value
                else:
                    sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _should_log_event(self, event_type: AuditEventType, severity: AuditSeverity) -> bool:
        """Determinar si se debe registrar el evento"""
        if not self.enabled:
            return False
            
        # Siempre registrar eventos críticos
        if severity == AuditSeverity.CRITICAL:
            return True
            
        # Configuración específica por tipo de evento
        if hasattr(settings, 'audit_event_filters'):
            filters = settings.audit_event_filters
            if event_type.value in filters:
                return filters[event_type.value]
        
        return True
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        action: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        context: Optional[AuditContext] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ):
        """Registrar evento de auditoría"""
        
        if not self._should_log_event(event_type, severity):
            return
        
        # Sanitizar datos sensibles
        sanitized_old = self._sanitize_data(old_values) if old_values else None
        sanitized_new = self._sanitize_data(new_values) if new_values else None
        sanitized_metadata = self._sanitize_data(event_metadata) if event_metadata else None
        
        # Crear entrada de auditoría
        audit_entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            event_type=event_type.value,
            severity=severity.value,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            action=action,
            description=description,
            old_values=sanitized_old,
            new_values=sanitized_new,
            event_metadata=sanitized_metadata,
            is_sensitive=event_type in self.sensitive_events,
            is_system_generated=user_id is None
        )
        
        # Agregar contexto si está disponible
        if context:
            audit_entry.request_id = context.request_id
            audit_entry.session_id = context.session_id
            audit_entry.ip_address = context.ip_address
            audit_entry.user_agent = context.user_agent
            audit_entry.endpoint = context.endpoint
            audit_entry.method = context.method
            audit_entry.response_code = context.response_code
            audit_entry.response_time = int(context.response_time * 1000) if context.response_time else None
        
        # Logging asíncrono vs síncrono
        if self.async_logging:
            self.log_buffer.append(audit_entry)
            
            # Flush si el buffer está lleno o es evento crítico
            if len(self.log_buffer) >= self.buffer_size or severity == AuditSeverity.CRITICAL:
                await self._flush_buffer(db)
        else:
            await self._write_to_database(audit_entry, db)
        
        # Log inmediato para eventos críticos
        if severity == AuditSeverity.CRITICAL:
            logger.critical(
                f"AUDIT: {event_type.value}",
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                description=description,
                ip_address=context.ip_address if context else None,
                endpoint=context.endpoint if context else None
            )
    
    async def _write_to_database(self, audit_entry: AuditLogEntry, db: Optional[Session] = None):
        """Escribir entrada de auditoría a la base de datos"""
        if not db:
            # Obtener sesión de base de datos
            db = next(get_db())
        
        try:
            db.add(audit_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error writing audit log to database: {e}")
            db.rollback()
            
            # Fallback a logging regular
            logger.warning(
                f"AUDIT_FALLBACK: {audit_entry.event_type}",
                user_id=audit_entry.user_id,
                username=audit_entry.username,
                resource_type=audit_entry.resource_type,
                resource_id=audit_entry.resource_id,
                description=audit_entry.description,
                severity=audit_entry.severity
            )
        finally:
            db.close()
    
    async def _flush_buffer(self, db: Optional[Session] = None):
        """Flush del buffer de auditoría"""
        if not self.log_buffer:
            return
        
        if not db:
            db = next(get_db())
        
        try:
            # Escribir todas las entradas en batch
            db.add_all(self.log_buffer)
            db.commit()
            
            logger.debug(f"Flushed {len(self.log_buffer)} audit entries to database")
            self.log_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing audit buffer: {e}")
            db.rollback()
            
            # Fallback a logging individual
            for entry in self.log_buffer:
                logger.warning(
                    f"AUDIT_FALLBACK: {entry.event_type}",
                    user_id=entry.user_id,
                    username=entry.username,
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    description=entry.description,
                    severity=entry.severity
                )
            
            self.log_buffer.clear()
        finally:
            db.close()
    
    async def _periodic_flush(self):
        """Flush periódico del buffer"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.log_buffer:
                    await self._flush_buffer()
            except Exception as e:
                logger.error(f"Error in periodic audit flush: {e}")
    
    async def cleanup_old_logs(self, days_to_keep: Optional[int] = None):
        """Limpiar logs antiguos"""
        days_to_keep = days_to_keep or self.retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        db = next(get_db())
        try:
            # Eliminar entradas antiguas
            deleted_count = db.query(AuditLogEntry).filter(
                AuditLogEntry.timestamp < cutoff_date
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old audit log entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up audit logs: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    async def get_audit_trail(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtener trail de auditoría con filtros"""
        
        db = next(get_db())
        try:
            query = db.query(AuditLogEntry)
            
            # Aplicar filtros
            if user_id:
                query = query.filter(AuditLogEntry.user_id == user_id)
            
            if resource_type:
                query = query.filter(AuditLogEntry.resource_type == resource_type)
            
            if resource_id:
                query = query.filter(AuditLogEntry.resource_id == str(resource_id))
            
            if event_type:
                query = query.filter(AuditLogEntry.event_type == event_type.value)
            
            if start_date:
                query = query.filter(AuditLogEntry.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditLogEntry.timestamp <= end_date)
            
            # Ordenar por timestamp descendente
            query = query.order_by(AuditLogEntry.timestamp.desc())
            
            # Aplicar paginación
            entries = query.offset(offset).limit(limit).all()
            
            # Convertir a diccionarios
            result = []
            for entry in entries:
                entry_dict = {
                    'id': str(entry.id),
                    'timestamp': entry.timestamp.isoformat(),
                    'event_type': entry.event_type,
                    'severity': entry.severity,
                    'user_id': entry.user_id,
                    'username': entry.username,
                    'session_id': entry.session_id,
                    'request_id': entry.request_id,
                    'ip_address': entry.ip_address,
                    'user_agent': entry.user_agent,
                    'endpoint': entry.endpoint,
                    'method': entry.method,
                    'resource_type': entry.resource_type,
                    'resource_id': entry.resource_id,
                    'action': entry.action,
                    'description': entry.description,
                    'old_values': entry.old_values,
                    'new_values': entry.new_values,
                    'event_metadata': entry.event_metadata,
                    'response_code': entry.response_code,
                    'response_time': entry.response_time,
                    'is_sensitive': entry.is_sensitive,
                    'is_system_generated': entry.is_system_generated
                }
                result.append(entry_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
        finally:
            db.close()
    
    async def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtener estadísticas de auditoría"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        
        if not end_date:
            end_date = datetime.utcnow()
        
        db = next(get_db())
        try:
            base_query = db.query(AuditLogEntry).filter(
                AuditLogEntry.timestamp >= start_date,
                AuditLogEntry.timestamp <= end_date
            )
            
            # Estadísticas básicas
            total_events = base_query.count()
            
            # Eventos por tipo
            event_counts = {}
            for event_type in AuditEventType:
                count = base_query.filter(AuditLogEntry.event_type == event_type.value).count()
                if count > 0:
                    event_counts[event_type.value] = count
            
            # Eventos por severidad
            severity_counts = {}
            for severity in AuditSeverity:
                count = base_query.filter(AuditLogEntry.severity == severity.value).count()
                if count > 0:
                    severity_counts[severity.value] = count
            
            # Top usuarios por actividad
            from sqlalchemy import func
            top_users = db.query(
                AuditLogEntry.user_id,
                AuditLogEntry.username,
                func.count(AuditLogEntry.id).label('event_count')
            ).filter(
                AuditLogEntry.timestamp >= start_date,
                AuditLogEntry.timestamp <= end_date,
                AuditLogEntry.user_id.isnot(None)
            ).group_by(
                AuditLogEntry.user_id,
                AuditLogEntry.username
            ).order_by(
                func.count(AuditLogEntry.id).desc()
            ).limit(10).all()
            
            # Top IPs por actividad
            top_ips = db.query(
                AuditLogEntry.ip_address,
                func.count(AuditLogEntry.id).label('event_count')
            ).filter(
                AuditLogEntry.timestamp >= start_date,
                AuditLogEntry.timestamp <= end_date,
                AuditLogEntry.ip_address.isnot(None)
            ).group_by(
                AuditLogEntry.ip_address
            ).order_by(
                func.count(AuditLogEntry.id).desc()
            ).limit(10).all()
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_events': total_events,
                'events_by_type': event_counts,
                'events_by_severity': severity_counts,
                'top_users': [
                    {
                        'user_id': user.user_id,
                        'username': user.username,
                        'event_count': user.event_count
                    }
                    for user in top_users
                ],
                'top_ips': [
                    {
                        'ip_address': ip.ip_address,
                        'event_count': ip.event_count
                    }
                    for ip in top_ips
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {}
        finally:
            db.close()


# Instancia global
audit_logger = AuditLogger()


# Funciones helper para eventos comunes
async def log_user_login(user_id: int, username: str, context: AuditContext, success: bool = True):
    """Log de login de usuario"""
    event_type = AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED
    severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
    
    await audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        username=username,
        action="login_attempt",
        description=f"User {'successful' if success else 'failed'} login attempt",
        context=context
    )


async def log_user_logout(user_id: int, username: str, context: AuditContext):
    """Log de logout de usuario"""
    await audit_logger.log_event(
        event_type=AuditEventType.LOGOUT,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=username,
        action="logout",
        description="User logout",
        context=context
    )


async def log_data_access(
    user_id: int,
    username: str,
    resource_type: str,
    resource_id: Union[str, int],
    action: str,
    context: AuditContext,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None
):
    """Log de acceso a datos"""
    event_mapping = {
        'create': AuditEventType.USER_CREATE if resource_type == 'user' else AuditEventType.PRODUCT_CREATE,
        'update': AuditEventType.USER_UPDATE if resource_type == 'user' else AuditEventType.PRODUCT_UPDATE,
        'delete': AuditEventType.USER_DELETE if resource_type == 'user' else AuditEventType.PRODUCT_DELETE,
        'view': AuditEventType.PRODUCT_VIEW,
        'search': AuditEventType.PRODUCT_SEARCH
    }
    
    event_type = event_mapping.get(action, AuditEventType.USER_CREATE)
    severity = AuditSeverity.WARNING if action == 'delete' else AuditSeverity.INFO
    
    await audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        username=username,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        description=f"{action.capitalize()} {resource_type} {resource_id}",
        old_values=old_values,
        new_values=new_values,
        context=context
    )


async def log_security_event(
    event_type: AuditEventType,
    severity: AuditSeverity,
    description: str,
    context: AuditContext,
    event_metadata: Optional[Dict] = None
):
    """Log de eventos de seguridad"""
    await audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        description=description,
        context=context,
        event_metadata=event_metadata
    )


async def log_system_event(
    event_type: AuditEventType,
    action: str,
    description: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    context: Optional[AuditContext] = None,
    event_metadata: Optional[Dict] = None
):
    """Log de eventos del sistema"""
    await audit_logger.log_event(
        event_type=event_type,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=username,
        action=action,
        description=description,
        context=context,
        event_metadata=event_metadata
    )


# Context manager para auditoría automática
@asynccontextmanager
async def audit_context(
    event_type: AuditEventType,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[Union[str, int]] = None,
    context: Optional[AuditContext] = None
):
    """Context manager para auditoría automática de operaciones"""
    start_time = datetime.utcnow()
    
    try:
        yield
        
        # Log de éxito
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        if context:
            context.response_time = response_time
            context.response_code = 200
        
        await audit_logger.log_event(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            action="operation_success",
            description=f"Operation {event_type.value} completed successfully",
            context=context
        )
        
    except Exception as e:
        # Log de error
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        if context:
            context.response_time = response_time
            context.response_code = 500
        
        await audit_logger.log_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            action="operation_failed",
            description=f"Operation {event_type.value} failed: {str(e)}",
            context=context,
            event_metadata={"error_type": type(e).__name__, "error_message": str(e)}
        )
        
        raise