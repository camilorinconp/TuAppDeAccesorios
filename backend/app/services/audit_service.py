# ==================================================================
# SERVICIO DE AUDITORÍA - SEGUIMIENTO Y REGISTRO DE EVENTOS
# ==================================================================

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import Request
from datetime import datetime, timedelta, timezone
import json
import hashlib
import uuid

from ..models.audit import (
    AuditLog, 
    SecurityAlert, 
    LoginAttempt,
    AuditActionType, 
    AuditSeverity
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class AuditService:
    """Servicio principal para el manejo de auditoría"""
    
    @staticmethod
    def log_event(
        db: Session,
        action_type: AuditActionType,
        description: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        table_name: Optional[str] = None,
        record_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AuditLog:
        """Registra un evento de auditoría en la base de datos"""
        
        try:
            # Extraer información de la request si está disponible
            ip_address = None
            user_agent = None
            endpoint = None
            request_method = None
            
            if request:
                ip_address = AuditService._get_client_ip(request)
                user_agent = request.headers.get("user-agent")
                endpoint = str(request.url.path)
                request_method = request.method
            
            # Crear registro de auditoría
            audit_log = AuditLog(
                action_type=action_type,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                username=username,
                user_role=user_role,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                table_name=table_name,
                record_id=str(record_id) if record_id else None,
                description=description,
                old_values=old_values,
                new_values=new_values,
                additional_data=additional_data,
                endpoint=endpoint,
                request_method=request_method,
                execution_time_ms=execution_time_ms
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            # Log estructurado para monitoreo
            logger.info(
                "audit_event_logged",
                audit_id=audit_log.id,
                action_type=action_type.value,
                severity=severity.value,
                user_id=user_id,
                username=username,
                table_name=table_name,
                record_id=record_id,
                ip_address=ip_address
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(
                "Error al registrar evento de auditoría",
                error=str(e),
                action_type=action_type.value,
                user_id=user_id
            )
            db.rollback()
            raise
    
    @staticmethod
    def log_security_alert(
        db: Session,
        alert_type: str,
        description: str,
        severity: AuditSeverity = AuditSeverity.HIGH,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        username_attempt: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> SecurityAlert:
        """Registra una alerta de seguridad"""
        
        try:
            # Extraer información de la request si está disponible
            if request and not ip_address:
                ip_address = AuditService._get_client_ip(request)
            if request and not user_agent:
                user_agent = request.headers.get("user-agent")
            
            # Crear alerta de seguridad
            alert = SecurityAlert(
                alert_type=alert_type,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                username_attempt=username_attempt,
                description=description,
                details=details,
                resolved="false"
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Log crítico para alertas de seguridad
            logger.critical(
                "security_alert_created",
                alert_id=alert.id,
                alert_type=alert_type,
                severity=severity.value,
                ip_address=ip_address,
                username_attempt=username_attempt,
                description=description
            )
            
            return alert
            
        except Exception as e:
            logger.error(
                "Error al registrar alerta de seguridad",
                error=str(e),
                alert_type=alert_type
            )
            db.rollback()
            raise
    
    @staticmethod
    def log_login_attempt(
        db: Session,
        username: str,
        success: bool,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        request: Optional[Request] = None
    ) -> LoginAttempt:
        """Registra un intento de login"""
        
        try:
            # Extraer información de la request si está disponible
            if request and not ip_address:
                ip_address = AuditService._get_client_ip(request)
            if request and not user_agent:
                user_agent = request.headers.get("user-agent")
            
            # Crear registro de intento de login
            login_attempt = LoginAttempt(
                timestamp=datetime.now(timezone.utc),
                username=username,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                failure_reason=failure_reason,
                user_id=user_id
            )
            
            db.add(login_attempt)
            db.commit()
            db.refresh(login_attempt)
            
            # Log del intento
            log_level = "info" if success else "warning"
            getattr(logger, log_level)(
                "login_attempt_logged",
                attempt_id=login_attempt.id,
                username=username,
                success=success,
                ip_address=ip_address,
                failure_reason=failure_reason
            )
            
            # Verificar si hay intentos fallidos sospechosos
            if not success:
                AuditService._check_suspicious_login_attempts(db, username, ip_address)
            
            return login_attempt
            
        except Exception as e:
            logger.error(
                "Error al registrar intento de login",
                error=str(e),
                username=username
            )
            db.rollback()
            raise
    
    @staticmethod
    def _check_suspicious_login_attempts(
        db: Session,
        username: str,
        ip_address: Optional[str]
    ):
        """Verifica patrones sospechosos de intentos de login"""
        
        try:
            # Verificar intentos fallidos en los últimos 15 minutos
            since = datetime.now(timezone.utc) - timedelta(minutes=15)
            
            failed_attempts = db.query(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.success == False,
                LoginAttempt.timestamp >= since
            ).count()
            
            # Alerta por múltiples intentos fallidos
            if failed_attempts >= 5:
                AuditService.log_security_alert(
                    db=db,
                    alert_type="MULTIPLE_FAILED_LOGINS",
                    description=f"Usuario '{username}' ha tenido {failed_attempts} intentos de login fallidos en 15 minutos",
                    severity=AuditSeverity.HIGH,
                    ip_address=ip_address,
                    username_attempt=username,
                    details={
                        "failed_attempts": failed_attempts,
                        "time_window_minutes": 15,
                        "username": username
                    }
                )
            
            # Verificar intentos desde múltiples IPs
            if ip_address:
                unique_ips = db.query(LoginAttempt.ip_address).filter(
                    LoginAttempt.username == username,
                    LoginAttempt.timestamp >= since,
                    LoginAttempt.ip_address.isnot(None)
                ).distinct().count()
                
                if unique_ips >= 3:
                    AuditService.log_security_alert(
                        db=db,
                        alert_type="MULTIPLE_IP_LOGIN_ATTEMPTS",
                        description=f"Usuario '{username}' ha intentado login desde {unique_ips} IPs diferentes en 15 minutos",
                        severity=AuditSeverity.CRITICAL,
                        ip_address=ip_address,
                        username_attempt=username,
                        details={
                            "unique_ips": unique_ips,
                            "time_window_minutes": 15,
                            "username": username
                        }
                    )
        
        except Exception as e:
            logger.error(
                "Error al verificar intentos sospechosos",
                error=str(e),
                username=username,
                ip_address=ip_address
            )
    
    @staticmethod
    def _get_client_ip(request: Request) -> Optional[str]:
        """Extrae la IP real del cliente considerando proxies"""
        
        # Verificar headers de proxy comunes
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Tomar la primera IP (cliente original)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback a la IP de conexión directa
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    @staticmethod
    def generate_session_id() -> str:
        """Genera un ID de sesión único"""
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash de datos sensibles para auditoría"""
        return hashlib.sha256(data.encode()).hexdigest()


class AuditQueryService:
    """Servicio para consultas de auditoría"""
    
    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Obtiene la actividad de un usuario específico"""
        
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_security_alerts(
        db: Session,
        resolved: Optional[bool] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100
    ) -> List[SecurityAlert]:
        """Obtiene alertas de seguridad"""
        
        query = db.query(SecurityAlert)
        
        if resolved is not None:
            query = query.filter(SecurityAlert.resolved == resolved)
        if severity:
            query = query.filter(SecurityAlert.severity == severity)
        
        return query.order_by(SecurityAlert.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_failed_login_attempts(
        db: Session,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[LoginAttempt]:
        """Obtiene intentos de login fallidos"""
        
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = db.query(LoginAttempt).filter(
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= since
        )
        
        if username:
            query = query.filter(LoginAttempt.username == username)
        if ip_address:
            query = query.filter(LoginAttempt.ip_address == ip_address)
        
        return query.order_by(LoginAttempt.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_audit_statistics(
        db: Session,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de auditoría"""
        
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Conteos por tipo de acción
        action_counts = {}
        for action_type in AuditActionType:
            count = db.query(AuditLog).filter(
                AuditLog.action_type == action_type,
                AuditLog.timestamp >= since
            ).count()
            action_counts[action_type.value] = count
        
        # Conteos por severidad
        severity_counts = {}
        for severity in AuditSeverity:
            count = db.query(AuditLog).filter(
                AuditLog.severity == severity,
                AuditLog.timestamp >= since
            ).count()
            severity_counts[severity.value] = count
        
        # Alertas sin resolver
        unresolved_alerts = db.query(SecurityAlert).filter(
            SecurityAlert.resolved == False
        ).count()
        
        # Intentos de login fallidos
        failed_logins = db.query(LoginAttempt).filter(
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= since
        ).count()
        
        return {
            "time_window_hours": hours,
            "action_counts": action_counts,
            "severity_counts": severity_counts,
            "unresolved_alerts": unresolved_alerts,
            "failed_logins_recent": failed_logins,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }