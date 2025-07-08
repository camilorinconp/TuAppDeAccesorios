"""
Modelos de base de datos para auditoría
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from ..database import Base


class AuditLogEntry(Base):
    """Modelo de base de datos para entradas de auditoría"""
    __tablename__ = "audit_log_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    
    # Usuario y sesión
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Contexto de request
    request_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    
    # Detalles del evento
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Datos del evento
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    
    # Métricas
    response_code = Column(Integer, nullable=True)
    response_time = Column(Integer, nullable=True)  # en milisegundos
    
    # Flags
    is_sensitive = Column(Boolean, default=False)
    is_system_generated = Column(Boolean, default=False)
    
    # Índices para optimizar búsquedas
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user_id', 'user_id'),
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_ip_address', 'ip_address'),
        Index('idx_audit_severity', 'severity'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_compound', 'user_id', 'timestamp', 'event_type'),
    )