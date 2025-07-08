"""
Endpoints para monitoreo de seguridad
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..auth import get_current_user
from ..dependencies import get_current_admin_user
from ..security.security_monitor import security_monitor, SecurityEvent, ThreatType, AlertSeverity
from ..security.endpoint_security import secure_endpoint, admin_required
from ..logging_config import get_secure_logger

router = APIRouter(prefix="/api/security", tags=["Security Monitoring"])
logger = get_secure_logger(__name__)


@router.get("/dashboard")
@secure_endpoint(max_requests_per_hour=50, require_admin=True)
@admin_required
async def get_security_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Dashboard de seguridad con estadísticas principales"""
    try:
        stats = security_monitor.get_security_stats()
        
        # Agregar información adicional
        dashboard_data = {
            "summary": {
                "events_last_24h": stats["total_events_24h"],
                "events_last_hour": stats["total_events_1h"],
                "alerts_sent_today": stats["alerts_sent_today"],
                "active_monitoring_rules": stats["active_rules"],
                "notification_channels": stats["notification_handlers"]
            },
            "threat_breakdown_24h": stats["threats_24h"],
            "threat_breakdown_1h": stats["threats_1h"],
            "top_attackers": stats["top_attackers"],
            "security_status": _calculate_security_status(stats),
            "recent_alerts": _get_recent_alerts(),
            "system_health": {
                "monitor_running": security_monitor.running,
                "rules_enabled": len([r for r in security_monitor.alert_rules if r.enabled]),
                "total_rules": len(security_monitor.alert_rules)
            }
        }
        
        # Log acceso al dashboard
        logger.info(
            f"Security dashboard accessed",
            admin_user_id=current_user.id,
            client_ip=request.client.host
        )
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting security dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving security dashboard"
        )


