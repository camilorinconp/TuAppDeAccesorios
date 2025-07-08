"""
Middleware para auditoría automática de requests
"""
import time
import uuid
import asyncio
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..security.audit_logger import (
    audit_logger, 
    AuditContext, 
    AuditEventType, 
    AuditSeverity,
    log_security_event,
    log_data_access
)
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware para auditoría automática de todas las requests"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Configuración de auditoría
        self.audit_enabled = True
        self.audit_read_operations = False  # Solo auditar operaciones de escritura por defecto
        self.audit_sensitive_endpoints = True
        
        # Endpoints que siempre se auditan
        self.always_audit_patterns = [
            '/token',
            '/login',
            '/logout',
            '/refresh',
            '/auth/',
            '/api/users/',
            '/api/admin/',
            '/api/security/',
            '/api/audit/',
            '/api/cache/clear',
            '/api/backup/',
            '/api/system/'
        ]
        
        # Endpoints que nunca se auditan
        self.never_audit_patterns = [
            '/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico',
            '/static/',
            '/metrics',
            '/ping'
        ]
        
        # Métodos que se auditan
        self.audit_methods = {'POST', 'PUT', 'PATCH', 'DELETE'}
        
        # Métodos de lectura (solo si están habilitados)
        self.read_methods = {'GET', 'HEAD', 'OPTIONS'}
        
    def _should_audit_request(self, request: Request) -> bool:
        """Determinar si se debe auditar la request"""
        
        if not self.audit_enabled:
            return False
        
        path = request.url.path
        method = request.method
        
        # Nunca auditar ciertos endpoints
        for pattern in self.never_audit_patterns:
            if pattern in path:
                return False
        
        # Siempre auditar ciertos endpoints
        for pattern in self.always_audit_patterns:
            if pattern in path:
                return True
        
        # Auditar métodos de escritura
        if method in self.audit_methods:
            return True
        
        # Auditar métodos de lectura si está habilitado
        if self.audit_read_operations and method in self.read_methods:
            return True
        
        return False
    
    def _classify_endpoint(self, request: Request) -> tuple[Optional[AuditEventType], Optional[str], Optional[str]]:
        """Clasificar endpoint para determinar tipo de evento de auditoría"""
        
        path = request.url.path.lower()
        method = request.method.upper()
        
        # Autenticación
        if '/token' in path or '/login' in path:
            return AuditEventType.LOGIN, "auth", "login"
        elif '/logout' in path:
            return AuditEventType.LOGOUT, "auth", "logout"
        elif '/refresh' in path:
            return AuditEventType.TOKEN_REFRESH, "auth", "token_refresh"
        
        # Usuarios
        elif '/api/users/' in path:
            if method == 'POST':
                return AuditEventType.USER_CREATE, "user", "create"
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.USER_UPDATE, "user", "update"
            elif method == 'DELETE':
                return AuditEventType.USER_DELETE, "user", "delete"
            elif method == 'GET':
                return AuditEventType.USER_CREATE, "user", "view"  # Reusing enum
        
        # Productos
        elif '/api/products/' in path:
            if method == 'POST':
                return AuditEventType.PRODUCT_CREATE, "product", "create"
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.PRODUCT_UPDATE, "product", "update"
            elif method == 'DELETE':
                return AuditEventType.PRODUCT_DELETE, "product", "delete"
            elif method == 'GET':
                return AuditEventType.PRODUCT_VIEW, "product", "view"
        
        elif '/api/products/search' in path:
            return AuditEventType.PRODUCT_SEARCH, "product", "search"
        
        # Distribuidores
        elif '/api/distributors/' in path:
            if method == 'POST':
                return AuditEventType.DISTRIBUTOR_CREATE, "distributor", "create"
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.DISTRIBUTOR_UPDATE, "distributor", "update"
            elif method == 'DELETE':
                return AuditEventType.DISTRIBUTOR_DELETE, "distributor", "delete"
        
        # POS y ventas
        elif '/api/pos/' in path or '/api/sales/' in path:
            if method == 'POST':
                return AuditEventType.SALE_CREATE, "sale", "create"
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.SALE_UPDATE, "sale", "update"
            elif method == 'DELETE':
                return AuditEventType.SALE_DELETE, "sale", "delete"
        
        # Sistema
        elif '/api/cache/clear' in path:
            return AuditEventType.CACHE_CLEAR, "system", "cache_clear"
        
        elif '/api/backup/' in path:
            if method == 'POST':
                return AuditEventType.BACKUP_CREATE, "system", "backup_create"
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.BACKUP_RESTORE, "system", "backup_restore"
        
        elif '/api/system/' in path or '/api/config/' in path:
            return AuditEventType.SYSTEM_CONFIG_CHANGE, "system", "config_change"
        
        # Seguridad
        elif '/api/security/' in path:
            return AuditEventType.SECURITY_ALERT, "security", "security_access"
        
        # Auditoría
        elif '/api/audit/' in path:
            return AuditEventType.DATA_EXPORT, "audit", "audit_access"
        
        # Reportes
        elif '/api/report' in path:
            return AuditEventType.REPORT_GENERATE, "report", "generate"
        
        # Genérico
        return None, None, None
    
    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """Extraer ID del recurso de la URL"""
        
        path_parts = request.url.path.split('/')
        
        # Buscar partes que parezcan IDs (números)
        for part in reversed(path_parts):
            if part.isdigit():
                return part
        
        return None
    
    def _get_user_info(self, request: Request) -> tuple[Optional[int], Optional[str]]:
        """Obtener información del usuario de la request"""
        
        user_id = None
        username = None
        
        # Intentar obtener del estado de la request
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        if hasattr(request.state, 'username'):
            username = request.state.username
        
        if hasattr(request.state, 'user'):
            user = request.state.user
            if hasattr(user, 'id'):
                user_id = user.id
            if hasattr(user, 'username'):
                username = user.username
        
        return user_id, username
    
    def _create_audit_context(self, request: Request, response: Optional[Response] = None) -> AuditContext:
        """Crear contexto de auditoría"""
        
        # Generar ID único para la request
        request_id = str(uuid.uuid4())
        
        # Obtener IP del cliente
        client_ip = request.client.host if request.client else None
        
        # Considerar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        
        # Obtener sesión ID si existe
        session_id = None
        if hasattr(request.state, 'session_id'):
            session_id = request.state.session_id
        
        # Crear contexto
        context = AuditContext(
            request_id=request_id,
            session_id=session_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip,
            endpoint=request.url.path,
            method=request.method,
            response_code=response.status_code if response else None,
            request_size=int(request.headers.get("content-length", 0)),
            additional_data={
                "query_params": dict(request.query_params),
                "headers": {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']},
            }
        )
        
        return context
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Procesar request con auditoría"""
        
        # Verificar si se debe auditar
        if not self._should_audit_request(request):
            return await call_next(request)
        
        # Tiempo de inicio
        start_time = time.time()
        
        # Crear contexto inicial
        context = self._create_audit_context(request)
        
        # Obtener información del usuario
        user_id, username = self._get_user_info(request)
        
        # Clasificar endpoint
        event_type, resource_type, action = self._classify_endpoint(request)
        
        # Extraer ID del recurso
        resource_id = self._extract_resource_id(request)
        
        # Procesar request
        response = None
        error_occurred = False
        
        try:
            response = await call_next(request)
            
            # Actualizar contexto con respuesta
            context.response_code = response.status_code
            context.response_time = time.time() - start_time
            
            # Obtener tamaño de respuesta
            if hasattr(response, 'headers') and 'content-length' in response.headers:
                context.response_size = int(response.headers['content-length'])
            
        except Exception as e:
            error_occurred = True
            
            # Crear respuesta de error para auditoría
            context.response_code = 500
            context.response_time = time.time() - start_time
            context.additional_data['error'] = str(e)
            
            # Log del error
            await audit_logger.log_event(
                event_type=AuditEventType.ERROR_OCCURRED,
                severity=AuditSeverity.ERROR,
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                description=f"Error processing request: {str(e)}",
                context=context,
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            # Re-raise la excepción
            raise
        
        finally:
            # Auditar la request si no hubo error o si queremos auditar errores
            if not error_occurred and event_type:
                
                # Determinar severidad basada en código de respuesta
                if response and response.status_code >= 400:
                    severity = AuditSeverity.WARNING
                elif response and response.status_code >= 500:
                    severity = AuditSeverity.ERROR
                else:
                    severity = AuditSeverity.INFO
                
                # Descripción del evento
                description = f"{action.capitalize()} {resource_type}" if action and resource_type else f"Request to {request.url.path}"
                
                # Registrar evento de auditoría
                await audit_logger.log_event(
                    event_type=event_type,
                    severity=severity,
                    user_id=user_id,
                    username=username,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    description=description,
                    context=context
                )
                
                # Log adicional para eventos sensibles
                if event_type in [AuditEventType.USER_DELETE, AuditEventType.SYSTEM_CONFIG_CHANGE, 
                                AuditEventType.BACKUP_RESTORE, AuditEventType.CACHE_CLEAR]:
                    logger.warning(
                        f"Sensitive operation performed: {event_type.value}",
                        user_id=user_id,
                        username=username,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        ip_address=context.ip_address,
                        endpoint=context.endpoint,
                        response_code=context.response_code
                    )
        
        return response


# Middleware para auditoría de autenticación
class AuthAuditMiddleware(BaseHTTPMiddleware):
    """Middleware específico para auditoría de autenticación"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Auditar eventos de autenticación"""
        
        path = request.url.path
        method = request.method
        
        # Solo procesar endpoints de autenticación
        if not any(pattern in path for pattern in ['/token', '/login', '/logout', '/refresh', '/auth/']):
            return await call_next(request)
        
        # Crear contexto
        context = AuditContext(
            request_id=str(uuid.uuid4()),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            endpoint=path,
            method=method
        )
        
        # Procesar request
        start_time = time.time()
        response = await call_next(request)
        
        # Actualizar contexto
        context.response_code = response.status_code
        context.response_time = time.time() - start_time
        
        # Obtener información del usuario si está disponible
        user_id, username = None, None
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        if hasattr(request.state, 'username'):
            username = request.state.username
        
        # Determinar evento y severidad
        success = 200 <= response.status_code < 300
        
        if '/login' in path or '/token' in path:
            event_type = AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED
            severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
            description = f"Login attempt {'successful' if success else 'failed'}"
            
        elif '/logout' in path:
            event_type = AuditEventType.LOGOUT
            severity = AuditSeverity.INFO
            description = "User logout"
            
        elif '/refresh' in path:
            event_type = AuditEventType.TOKEN_REFRESH
            severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
            description = f"Token refresh {'successful' if success else 'failed'}"
            
        else:
            # Otros eventos de autenticación
            event_type = AuditEventType.LOGIN
            severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
            description = f"Authentication request to {path}"
        
        # Log del evento
        await audit_logger.log_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            resource_type="auth",
            action="authenticate",
            description=description,
            context=context
        )
        
        return response


