"""
Middleware para manejo de errores y métricas
"""
import time
import traceback
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError

from .exceptions import AppException, convert_to_http_exception, ErrorResponse
from .logging_config import get_logger
from .metrics import metrics_registry
import logging
import hashlib
import uuid
from contextvars import ContextVar

# Context variable para el request ID
request_id_var: ContextVar[str] = ContextVar('request_id')

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware para manejo centralizado de errores"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar ID único para el request
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Agregar información del request al contexto de logging
        user_id = None
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        log_context = {
            "request_id": request_id,
            "user_id": user_id,
            "endpoint": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent", "")
        }
        
        try:
            response = await call_next(request)
            return response
            
        except AppException as exc:
            # Excepciones de la aplicación
            logger.warning(
                f"App exception: {exc.message}",
                **log_context,
                error_type=type(exc).__name__,
                error_details=exc.details
            )
            
            http_exc = convert_to_http_exception(exc)
            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail
            )
            
        except IntegrityError as exc:
            # Errores de integridad de la base de datos
            logger.error(
                f"Database integrity error: {str(exc)}",
                **log_context,
                error_type="IntegrityError"
            )
            
            error_message = "Error de integridad en la base de datos"
            if "UNIQUE constraint failed" in str(exc) or "duplicate key" in str(exc):
                error_message = "El recurso ya existe"
            elif "FOREIGN KEY constraint failed" in str(exc):
                error_message = "Referencia inválida a otro recurso"
            
            return JSONResponse(
                status_code=400,
                content={
                    "message": error_message,
                    "type": "database_integrity_error",
                    "details": {}
                }
            )
            
        except SQLAlchemyError as exc:
            # Otros errores de SQLAlchemy
            logger.error(
                f"Database error: {str(exc)}",
                **log_context,
                error_type="SQLAlchemyError"
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Error en la base de datos",
                    "type": "database_error",
                    "details": {}
                }
            )
            
        except PydanticValidationError as exc:
            # Errores de validación de Pydantic
            logger.warning(
                f"Validation error: {str(exc)}",
                **log_context,
                error_type="ValidationError",
                validation_errors=exc.errors()
            )
            
            return JSONResponse(
                status_code=422,
                content={
                    "message": "Error de validación de datos",
                    "type": "validation_error",
                    "details": {"validation_errors": exc.errors()}
                }
            )
            
        except HTTPException as exc:
            # HTTPException de FastAPI (pasamos tal como están)
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}
            )
            
        except Exception as exc:
            # Cualquier otra excepción no manejada
            logger.error(
                f"Unhandled exception: {str(exc)}",
                **log_context,
                error_type=type(exc).__name__,
                traceback=traceback.format_exc()
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Error interno del servidor",
                    "type": "internal_server_error",
                    "details": {}
                }
            )


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware para métricas de performance"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Obtener información del request
        request_id = request_id_var.get(str(uuid.uuid4()))
        user_id = getattr(request.state, 'user_id', None)
        
        # Incrementar contador de conexiones activas
        metrics_registry.set_active_connections(
            metrics_registry._active_connections.value + 1
        )
        
        try:
            # Procesar request
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Agregar header con tiempo de procesamiento
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            # Registrar métricas
            metrics_registry.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=process_time
            )
            
            # Log de métricas de performance
            logger.performance(
                f"Request processed",
                duration=process_time,
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                request_id=request_id,
                user_id=user_id,
                client_ip=request.client.host,
                user_agent=request.headers.get("user-agent", "")
            )
            
            return response
            
        finally:
            # Decrementar contador de conexiones activas
            metrics_registry.set_active_connections(
                max(0, metrics_registry._active_connections.value - 1)
            )


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Middleware para cachear respuestas HTTP"""
    
    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        
        # Importar settings aquí para evitar circular imports
        try:
            from .config import settings
            self.cache_enabled = settings.redis_cache_enabled
        except ImportError:
            self.cache_enabled = False
        
        if self.cache_enabled:
            from .cache import cache_manager
            self.cache_manager = cache_manager
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Solo cachear GET requests
        if not self.cache_enabled or request.method != "GET":
            return await call_next(request)
        
        # No cachear requests autenticados (por seguridad)
        if "Authorization" in request.headers or "Cookie" in request.headers:
            return await call_next(request)
        
        # Generar clave de caché
        cache_key = self._generate_cache_key(request)
        
        try:
            # Intentar obtener respuesta del caché
            cached_response = self.cache_manager.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {cache_key}")
                metrics_registry.record_cache_hit("http_response")
                return JSONResponse(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"],
                    headers={**cached_response["headers"], "X-Cache": "HIT"}
                )
            
            # Procesar request normal
            response = await call_next(request)
            
            # Registrar cache miss
            metrics_registry.record_cache_miss("http_response")
            
            # Cachear solo respuestas exitosas
            if response.status_code == 200 and hasattr(response, 'body'):
                response.headers["X-Cache"] = "MISS"
            
            return response
            
        except Exception as e:
            logger.error(
                f"Error in cache middleware: {e}",
                error_type=type(e).__name__,
                cache_key=cache_key if 'cache_key' in locals() else None
            )
            return await call_next(request)
    
    def _generate_cache_key(self, request: Request) -> str:
        """Genera clave única para el caché basada en la request"""
        key_data = f"http:{request.url.path}:{request.query_params}"
        return f"response_cache:{hashlib.md5(key_data.encode()).hexdigest()}"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad completos"""
    
    def __init__(self, app):
        super().__init__(app)
        # Importar settings aquí para evitar circular imports
        try:
            from .config import settings
            self.settings = settings
        except ImportError:
            self.settings = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Headers de seguridad básicos
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy - más permisivo para Swagger UI
        if request.url.path == "/docs":
            # CSP relajado para Swagger UI
            csp_policy = (
                "default-src 'self' https://cdn.jsdelivr.net; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # CSP restrictivo para el resto de la aplicación
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Permissions Policy (antes Feature-Policy)
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=(), "
            "vibrate=(), "
            "fullscreen=(self)"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # HSTS para producción
        if self.settings and (self.settings.is_production or self.settings.force_https):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Prevenir MIME sniffing
        response.headers["X-Download-Options"] = "noopen"
        
        # No almacenar en cache páginas sensibles
        if request.url.path in ["/token", "/refresh", "/admin"]:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estructurado de requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Obtener información del request
        start_time = time.time()
        request_id = request_id_var.get(str(uuid.uuid4()))
        user_id = getattr(request.state, 'user_id', None)
        
        # Log de inicio del request
        logger.info(
            f"Request started",
            request_id=request_id,
            method=request.method,
            endpoint=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            user_id=user_id
        )
        
        try:
            response = await call_next(request)
            
            # Log de finalización exitosa
            duration = time.time() - start_time
            logger.info(
                f"Request completed",
                request_id=request_id,
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_ms=duration * 1000,
                user_id=user_id
            )
            
            return response
            
        except Exception as exc:
            # Log de error
            duration = time.time() - start_time
            logger.error(
                f"Request failed",
                request_id=request_id,
                method=request.method,
                endpoint=request.url.path,
                duration_ms=duration * 1000,
                error_type=type(exc).__name__,
                error_message=str(exc),
                user_id=user_id
            )
            raise