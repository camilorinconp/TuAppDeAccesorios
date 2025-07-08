"""
Endpoints para gestión y consulta de auditoría
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import csv
import io
from fastapi.responses import StreamingResponse

from ..database import get_db
from ..auth import get_current_user
from ..dependencies import get_current_admin_user
from ..security.audit_logger import (
    audit_logger,
    AuditEventType,
    AuditSeverity,
    AuditContext,
    log_data_access,
    log_system_event
)
from ..security.endpoint_security import secure_endpoint, admin_required
from ..logging_config import get_secure_logger

router = APIRouter(prefix="/api/audit", tags=["Audit"])
logger = get_secure_logger(__name__)


@router.get("/trail")
@secure_endpoint(max_requests_per_hour=20, require_admin=True)
@admin_required
async def get_audit_trail(
    request: Request,
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Maximum number of records"),
    offset: int = Query(0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Obtener trail de auditoría con filtros"""
    try:
        # Validar event_type si se proporciona
        audit_event_type = None
        if event_type:
            try:
                audit_event_type = AuditEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        # Obtener trail de auditoría
        audit_trail = await audit_logger.get_audit_trail(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=audit_event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Crear contexto para auditar esta consulta
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log de acceso a auditoría
        await log_data_access(
            user_id=current_user.id,
            username=current_user.username,
            resource_type="audit",
            resource_id="trail",
            action="view",
            context=context,
            metadata={
                "filters": {
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "event_type": event_type,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "limit": limit,
                    "offset": offset
                },
                "records_returned": len(audit_trail)
            }
        )
        
        return {
            "audit_trail": audit_trail,
            "total_returned": len(audit_trail),
            "offset": offset,
            "limit": limit,
            "has_more": len(audit_trail) == limit,
            "filters": {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "event_type": event_type,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving audit trail"
        )


@router.get("/statistics")
@secure_endpoint(max_requests_per_hour=10, require_admin=True)
@admin_required
async def get_audit_statistics(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Obtener estadísticas de auditoría"""
    try:
        # Usar valores por defecto si no se proporcionan fechas
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        
        if not end_date:
            end_date = datetime.utcnow()
        
        # Obtener estadísticas
        stats = await audit_logger.get_audit_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Crear contexto para auditar esta consulta
        context = AuditContext(
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=request.url.path,
            method=request.method
        )
        
        # Log de acceso a estadísticas
        await log_data_access(
            user_id=current_user.id,
            username=current_user.username,
            resource_type="audit",
            resource_id="statistics",
            action="view",
            context=context,
            metadata={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            }
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting audit statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving audit statistics"
        )


@router.get("/events/types")
@secure_endpoint(max_requests_per_hour=30, require_admin=True)
@admin_required
async def get_event_types(
    request: Request,
    current_user = Depends(get_current_admin_user)
):
    """Obtener tipos de eventos disponibles para filtrado"""
    try:
        event_types = [
            {
                "value": event_type.value,
                "description": event_type.value.replace("_", " ").title()
            }
            for event_type in AuditEventType
        ]
        
        severities = [
            {
                "value": severity.value,
                "description": severity.value.title()
            }
            for severity in AuditSeverity
        ]
        
        return {
            "event_types": event_types,
            "severities": severities
        }
        
    except Exception as e:
        logger.error(f"Error getting event types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving event types"
        )


@router.get("/health")
async def get_audit_health(request: Request):
    """Health check del sistema de auditoría"""
    try:
        health_data = {
            "audit_enabled": audit_logger.enabled,
            "async_logging": audit_logger.async_logging,
            "buffer_size": len(audit_logger.log_buffer),
            "max_buffer_size": audit_logger.buffer_size,
            "retention_days": audit_logger.retention_days,
            "log_sensitive_data": audit_logger.log_sensitive_data,
            "status": "healthy"
        }
        
        # Verificar si el buffer está muy lleno
        if len(audit_logger.log_buffer) > audit_logger.buffer_size * 0.8:
            health_data["status"] = "warning"
            health_data["warning"] = "Audit buffer is getting full"
        
        # Verificar si está habilitado
        if not audit_logger.enabled:
            health_data["status"] = "disabled"
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting audit health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving audit health"
        )