# Decorator para auditoría manual
def audit_operation(
    event_type: AuditEventType,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO
):
    """Decorator para auditar operaciones específicas"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Buscar request en los argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Crear contexto si hay request
            context = None
            if request:
                context = AuditContext(
                    request_id=str(uuid.uuid4()),
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    endpoint=request.url.path,
                    method=request.method
                )
            
            # Obtener información del usuario
            user_id, username = None, None
            if request:
                if hasattr(request.state, 'user_id'):
                    user_id = request.state.user_id
                if hasattr(request.state, 'username'):
                    username = request.state.username
            
            # Ejecutar función
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Auditar éxito
                context.response_time = time.time() - start_time
                context.response_code = 200
                
                await audit_logger.log_event(
                    event_type=event_type,
                    severity=severity,
                    user_id=user_id,
                    username=username,
                    resource_type=resource_type,
                    action=action,
                    description=f"Operation {func.__name__} completed successfully",
                    context=context
                )
                
                return result
                
            except Exception as e:
                # Auditar error
                context.response_time = time.time() - start_time
                context.response_code = 500
                
                await audit_logger.log_event(
                    event_type=AuditEventType.ERROR_OCCURRED,
                    severity=AuditSeverity.ERROR,
                    user_id=user_id,
                    username=username,
                    resource_type=resource_type,
                    action=action,
                    description=f"Operation {func.__name__} failed: {str(e)}",
                    context=context,
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "function": func.__name__
                    }
                )
                
                raise
        
        return wrapper
    return decorator