# ==================================================================
# MODELOS DE AUDITORÍA - SEGUIMIENTO DE CAMBIOS EN BASE DE DATOS
# ==================================================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Enum,
    JSON,
    Boolean
)
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime
import enum


class AuditActionType(str, enum.Enum):
    """Tipos de acciones auditables"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    SEARCH = "SEARCH"
    SALE = "SALE"
    CONSIGNMENT = "CONSIGNMENT"


class AuditSeverity(str, enum.Enum):
    """Niveles de severidad para auditoría"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLog(Base):
    """Tabla principal de auditoría para todos los eventos del sistema"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Información del evento
    action_type = Column(Enum(AuditActionType), nullable=False, index=True)
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.LOW, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Información del usuario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String, nullable=True, index=True)
    user_role = Column(String, nullable=True)
    
    # Información de la sesión
    session_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    
    # Información del recurso afectado
    table_name = Column(String, nullable=True, index=True)
    record_id = Column(String, nullable=True, index=True)  # String para flexibilidad
    
    # Detalles del evento
    description = Column(Text, nullable=False)
    old_values = Column(JSON, nullable=True)  # Valores anteriores (para UPDATE/DELETE)
    new_values = Column(JSON, nullable=True)  # Valores nuevos (para CREATE/UPDATE)
    additional_data = Column(JSON, nullable=True)  # Datos adicionales específicos del evento
    
    # Metadatos
    endpoint = Column(String, nullable=True)
    request_method = Column(String, nullable=True)
    response_code = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    # Relaciones
    user = relationship("User", foreign_keys=[user_id])


class SecurityAlert(Base):
    """Tabla para alertas de seguridad críticas"""
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Información del evento
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.HIGH, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Información del origen
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    username_attempt = Column(String, nullable=True, index=True)
    
    # Detalles del evento
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Estado de la alerta
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relaciones
    resolver = relationship("User", foreign_keys=[resolved_by])


class LoginAttempt(Base):
    """Tabla específica para seguimiento de intentos de login"""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Información del intento
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    username = Column(String, nullable=False, index=True)
    success = Column(Boolean, nullable=False, index=True)
    
    # Información de la sesión
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Detalles del intento
    failure_reason = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Relaciones
    user = relationship("User", foreign_keys=[user_id])


# Índices compuestos para optimizar consultas de auditoría
Index('idx_audit_user_time', AuditLog.user_id, AuditLog.timestamp)
Index('idx_audit_action_time', AuditLog.action_type, AuditLog.timestamp)
Index('idx_audit_table_record', AuditLog.table_name, AuditLog.record_id)
Index('idx_audit_severity_time', AuditLog.severity, AuditLog.timestamp)
Index('idx_audit_ip_time', AuditLog.ip_address, AuditLog.timestamp)

Index('idx_security_type_time', SecurityAlert.alert_type, SecurityAlert.timestamp)
Index('idx_security_severity_resolved', SecurityAlert.severity, SecurityAlert.resolved)
Index('idx_security_ip_time', SecurityAlert.ip_address, SecurityAlert.timestamp)

Index('idx_login_username_time', LoginAttempt.username, LoginAttempt.timestamp)
Index('idx_login_success_time', LoginAttempt.success, LoginAttempt.timestamp)
Index('idx_login_ip_time', LoginAttempt.ip_address, LoginAttempt.timestamp)