@router.get("/events")
@secure_endpoint(max_requests_per_hour=30, require_admin=True)
@admin_required
async def get_security_events(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    threat_type: Optional[str] = None,
    severity: Optional[str] = None,
    source_ip: Optional[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Obtener eventos de seguridad con filtros"""
    try:
        # Filtrar eventos
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        filtered_events = []
        
        for event in security_monitor.events:
            if event.timestamp < cutoff_time:
                continue
            
            # Aplicar filtros
            if threat_type and event.event_type.value != threat_type:
                continue
            if severity and event.severity.value != severity:
                continue
            if source_ip and event.source_ip != source_ip:
                continue
            
            filtered_events.append(event)
        
        # Ordenar por timestamp descendente
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Aplicar paginación
        total_events = len(filtered_events)
        paginated_events = filtered_events[offset:offset + limit]
        
        # Serializar eventos
        serialized_events = []
        for event in paginated_events:
            serialized_events.append({
                "id": event.fingerprint or f"{event.timestamp.timestamp()}_{event.source_ip}",
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "source_ip": event.source_ip,
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "user_id": event.user_id,
                "details": event.details,
                "count": event.count
            })
        
        return {
            "events": serialized_events,
            "total": total_events,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_events,
            "filters_applied": {
                "threat_type": threat_type,
                "severity": severity,
                "source_ip": source_ip,
                "hours_back": hours_back
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting security events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving security events"
        )


@router.get("/threats/analysis")
@secure_endpoint(max_requests_per_hour=20, require_admin=True)
@admin_required
async def get_threat_analysis(
    request: Request,
    hours_back: int = 24,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Análisis detallado de amenazas"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        recent_events = [e for e in security_monitor.events if e.timestamp >= cutoff_time]
        
        # Análisis por IP
        ip_analysis = {}
        for event in recent_events:
            ip = event.source_ip
            if ip not in ip_analysis:
                ip_analysis[ip] = {
                    "total_events": 0,
                    "threat_types": set(),
                    "severity_counts": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                    "endpoints_targeted": set(),
                    "first_seen": event.timestamp,
                    "last_seen": event.timestamp,
                    "user_agents": set()
                }
            
            ip_data = ip_analysis[ip]
            ip_data["total_events"] += 1
            ip_data["threat_types"].add(event.event_type.value)
            ip_data["severity_counts"][event.severity.value] += 1
            ip_data["endpoints_targeted"].add(event.endpoint)
            ip_data["user_agents"].add(event.user_agent)
            
            if event.timestamp < ip_data["first_seen"]:
                ip_data["first_seen"] = event.timestamp
            if event.timestamp > ip_data["last_seen"]:
                ip_data["last_seen"] = event.timestamp
        
        # Convertir sets a listas para JSON serialization
        for ip_data in ip_analysis.values():
            ip_data["threat_types"] = list(ip_data["threat_types"])
            ip_data["endpoints_targeted"] = list(ip_data["endpoints_targeted"])
            ip_data["user_agents"] = list(ip_data["user_agents"])
            ip_data["first_seen"] = ip_data["first_seen"].isoformat()
            ip_data["last_seen"] = ip_data["last_seen"].isoformat()
        
        # Análisis de patrones temporales
        hourly_counts = {}
        for event in recent_events:
            hour = event.timestamp.replace(minute=0, second=0, microsecond=0)
            hour_key = hour.isoformat()
            if hour_key not in hourly_counts:
                hourly_counts[hour_key] = {"total": 0, "by_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0}}
            
            hourly_counts[hour_key]["total"] += 1
            hourly_counts[hour_key]["by_severity"][event.severity.value] += 1
        
        # Top amenazas
        threat_counts = {}
        for event in recent_events:
            threat_type = event.event_type.value
            if threat_type not in threat_counts:
                threat_counts[threat_type] = 0
            threat_counts[threat_type] += 1
        
        top_threats = sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "analysis_period": {
                "hours_back": hours_back,
                "start_time": cutoff_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "total_events": len(recent_events)
            },
            "ip_analysis": ip_analysis,
            "temporal_patterns": hourly_counts,
            "top_threats": top_threats,
            "risk_assessment": _calculate_risk_assessment(recent_events, ip_analysis)
        }
        
    except Exception as e:
        logger.error(f"Error in threat analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing threat analysis"
        )


@router.post("/block-ip")
@secure_endpoint(max_requests_per_hour=10, require_admin=True)
@admin_required
async def block_ip_address(
    request: Request,
    ip_address: str,
    duration_hours: int = 24,
    reason: str = "manual_block",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Bloquear dirección IP manualmente"""
    try:
        from ..security.advanced_rate_limiter import advanced_rate_limiter
        
        # Validar IP
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address format"
            )
        
        # Bloquear IP
        duration_seconds = duration_hours * 3600
        advanced_rate_limiter.block_identifier(
            f"ip:{ip_address}",
            duration_seconds,
            reason
        )
        
        # Log de auditoría
        logger.critical(
            f"IP address manually blocked",
            blocked_ip=ip_address,
            duration_hours=duration_hours,
            reason=reason,
            admin_user_id=current_user.id,
            client_ip=request.client.host
        )
        
        return {
            "success": True,
            "blocked_ip": ip_address,
            "duration_hours": duration_hours,
            "reason": reason,
            "blocked_by": current_user.username,
            "blocked_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking IP address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error blocking IP address"
        )


@router.get("/alert-rules")
@secure_endpoint(max_requests_per_hour=30, require_admin=True)
async def get_alert_rules(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Obtener reglas de alerta configuradas"""
    try:
        rules_data = []
        for rule in security_monitor.alert_rules:
            rules_data.append({
                "name": rule.name,
                "threat_type": rule.threat_type.value,
                "threshold": rule.threshold,
                "window_minutes": rule.window_minutes,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
                "conditions": rule.conditions
            })
        
        return {
            "rules": rules_data,
            "total_rules": len(rules_data),
            "enabled_rules": len([r for r in security_monitor.alert_rules if r.enabled])
        }
        
    except Exception as e:
        logger.error(f"Error getting alert rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving alert rules"
        )


@router.get("/health")
async def get_security_monitor_health(request: Request):
    """Health check del sistema de monitoreo de seguridad"""
    try:
        health_data = {
            "monitor_running": security_monitor.running,
            "total_events": len(security_monitor.events),
            "notification_handlers": len(security_monitor.notification_handlers),
            "alert_rules_enabled": len([r for r in security_monitor.alert_rules if r.enabled]),
            "alert_rules_total": len(security_monitor.alert_rules),
            "last_event_time": None
        }
        
        if security_monitor.events:
            health_data["last_event_time"] = security_monitor.events[-1].timestamp.isoformat()
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting security monitor health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving security monitor health"
        )


def _calculate_security_status(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Calcular estado general de seguridad"""
    events_24h = stats["total_events_24h"]
    events_1h = stats["total_events_1h"]
    
    # Clasificar estado basado en número de eventos
    if events_1h >= 50:
        status_level = "critical"
        status_message = "High security activity detected"
    elif events_1h >= 20:
        status_level = "warning"
        status_message = "Elevated security activity"
    elif events_24h >= 100:
        status_level = "caution"
        status_message = "Moderate security activity"
    else:
        status_level = "normal"
        status_message = "Security activity within normal parameters"
    
    return {
        "level": status_level,
        "message": status_message,
        "events_last_hour": events_1h,
        "events_last_24h": events_24h
    }


def _get_recent_alerts() -> List[Dict[str, Any]]:
    """Obtener alertas recientes"""
    # Esta función simula alertas recientes
    # En una implementación real, se obtendría de una base de datos
    recent_time = datetime.utcnow() - timedelta(hours=24)
    alerts = []
    
    # Filtrar eventos que habrían generado alertas
    for event in security_monitor.events:
        if event.timestamp >= recent_time and event.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            alerts.append({
                "timestamp": event.timestamp.isoformat(),
                "threat_type": event.event_type.value,
                "severity": event.severity.value,
                "source_ip": event.source_ip,
                "endpoint": event.endpoint
            })
    
    return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)[:10]


def _calculate_risk_assessment(events: List[SecurityEvent], ip_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Calcular evaluación de riesgo"""
    if not events:
        return {"level": "low", "score": 0, "factors": []}
    
    risk_score = 0
    risk_factors = []
    
    # Factor 1: Volumen de eventos
    if len(events) > 100:
        risk_score += 30
        risk_factors.append("High volume of security events")
    elif len(events) > 50:
        risk_score += 15
        risk_factors.append("Moderate volume of security events")
    
    # Factor 2: Severidad de eventos
    critical_events = len([e for e in events if e.severity == AlertSeverity.CRITICAL])
    high_events = len([e for e in events if e.severity == AlertSeverity.HIGH])
    
    if critical_events > 0:
        risk_score += critical_events * 20
        risk_factors.append(f"{critical_events} critical severity events")
    
    if high_events > 5:
        risk_score += high_events * 5
        risk_factors.append(f"{high_events} high severity events")
    
    # Factor 3: IPs con alta actividad
    high_activity_ips = len([ip for ip, data in ip_analysis.items() if data["total_events"] > 10])
    if high_activity_ips > 0:
        risk_score += high_activity_ips * 10
        risk_factors.append(f"{high_activity_ips} IPs with high activity")
    
    # Factor 4: Diversidad de tipos de amenaza
    threat_types = set(e.event_type for e in events)
    if len(threat_types) > 3:
        risk_score += 15
        risk_factors.append("Multiple threat types detected")
    
    # Determinar nivel de riesgo
    if risk_score >= 70:
        risk_level = "critical"
    elif risk_score >= 40:
        risk_level = "high"
    elif risk_score >= 20:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "level": risk_level,
        "score": min(risk_score, 100),  # Cap at 100
        "factors": risk_factors
    }