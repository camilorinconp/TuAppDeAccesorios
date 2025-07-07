"""
Decoradores y utilidades de seguridad para endpoints
"""
from functools import wraps
from typing import Callable, List, Optional, Any
from fastapi import HTTPException, status, Request
import time
import hashlib

from ..logging_config import get_secure_logger
from .input_validation import InputValidator

logger = get_secure_logger(__name__)


class EndpointSecurity:
    """Clase para aplicar múltiples validaciones de seguridad a endpoints"""
    
    def __init__(self):
        self.request_history = {}  # Cache simple para tracking
        self.max_history_size = 10000
    
    def validate_request_rate(self, client_ip: str, endpoint: str, max_requests: int = 100, window: int = 3600) -> bool:
        """Validar rate limiting por IP y endpoint específico"""
        current_time = time.time()
        key = f"{client_ip}:{endpoint}"
        
        if key not in self.request_history:
            self.request_history[key] = []
        
        # Limpiar requests antiguos
        self.request_history[key] = [
            req_time for req_time in self.request_history[key] 
            if current_time - req_time < window
        ]
        
        # Verificar límite
        if len(self.request_history[key]) >= max_requests:
            return False
        
        # Agregar request actual
        self.request_history[key].append(current_time)
        
        # Limpiar cache si crece demasiado
        if len(self.request_history) > self.max_history_size:
            self.request_history.clear()
        
        return True
    
    def detect_suspicious_activity(self, request: Request) -> List[str]:
        """Detectar actividad sospechosa en el request"""
        suspicious_indicators = []
        
        # Verificar User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "gobuster", "scanner", "bot"]
        if any(agent in user_agent for agent in suspicious_agents):
            suspicious_indicators.append("suspicious_user_agent")
        
        # Verificar headers sospechosos
        suspicious_headers = ["x-forwarded-host", "x-cluster-client-ip", "x-real-ip"]
        for header in suspicious_headers:
            if header in request.headers and request.headers[header] != request.client.host:
                suspicious_indicators.append("suspicious_headers")
        
        # Verificar tamaño de request
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB
            suspicious_indicators.append("large_request")
        
        # Verificar patrones en URL
        url_str = str(request.url).lower()
        if any(pattern in url_str for pattern in ["union", "select", "drop", "insert", "../", "script"]):
            suspicious_indicators.append("suspicious_url_pattern")
        
        return suspicious_indicators
    
    def generate_request_fingerprint(self, request: Request) -> str:
        """Generar fingerprint único del request para tracking"""
        fingerprint_data = f"{request.client.host}:{request.method}:{request.url.path}:{request.headers.get('user-agent', '')}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]


# Instancia global
endpoint_security = EndpointSecurity()


def secure_endpoint(
    max_requests_per_hour: int = 100,
    require_admin: bool = False,
    validate_input: bool = True,
    log_access: bool = True
):
    """
    Decorador para asegurar endpoints con múltiples validaciones
    
    Args:
        max_requests_per_hour: Límite de requests por hora por IP
        require_admin: Si requiere permisos de administrador
        validate_input: Si validar inputs automáticamente
        log_access: Si registrar accesos en logs de auditoría
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar request en los argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Buscar en kwargs
                request = kwargs.get('request')
            
            if not request:
                logger.error("Request object not found in secure_endpoint decorator")
                raise HTTPException(status_code=500, detail="Internal security error")
            
            client_ip = request.client.host
            endpoint = request.url.path
            
            # 1. Rate limiting específico
            if not endpoint_security.validate_request_rate(
                client_ip, endpoint, max_requests_per_hour, 3600
            ):
                logger.warning(
                    f"Rate limit exceeded for endpoint",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    max_requests=max_requests_per_hour
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: max {max_requests_per_hour} requests per hour"
                )
            
            # 2. Detectar actividad sospechosa
            suspicious_indicators = endpoint_security.detect_suspicious_activity(request)
            if suspicious_indicators:
                logger.warning(
                    f"Suspicious activity detected",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    indicators=suspicious_indicators,
                    user_agent=request.headers.get("user-agent"),
                    fingerprint=endpoint_security.generate_request_fingerprint(request)
                )
                
                # Si hay múltiples indicadores, bloquear
                if len(suspicious_indicators) >= 2:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Suspicious activity detected"
                    )
            
            # 3. Log de acceso de auditoría
            if log_access:
                logger.info(
                    f"Endpoint access",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    method=request.method,
                    user_agent=request.headers.get("user-agent"),
                    fingerprint=endpoint_security.generate_request_fingerprint(request)
                )
            
            # 4. Ejecutar función original
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_json_input(max_size: int = 1024 * 1024):  # 1MB por defecto
    """Decorador para validar input JSON"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar request
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request and request.method in ["POST", "PUT", "PATCH"]:
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > max_size:
                    logger.warning(
                        f"JSON payload too large",
                        client_ip=request.client.host,
                        content_length=content_length,
                        max_size=max_size
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Payload too large. Maximum size: {max_size} bytes"
                    )
            
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        return wrapper
    return decorator


def admin_required(func: Callable) -> Callable:
    """Decorador para endpoints que requieren permisos de administrador"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Este decorador se combina con get_current_admin_user en las dependencias
        # Solo registra el acceso a endpoint administrativo
        
        # Buscar request
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if request:
            logger.info(
                f"Admin endpoint accessed",
                client_ip=request.client.host,
                endpoint=request.url.path,
                method=request.method
            )
        
        return func(*args, **kwargs)
    
    return wrapper


def sanitize_query_params(*param_names: str):
    """Decorador para sanitizar parámetros de query específicos"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for param_name in param_names:
                if param_name in kwargs and kwargs[param_name] is not None:
                    try:
                        kwargs[param_name] = InputValidator.validate_input(
                            str(kwargs[param_name]), 
                            'alphanumeric', 
                            max_length=100
                        )
                    except HTTPException as e:
                        logger.warning(
                            f"Invalid query parameter",
                            param_name=param_name,
                            param_value=kwargs[param_name],
                            error=e.detail
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid parameter '{param_name}': {e.detail}"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Importar asyncio para verificación de funciones asíncronas
import asyncio