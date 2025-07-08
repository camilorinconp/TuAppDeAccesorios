"""
Rate limiting middleware para prevenir ataques de fuerza bruta y DoS
"""
import time
import redis
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Rate limiter usando Redis como backend"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis_client = None
        self.enabled = settings.rate_limit_enabled
    
    @property
    def redis_client(self):
        if self._redis_client is None and self.enabled:
            try:
                # Extraer password de la URL si existe
                if ":" in self.redis_url and "@" in self.redis_url:
                    # Format: redis://:password@host:port/db
                    parts = self.redis_url.split("@")
                    auth_part = parts[0].split(":")[-1]
                    host_part = parts[1]
                    self._redis_client = redis.from_url(self.redis_url)
                else:
                    self._redis_client = redis.from_url(self.redis_url)
                
                # Test connection
                self._redis_client.ping()
                logger.info("Rate limiter connected to Redis")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis for rate limiting: {e}")
                self.enabled = False
                self._redis_client = None
        
        return self._redis_client
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, Dict[str, int]]:
        """
        Verifica si la request está permitida bajo los límites de rate limiting
        
        Args:
            identifier: Identificador único (IP, user_id, etc.)
            limit: Número máximo de requests permitidas
            window: Ventana de tiempo en segundos
            
        Returns:
            (is_allowed, info) donde info contiene detalles del rate limit
        """
        if not self.enabled or not self.redis_client:
            return True, {"remaining": limit, "reset_time": int(time.time()) + window}
        
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            
            # Usar pipeline para operaciones atómicas
            pipe = self.redis_client.pipeline()
            
            # Limpiar entradas antiguas (sliding window)
            pipe.zremrangebyscore(key, 0, current_time - window)
            
            # Contar requests actuales
            pipe.zcard(key)
            
            # Agregar request actual
            pipe.zadd(key, {str(current_time): current_time})
            
            # Establecer TTL
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_count = results[1]
            
            # Calcular información del rate limit
            reset_time = current_time + window
            remaining = max(0, limit - current_count - 1)
            
            info = {
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count + 1
            }
            
            if current_count >= limit:
                logger.warning(
                    f"Rate limit exceeded",
                    identifier=identifier,
                    current_count=current_count,
                    limit=limit,
                    window=window
                )
                return False, info
            
            return True, info
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # En caso de error, permitir la request (fail open)
            return True, {"remaining": limit, "reset_time": int(time.time()) + window}
    
    def get_identifier(self, request: Request) -> str:
        """Genera identificador único para rate limiting"""
        
        # Priorizar user_id si está autenticado
        if hasattr(request.state, 'user_id') and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Usar IP como fallback
        client_ip = request.client.host
        
        # Considerar headers de proxy para obtener IP real
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        
        return f"ip:{client_ip}"

# Instancia global del rate limiter
rate_limiter = RateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting"""
    
    def __init__(self, app, requests_per_window: int = None, window_seconds: int = None):
        super().__init__(app)
        
        # Configuraciones específicas por endpoint
        # Límites más generosos para desarrollo, más restrictivos para producción
        is_dev = settings.environment.lower() == "development"
        
        # Rate limiting más generoso para desarrollo
        default_requests = 1000 if is_dev else 100
        default_window = 300 if is_dev else 3600
        
        self.requests_per_window = requests_per_window or default_requests
        self.window_seconds = window_seconds or default_window
        
        self.endpoint_limits = {
            # Autenticación - muy restrictivo
            "/token": {"requests": 20 if is_dev else 5, "window": 300},  # 5 min
            "/distributor-token": {"requests": 20 if is_dev else 5, "window": 300},
            "/refresh": {"requests": 30 if is_dev else 10, "window": 300},
            "/auth/logout": {"requests": 50 if is_dev else 20, "window": 300},
            
            # Endpoints administrativos - restrictivo
            "/api/users/": {"requests": 10 if is_dev else 5, "window": 3600},  # 1 hora
            "/api/users": {"requests": 50 if is_dev else 20, "window": 3600},
            "/api/distributors/": {"requests": 10 if is_dev else 5, "window": 3600},
            "/api/products/": {"requests": 20 if is_dev else 10, "window": 1800},  # 30 min
            
            # Búsquedas - moderado
            "/products/search": {"requests": 100 if is_dev else 50, "window": 300},
            "/products/suggest-names": {"requests": 200 if is_dev else 100, "window": 300},
            
            # POS y ventas - generoso para operaciones normales
            "/pos/": {"requests": 500 if is_dev else 200, "window": 3600},
            "/pos/sales": {"requests": 200 if is_dev else 100, "window": 3600},
            
            # APIs de lectura - generoso
            "/products": {"requests": 1000 if is_dev else 500, "window": 3600},
            "/products/": {"requests": 1000 if is_dev else 500, "window": 3600},
            "/api/dashboard": {"requests": 200 if is_dev else 100, "window": 3600},
            
            # Métricas y monitoreo - muy restrictivo
            "/metrics": {"requests": 10 if is_dev else 5, "window": 300},
            "/api/audit": {"requests": 20 if is_dev else 10, "window": 3600},
            
            # Cache admin - muy restrictivo
            "/api/cache/clear": {"requests": 5 if is_dev else 2, "window": 3600},
            "/api/cache/stats": {"requests": 20 if is_dev else 10, "window": 300},
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Obtener configuración específica del endpoint
        # Intentar match exacto primero, luego por patrón
        endpoint_config = self.endpoint_limits.get(request.url.path)
        
        if not endpoint_config:
            # Buscar por patrones (ej: /api/products/123 -> /api/products/)
            for pattern, config in self.endpoint_limits.items():
                if pattern.endswith('/') and request.url.path.startswith(pattern):
                    endpoint_config = config
                    break
                elif '/' in pattern and pattern.rstrip('/') in request.url.path:
                    endpoint_config = config
                    break
        
        if endpoint_config:
            limit = endpoint_config["requests"]
            window = endpoint_config["window"]
        else:
            limit = self.requests_per_window
            window = self.window_seconds
        
        # Generar identificador
        identifier = rate_limiter.get_identifier(request)
        
        # Verificar rate limit
        is_allowed, info = rate_limiter.is_allowed(identifier, limit, window)
        
        if not is_allowed:
            # Log del rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                endpoint=request.url.path,
                method=request.method,
                limit=limit,
                window=window,
                current_count=info.get("current_count", 0)
            )
            
            # Retornar error 429 Too Many Requests
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Too many requests. Please try again later.",
                    "limit": info["limit"],
                    "remaining": info["remaining"],
                    "reset_time": info["reset_time"]
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset_time"]),
                    "Retry-After": str(window)
                }
            )
        
        # Procesar request normal
        response = await call_next(request)
        
        # Agregar headers de rate limit a la respuesta
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
        
        return response

# Funciones de utilidad para rate limiting manual

def check_rate_limit(identifier: str, limit: int = None, window: int = None) -> tuple[bool, Dict]:
    """
    Función utilitaria para verificar rate limits manualmente
    """
    limit = limit or settings.rate_limit_requests
    window = window or settings.rate_limit_window
    
    return rate_limiter.is_allowed(identifier, limit, window)

def rate_limit_user(user_id: int, limit: int = 100, window: int = 3600) -> tuple[bool, Dict]:
    """Rate limit específico para un usuario"""
    return check_rate_limit(f"user:{user_id}", limit, window)

def rate_limit_ip(ip_address: str, limit: int = 100, window: int = 3600) -> tuple[bool, Dict]:
    """Rate limit específico para una IP"""
    return check_rate_limit(f"ip:{ip_address}", limit, window)