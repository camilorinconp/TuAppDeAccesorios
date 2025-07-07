"""
Sistema de monitoreo de seguridad con alertas automáticas
"""
import time
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
from collections import defaultdict, deque
import smtplib
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Tipos de amenazas detectadas"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    SUSPICIOUS_USER_AGENT = "suspicious_user_agent"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALICIOUS_PAYLOAD = "malicious_payload"


@dataclass
class SecurityEvent:
    """Evento de seguridad detectado"""
    timestamp: datetime
    event_type: ThreatType
    severity: AlertSeverity
    source_ip: str
    user_agent: str
    endpoint: str
    details: Dict[str, Any]
    user_id: Optional[int] = None
    fingerprint: Optional[str] = None
    count: int = 1


@dataclass
class AlertRule:
    """Regla de alerta de seguridad"""
    name: str
    threat_type: ThreatType
    threshold: int
    window_minutes: int
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 60
    conditions: Dict[str, Any] = field(default_factory=dict)


class SecurityMonitor:
    """Monitor de seguridad en tiempo real"""
    
    def __init__(self):
        self.events = deque(maxlen=10000)  # Buffer circular para eventos
        self.alerts_sent = {}  # Tracking de alertas enviadas
        self.alert_rules = self._load_alert_rules()
        self.patterns = self._load_threat_patterns()
        self.notification_handlers = []
        self.running = False
        self.monitor_thread = None
        
        # Configurar handlers de notificación
        self._setup_notification_handlers()
        
    def _load_alert_rules(self) -> List[AlertRule]:
        """Cargar reglas de alerta"""
        return [
            # Brute force attacks
            AlertRule(
                name="brute_force_login",
                threat_type=ThreatType.BRUTE_FORCE,
                threshold=5,
                window_minutes=5,
                severity=AlertSeverity.HIGH,
                cooldown_minutes=30
            ),
            
            # SQL Injection attempts
            AlertRule(
                name="sql_injection_attempts",
                threat_type=ThreatType.SQL_INJECTION,
                threshold=1,
                window_minutes=1,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=15
            ),
            
            # XSS attempts
            AlertRule(
                name="xss_attempts",
                threat_type=ThreatType.XSS_ATTEMPT,
                threshold=3,
                window_minutes=5,
                severity=AlertSeverity.HIGH,
                cooldown_minutes=30
            ),
            
            # Rate limit abuse
            AlertRule(
                name="rate_limit_abuse",
                threat_type=ThreatType.RATE_LIMIT_ABUSE,
                threshold=10,
                window_minutes=10,
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=60
            ),
            
            # Suspicious user agents
            AlertRule(
                name="suspicious_user_agents",
                threat_type=ThreatType.SUSPICIOUS_USER_AGENT,
                threshold=5,
                window_minutes=15,
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=120
            ),
            
            # Privilege escalation
            AlertRule(
                name="privilege_escalation",
                threat_type=ThreatType.PRIVILEGE_ESCALATION,
                threshold=1,
                window_minutes=5,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=10
            ),
            
            # Anomalous behavior
            AlertRule(
                name="anomalous_behavior",
                threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                threshold=20,
                window_minutes=30,
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=60
            )
        ]
    
    def _load_threat_patterns(self) -> Dict[ThreatType, List[str]]:
        """Cargar patrones de detección de amenazas"""
        return {
            ThreatType.SQL_INJECTION: [
                r"(?i)(union|select|insert|delete|drop|create|alter|exec|execute)",
                r"(?i)(or|and)\s+['\"]?[0-9]+['\"]?\s*=\s*['\"]?[0-9]+['\"]?",
                r"['\"];\s*(select|insert|update|delete|drop)",
                r"(?i)(sleep|benchmark|waitfor|delay)\s*\(",
                r"(?i)(load_file|into\s+outfile|into\s+dumpfile)",
                r"(?i)(information_schema|mysql|performance_schema|sys)"
            ],
            
            ThreatType.XSS_ATTEMPT: [
                r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe\b[^>]*>",
                r"<object\b[^>]*>",
                r"<embed\b[^>]*>",
                r"<link\b[^>]*>",
                r"data:text/html"
            ],
            
            ThreatType.SUSPICIOUS_USER_AGENT: [
                r"(?i)(sqlmap|nikto|nmap|gobuster|dirb|masscan)",
                r"(?i)(bot|crawler|spider|scraper|scanner)",
                r"(?i)(python-requests|curl/[0-7]\.|wget)",
                r"(?i)(phantom|selenium|headless)",
                r"(?i)(attack|exploit|hack|penetration)"
            ],
            
            ThreatType.MALICIOUS_PAYLOAD: [
                r"(?i)(\.\./|\.\.\\|/etc/passwd|/proc/|cmd=|exec=)",
                r"(?i)(eval\s*\(|exec\s*\(|system\s*\()",
                r"(?i)(base64_decode|file_get_contents|include\s*\()",
                r"(?i)(\$_GET|\$_POST|\$_REQUEST|\$_COOKIE)",
                r"(?i)(wget|curl|nc\s+|netcat)"
            ]
        }
    
    def _setup_notification_handlers(self):
        """Configurar handlers de notificación"""
        # Email notifications
        if all([
            os.getenv('SMTP_HOST'),
            os.getenv('SMTP_USER'),
            os.getenv('SMTP_PASSWORD'),
            os.getenv('ALERT_EMAIL')
        ]):
            self.notification_handlers.append(self._send_email_alert)
        
        # Slack notifications
        if os.getenv('SLACK_WEBHOOK_URL'):
            self.notification_handlers.append(self._send_slack_alert)
        
        # Discord notifications
        if os.getenv('DISCORD_WEBHOOK_URL'):
            self.notification_handlers.append(self._send_discord_alert)
        
        # Log-based notifications (always available)
        self.notification_handlers.append(self._log_alert)
    
    def detect_threat(self, request_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Detectar amenazas en datos de request"""
        threats_detected = []
        
        url = request_data.get('url', '')
        user_agent = request_data.get('user_agent', '')
        payload = request_data.get('payload', '')
        headers = request_data.get('headers', {})
        
        # Detectar SQL injection
        for pattern in self.patterns[ThreatType.SQL_INJECTION]:
            if re.search(pattern, url + payload):
                threats_detected.append(ThreatType.SQL_INJECTION)
                break
        
        # Detectar XSS
        for pattern in self.patterns[ThreatType.XSS_ATTEMPT]:
            if re.search(pattern, url + payload):
                threats_detected.append(ThreatType.XSS_ATTEMPT)
                break
        
        # Detectar user agents sospechosos
        for pattern in self.patterns[ThreatType.SUSPICIOUS_USER_AGENT]:
            if re.search(pattern, user_agent):
                threats_detected.append(ThreatType.SUSPICIOUS_USER_AGENT)
                break
        
        # Detectar payloads maliciosos
        for pattern in self.patterns[ThreatType.MALICIOUS_PAYLOAD]:
            if re.search(pattern, url + payload):
                threats_detected.append(ThreatType.MALICIOUS_PAYLOAD)
                break
        
        # Si se detectó alguna amenaza, crear evento
        if threats_detected:
            # Usar la amenaza más severa
            threat_severity_map = {
                ThreatType.SQL_INJECTION: AlertSeverity.CRITICAL,
                ThreatType.XSS_ATTEMPT: AlertSeverity.HIGH,
                ThreatType.MALICIOUS_PAYLOAD: AlertSeverity.HIGH,
                ThreatType.SUSPICIOUS_USER_AGENT: AlertSeverity.MEDIUM,
            }
            
            primary_threat = max(threats_detected, 
                               key=lambda t: list(AlertSeverity).index(threat_severity_map.get(t, AlertSeverity.LOW)))
            
            return SecurityEvent(
                timestamp=datetime.utcnow(),
                event_type=primary_threat,
                severity=threat_severity_map.get(primary_threat, AlertSeverity.MEDIUM),
                source_ip=request_data.get('source_ip', 'unknown'),
                user_agent=user_agent,
                endpoint=request_data.get('endpoint', ''),
                details={
                    'threats_detected': [t.value for t in threats_detected],
                    'url': url,
                    'method': request_data.get('method', ''),
                    'payload_snippet': payload[:200] if payload else '',
                    'headers': dict(headers)
                },
                user_id=request_data.get('user_id'),
                fingerprint=self._generate_fingerprint(request_data)
            )
        
        return None
    
    def _generate_fingerprint(self, request_data: Dict[str, Any]) -> str:
        """Generar fingerprint único para el evento"""
        import hashlib
        
        key_data = f"{request_data.get('source_ip', '')}:{request_data.get('user_agent', '')}:{request_data.get('endpoint', '')}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def record_security_event(self, event: SecurityEvent):
        """Registrar evento de seguridad"""
        self.events.append(event)
        
        # Log inmediato para eventos críticos
        if event.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            logger.critical(
                f"Security threat detected: {event.event_type.value}",
                severity=event.severity.value,
                source_ip=event.source_ip,
                endpoint=event.endpoint,
                user_agent=event.user_agent,
                user_id=event.user_id,
                details=event.details
            )
        else:
            logger.warning(
                f"Security event: {event.event_type.value}",
                severity=event.severity.value,
                source_ip=event.source_ip,
                endpoint=event.endpoint
            )
        
        # Verificar si debe disparar alertas
        self._check_alert_rules(event)
    
    def _check_alert_rules(self, new_event: SecurityEvent):
        """Verificar reglas de alerta para el nuevo evento"""
        current_time = datetime.utcnow()
        
        for rule in self.alert_rules:
            if not rule.enabled or rule.threat_type != new_event.event_type:
                continue
            
            # Verificar cooldown
            rule_key = f"{rule.name}:{new_event.source_ip}"
            if rule_key in self.alerts_sent:
                last_alert = self.alerts_sent[rule_key]
                if current_time - last_alert < timedelta(minutes=rule.cooldown_minutes):
                    continue
            
            # Contar eventos del mismo tipo en la ventana de tiempo
            window_start = current_time - timedelta(minutes=rule.window_minutes)
            matching_events = [
                event for event in self.events
                if (event.event_type == rule.threat_type and
                    event.source_ip == new_event.source_ip and
                    event.timestamp >= window_start)
            ]
            
            if len(matching_events) >= rule.threshold:
                self._trigger_alert(rule, matching_events, new_event)
                self.alerts_sent[rule_key] = current_time
    
    def _trigger_alert(self, rule: AlertRule, events: List[SecurityEvent], trigger_event: SecurityEvent):
        """Disparar alerta de seguridad"""
        alert_data = {
            'rule_name': rule.name,
            'threat_type': rule.threat_type.value,
            'severity': rule.severity.value,
            'source_ip': trigger_event.source_ip,
            'event_count': len(events),
            'time_window': rule.window_minutes,
            'trigger_event': {
                'timestamp': trigger_event.timestamp.isoformat(),
                'endpoint': trigger_event.endpoint,
                'user_agent': trigger_event.user_agent,
                'details': trigger_event.details
            },
            'recent_events': [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'endpoint': event.endpoint,
                    'details': event.details
                }
                for event in events[-5:]  # Últimos 5 eventos
            ]
        }
        
        # Enviar notificaciones
        for handler in self.notification_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                logger.error(f"Error sending security alert: {e}")
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Enviar alerta por email"""
        try:
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            alert_email = os.getenv('ALERT_EMAIL')
            
            msg = MimeMultipart()
            msg['From'] = smtp_user
            msg['To'] = alert_email
            msg['Subject'] = f"🚨 Security Alert: {alert_data['threat_type']} - {alert_data['severity'].upper()}"
            
            body = self._format_email_body(alert_data)
            msg.attach(MimeText(body, 'html'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Security alert email sent for {alert_data['rule_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Enviar alerta a Slack"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            
            color_map = {
                'low': '#36a64f',
                'medium': '#ff9500',
                'high': '#ff4444',
                'critical': '#8b0000'
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(alert_data['severity'], '#ff4444'),
                    'title': f"🚨 Security Alert: {alert_data['threat_type']}",
                    'fields': [
                        {
                            'title': 'Severity',
                            'value': alert_data['severity'].upper(),
                            'short': True
                        },
                        {
                            'title': 'Source IP',
                            'value': alert_data['source_ip'],
                            'short': True
                        },
                        {
                            'title': 'Event Count',
                            'value': f"{alert_data['event_count']} events in {alert_data['time_window']} minutes",
                            'short': True
                        },
                        {
                            'title': 'Endpoint',
                            'value': alert_data['trigger_event']['endpoint'],
                            'short': True
                        }
                    ],
                    'footer': 'TuApp Security Monitor',
                    'ts': int(time.time())
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Security alert sent to Slack for {alert_data['rule_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_discord_alert(self, alert_data: Dict[str, Any]):
        """Enviar alerta a Discord"""
        try:
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            
            color_map = {
                'low': 0x36a64f,
                'medium': 0xff9500,
                'high': 0xff4444,
                'critical': 0x8b0000
            }
            
            embed = {
                'title': f"🚨 Security Alert: {alert_data['threat_type']}",
                'color': color_map.get(alert_data['severity'], 0xff4444),
                'fields': [
                    {
                        'name': 'Severity',
                        'value': alert_data['severity'].upper(),
                        'inline': True
                    },
                    {
                        'name': 'Source IP',
                        'value': alert_data['source_ip'],
                        'inline': True
                    },
                    {
                        'name': 'Events',
                        'value': f"{alert_data['event_count']} in {alert_data['time_window']}min",
                        'inline': True
                    },
                    {
                        'name': 'Endpoint',
                        'value': alert_data['trigger_event']['endpoint'],
                        'inline': False
                    }
                ],
                'footer': {
                    'text': 'TuApp Security Monitor'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            payload = {'embeds': [embed]}
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Security alert sent to Discord for {alert_data['rule_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
    
    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log de alerta (siempre disponible)"""
        logger.critical(
            f"SECURITY ALERT TRIGGERED: {alert_data['rule_name']}",
            threat_type=alert_data['threat_type'],
            severity=alert_data['severity'],
            source_ip=alert_data['source_ip'],
            event_count=alert_data['event_count'],
            time_window=alert_data['time_window'],
            trigger_endpoint=alert_data['trigger_event']['endpoint']
        )
    
    def _format_email_body(self, alert_data: Dict[str, Any]) -> str:
        """Formatear cuerpo del email de alerta"""
        return f"""
        <html>
        <body>
            <h2 style="color: red;">🚨 Security Alert Triggered</h2>
            
            <h3>Alert Details</h3>
            <ul>
                <li><strong>Rule:</strong> {alert_data['rule_name']}</li>
                <li><strong>Threat Type:</strong> {alert_data['threat_type']}</li>
                <li><strong>Severity:</strong> {alert_data['severity'].upper()}</li>
                <li><strong>Source IP:</strong> {alert_data['source_ip']}</li>
                <li><strong>Event Count:</strong> {alert_data['event_count']} events in {alert_data['time_window']} minutes</li>
            </ul>
            
            <h3>Trigger Event</h3>
            <ul>
                <li><strong>Timestamp:</strong> {alert_data['trigger_event']['timestamp']}</li>
                <li><strong>Endpoint:</strong> {alert_data['trigger_event']['endpoint']}</li>
                <li><strong>User Agent:</strong> {alert_data['trigger_event']['user_agent']}</li>
            </ul>
            
            <h3>Recent Events</h3>
            <table border="1" style="border-collapse: collapse;">
                <tr>
                    <th>Timestamp</th>
                    <th>Endpoint</th>
                </tr>
                {"".join([
                    f"<tr><td>{event['timestamp']}</td><td>{event['endpoint']}</td></tr>"
                    for event in alert_data['recent_events']
                ])}
            </table>
            
            <p><em>This alert was generated by TuApp Security Monitor</em></p>
        </body>
        </html>
        """
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de seguridad"""
        current_time = datetime.utcnow()
        last_24h = current_time - timedelta(hours=24)
        last_1h = current_time - timedelta(hours=1)
        
        # Filtrar eventos por tiempo
        events_24h = [e for e in self.events if e.timestamp >= last_24h]
        events_1h = [e for e in self.events if e.timestamp >= last_1h]
        
        # Agrupar por tipo de amenaza
        threats_24h = defaultdict(int)
        threats_1h = defaultdict(int)
        
        for event in events_24h:
            threats_24h[event.event_type.value] += 1
        
        for event in events_1h:
            threats_1h[event.event_type.value] += 1
        
        # Top IPs atacantes
        ip_attacks = defaultdict(int)
        for event in events_24h:
            ip_attacks[event.source_ip] += 1
        
        top_attackers = sorted(ip_attacks.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_events_24h': len(events_24h),
            'total_events_1h': len(events_1h),
            'threats_24h': dict(threats_24h),
            'threats_1h': dict(threats_1h),
            'top_attackers': top_attackers,
            'alerts_sent_today': len([
                ts for ts in self.alerts_sent.values()
                if ts >= last_24h
            ]),
            'active_rules': len([r for r in self.alert_rules if r.enabled]),
            'notification_handlers': len(self.notification_handlers)
        }
    
    def start_monitoring(self):
        """Iniciar monitoreo en background"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Security monitor started")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Security monitor stopped")
    
    def _monitor_loop(self):
        """Loop principal de monitoreo"""
        while self.running:
            try:
                # Limpiar eventos antiguos (más de 7 días)
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                while self.events and self.events[0].timestamp < cutoff_time:
                    self.events.popleft()
                
                # Limpiar alertas antiguas del cache
                cutoff_alerts = datetime.utcnow() - timedelta(hours=24)
                self.alerts_sent = {
                    k: v for k, v in self.alerts_sent.items()
                    if v >= cutoff_alerts
                }
                
                time.sleep(60)  # Check cada minuto
                
            except Exception as e:
                logger.error(f"Error in security monitor loop: {e}")
                time.sleep(60)


# Instancia global
security_monitor = SecurityMonitor()


# Funciones helper para integración
def record_failed_login(source_ip: str, user_agent: str, endpoint: str, username: str = None):
    """Registrar intento de login fallido"""
    event = SecurityEvent(
        timestamp=datetime.utcnow(),
        event_type=ThreatType.BRUTE_FORCE,
        severity=AlertSeverity.MEDIUM,
        source_ip=source_ip,
        user_agent=user_agent,
        endpoint=endpoint,
        details={
            'login_attempt': True,
            'username': username,
            'success': False
        }
    )
    security_monitor.record_security_event(event)


def record_rate_limit_exceeded(source_ip: str, user_agent: str, endpoint: str, limit_info: Dict[str, Any]):
    """Registrar exceso de rate limit"""
    event = SecurityEvent(
        timestamp=datetime.utcnow(),
        event_type=ThreatType.RATE_LIMIT_ABUSE,
        severity=AlertSeverity.MEDIUM,
        source_ip=source_ip,
        user_agent=user_agent,
        endpoint=endpoint,
        details={
            'rate_limit_exceeded': True,
            'limit_info': limit_info
        }
    )
    security_monitor.record_security_event(event)


def record_privilege_escalation_attempt(source_ip: str, user_agent: str, endpoint: str, user_id: int, attempted_action: str):
    """Registrar intento de escalación de privilegios"""
    event = SecurityEvent(
        timestamp=datetime.utcnow(),
        event_type=ThreatType.PRIVILEGE_ESCALATION,
        severity=AlertSeverity.CRITICAL,
        source_ip=source_ip,
        user_agent=user_agent,
        endpoint=endpoint,
        details={
            'privilege_escalation': True,
            'attempted_action': attempted_action
        },
        user_id=user_id
    )
    security_monitor.record_security_event(event)


# Iniciar monitor automáticamente
import os
if os.getenv('SECURITY_MONITOR_ENABLED', 'true').lower() == 'true':
    security_monitor.start_monitoring()


# Importaciones necesarias
import re
import os