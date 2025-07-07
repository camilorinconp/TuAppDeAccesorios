# ==================================================================
# ROUTER DE AUDITORÍA - ENDPOINTS PARA CONSULTA DE AUDITORÍA
# ==================================================================

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_db, get_current_admin_user
from ..models.audit import AuditActionType, AuditSeverity
from ..services.audit_service import AuditQueryService
from ..logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/audit/user-activity/{user_id}", dependencies=[Depends(get_current_admin_user)])
def get_user_activity(
    user_id: int,
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la actividad de auditoría de un usuario específico
    Requiere permisos de administrador
    """
    try:
        activity = AuditQueryService.get_user_activity(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "activity_count": len(activity),
            "start_date": start_date,
            "end_date": end_date,
            "activity": [
                {
                    "id": log.id,
                    "action_type": log.action_type,
                    "severity": log.severity,
                    "timestamp": log.timestamp,
                    "description": log.description,
                    "table_name": log.table_name,
                    "record_id": log.record_id,
                    "ip_address": log.ip_address,
                    "endpoint": log.endpoint,
                    "execution_time_ms": log.execution_time_ms
                } for log in activity
            ]
        }
        
    except Exception as e:
        logger.error(
            "Error al obtener actividad de usuario",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener actividad de usuario"
        )


@router.get("/audit/security-alerts", dependencies=[Depends(get_current_admin_user)])
def get_security_alerts(
    resolved: Optional[bool] = Query(None, description="Filtrar por estado resuelto"),
    severity: Optional[AuditSeverity] = Query(None, description="Filtrar por severidad"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    """
    Obtiene alertas de seguridad del sistema
    Requiere permisos de administrador
    """
    try:
        alerts = AuditQueryService.get_security_alerts(
            db=db,
            resolved=resolved,
            severity=severity,
            limit=limit
        )
        
        return {
            "alerts_count": len(alerts),
            "filters": {
                "resolved": resolved,
                "severity": severity
            },
            "alerts": [
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp,
                    "description": alert.description,
                    "ip_address": alert.ip_address,
                    "username_attempt": alert.username_attempt,
                    "resolved": alert.resolved == "true",
                    "resolved_by": alert.resolved_by,
                    "resolved_at": alert.resolved_at,
                    "details": alert.details
                } for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(
            "Error al obtener alertas de seguridad",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener alertas de seguridad"
        )


@router.post("/audit/security-alerts/{alert_id}/resolve", dependencies=[Depends(get_current_admin_user)])
def resolve_security_alert(
    alert_id: int,
    resolution_notes: str = Query(..., description="Notas de resolución"),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Marca una alerta de seguridad como resuelta
    Requiere permisos de administrador
    """
    try:
        # Buscar la alerta
        alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alerta de seguridad no encontrada"
            )
        
        # Marcar como resuelta
        alert.resolved = "true"
        alert.resolved_by = current_user.id
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = resolution_notes
        
        db.commit()
        
        logger.info(
            "Alerta de seguridad resuelta",
            alert_id=alert_id,
            resolved_by=current_user.id,
            username=current_user.username
        )
        
        return {
            "message": "Alerta de seguridad marcada como resuelta",
            "alert_id": alert_id,
            "resolved_by": current_user.username,
            "resolved_at": alert.resolved_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error al resolver alerta de seguridad",
            alert_id=alert_id,
            error=str(e)
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al resolver alerta de seguridad"
        )


@router.get("/audit/failed-logins", dependencies=[Depends(get_current_admin_user)])
def get_failed_login_attempts(
    username: Optional[str] = Query(None, description="Filtrar por usuario"),
    ip_address: Optional[str] = Query(None, description="Filtrar por dirección IP"),
    hours: int = Query(24, ge=1, le=168, description="Horas hacia atrás para buscar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    """
    Obtiene intentos de login fallidos
    Requiere permisos de administrador
    """
    try:
        attempts = AuditQueryService.get_failed_login_attempts(
            db=db,
            username=username,
            ip_address=ip_address,
            hours=hours,
            limit=limit
        )
        
        return {
            "attempts_count": len(attempts),
            "time_window_hours": hours,
            "filters": {
                "username": username,
                "ip_address": ip_address
            },
            "attempts": [
                {
                    "id": attempt.id,
                    "timestamp": attempt.timestamp,
                    "username": attempt.username,
                    "ip_address": attempt.ip_address,
                    "failure_reason": attempt.failure_reason,
                    "user_agent": attempt.user_agent
                } for attempt in attempts
            ]
        }
        
    except Exception as e:
        logger.error(
            "Error al obtener intentos de login fallidos",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener intentos de login fallidos"
        )


@router.get("/audit/statistics", dependencies=[Depends(get_current_admin_user)])
def get_audit_statistics(
    hours: int = Query(24, ge=1, le=168, description="Horas hacia atrás para estadísticas"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas generales de auditoría
    Requiere permisos de administrador
    """
    try:
        stats = AuditQueryService.get_audit_statistics(db=db, hours=hours)
        
        return {
            "statistics": stats,
            "generated_at": datetime.utcnow(),
            "time_window_hours": hours
        }
        
    except Exception as e:
        logger.error(
            "Error al obtener estadísticas de auditoría",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas de auditoría"
        )


@router.get("/audit/events", dependencies=[Depends(get_current_admin_user)])
def get_audit_events(
    action_type: Optional[AuditActionType] = Query(None, description="Filtrar por tipo de acción"),
    severity: Optional[AuditSeverity] = Query(None, description="Filtrar por severidad"),
    table_name: Optional[str] = Query(None, description="Filtrar por tabla afectada"),
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    """
    Obtiene eventos de auditoría con filtros
    Requiere permisos de administrador
    """
    try:
        from ..models.audit import AuditLog
        
        query = db.query(AuditLog)
        
        # Aplicar filtros
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if table_name:
            query = query.filter(AuditLog.table_name == table_name)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        # Obtener resultados ordenados por fecha
        events = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return {
            "events_count": len(events),
            "filters": {
                "action_type": action_type,
                "severity": severity,
                "table_name": table_name,
                "start_date": start_date,
                "end_date": end_date
            },
            "events": [
                {
                    "id": event.id,
                    "action_type": event.action_type,
                    "severity": event.severity,
                    "timestamp": event.timestamp,
                    "description": event.description,
                    "user_id": event.user_id,
                    "username": event.username,
                    "user_role": event.user_role,
                    "table_name": event.table_name,
                    "record_id": event.record_id,
                    "ip_address": event.ip_address,
                    "endpoint": event.endpoint,
                    "request_method": event.request_method,
                    "execution_time_ms": event.execution_time_ms,
                    "old_values": event.old_values,
                    "new_values": event.new_values,
                    "additional_data": event.additional_data
                } for event in events
            ]
        }
        
    except Exception as e:
        logger.error(
            "Error al obtener eventos de auditoría",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener eventos de auditoría"
        )