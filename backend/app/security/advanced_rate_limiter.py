"""
Sistema avanzado de rate limiting con múltiples estrategias
"""
import time
import redis
import hashlib
import json
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
from fastapi import Request, HTTPException, status
from enum import Enum

from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class LimitType(Enum):
    """Tipos de límites de rate limiting"""
    REQUEST_COUNT = "request_count"
    BANDWIDTH = "bandwidth"
    CONCURRENT = "concurrent"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimit:
    """Configuración de rate limit"""
    requests: int
    window: int  # segundos
    limit_type: LimitType = LimitType.SLIDING_WINDOW
    burst: int = 0  # Para token bucket
    block_duration: int = 0  # Duración del bloqueo en segundos


@dataclass
class RateLimitResult:
    """Resultado de verificación de rate limit"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit_type: str = ""
    current_usage: int = 0


class AdvancedRateLimiter:
    """Rate limiter avanzado con múltiples estrategias"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client or self._get_redis_client()
        self.enabled = settings.rate_limit_enabled
        
        # Configuraciones específicas por endpoint y tipo de usuario
        self.limits = self._load_rate_limits()
        
        # Cache local para performance
        self.local_cache = {}
        self.cache_ttl = 60  # 1 minuto
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Obtener cliente Redis"""
        try:
            client = redis.from_url(settings.redis_url)
            client.ping()
            return client
        except Exception as e:
            logger.error(f"Redis connection failed for advanced rate limiter: {e}")
            return None
    
    def _load_rate_limits(self) -> Dict[str, Dict[str, RateLimit]]:
        """Cargar configuraciones de rate limiting"""
        is_prod = settings.is_production
        
        return {
            # Autenticación - muy restrictivo
            "auth": {
                "login": RateLimit(
                    requests=3 if is_prod else 10,
                    window=300,
                    limit_type=LimitType.SLIDING_WINDOW,
                    block_duration=900  # 15 min bloqueo tras exceder
                ),
                "refresh": RateLimit(
                    requests=5 if is_prod else 20,
                    window=300,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=2
                ),
                "logout": RateLimit(
                    requests=10 if is_prod else 30,
                    window=300
                )
            },
            
            # Administración - restrictivo
            "admin": {
                "user_creation": RateLimit(
                    requests=2 if is_prod else 5,
                    window=3600,
                    block_duration=3600
                ),
                "product_creation": RateLimit(
                    requests=5 if is_prod else 20,
                    window=1800
                ),
                "system_config": RateLimit(
                    requests=1 if is_prod else 3,
                    window=3600,
                    block_duration=1800
                )
            },
            
            # Búsquedas - moderado con burst
            "search": {
                "product_search": RateLimit(
                    requests=30 if is_prod else 100,
                    window=300,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=10
                ),
                "autocomplete": RateLimit(
                    requests=50 if is_prod else 200,
                    window=300,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=20
                )
            },
            
            # POS y ventas - generoso para operaciones
            "pos": {
                "add_to_cart": RateLimit(
                    requests=100 if is_prod else 500,
                    window=3600,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=20
                ),
                "process_sale": RateLimit(
                    requests=20 if is_prod else 100,
                    window=3600
                ),
                "inventory_check": RateLimit(
                    requests=200 if is_prod else 1000,
                    window=3600,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=50
                )
            },
            
            # APIs de lectura - generoso
            "read": {
                "product_list": RateLimit(
                    requests=200 if is_prod else 1000,
                    window=3600,
                    limit_type=LimitType.TOKEN_BUCKET,
                    burst=50
                ),
                "dashboard": RateLimit(
                    requests=50 if is_prod else 200,
                    window=300,
                    burst=10
                )
            },
            
            # Monitoreo - muy restrictivo
            "monitoring": {
                "metrics": RateLimit(
                    requests=5 if is_prod else 20,
                    window=300
                ),
                "health_check": RateLimit(
                    requests=60 if is_prod else 300,
                    window=60  # 1 check por segundo
                ),
                "logs": RateLimit(
                    requests=10 if is_prod else 50,
                    window=300
                )
            }
        }
    
    def get_limit_key(self, identifier: str, endpoint: str, limit_category: str, limit_name: str) -> str:
        """Generar clave única para el límite"""
        key_data = f"{identifier}:{endpoint}:{limit_category}:{limit_name}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"rate_limit:{key_hash}"
    
    def classify_endpoint(self, request: Request) -> Tuple[str, str]:
        """Clasificar endpoint para determinar límites aplicables"""
        path = request.url.path.lower()
        method = request.method.upper()
        
        # Autenticación
        if "/token" in path or "/login" in path:
            return "auth", "login"
        elif "/refresh" in path:
            return "auth", "refresh"
        elif "/logout" in path:
            return "auth", "logout"
        
        # Administración
        elif "/users/" in path and method == "POST":
            return "admin", "user_creation"
        elif "/products/" in path and method == "POST":
            return "admin", "product_creation"
        elif "/cache/clear" in path or "/config" in path:
            return "admin", "system_config"
        
        # Búsquedas
        elif "/search" in path:
            return "search", "product_search"
        elif "/suggest" in path or "/autocomplete" in path:
            return "search", "autocomplete"
        
        # POS
        elif "/pos/" in path and "cart" in path:
            return "pos", "add_to_cart"
        elif "/pos/" in path and "sale" in path:
            return "pos", "process_sale"
        elif "/products" in path and method == "GET":
            return "pos", "inventory_check"
        
        # Lectura
        elif method == "GET" and "/dashboard" in path:
            return "read", "dashboard"
        elif method == "GET" and "/products" in path:
            return "read", "product_list"
        
        # Monitoreo
        elif "/metrics" in path:
            return "monitoring", "metrics"
        elif "/health" in path:
            return "monitoring", "health_check"
        elif "/logs" in path:
            return "monitoring", "logs"
        
        # Default para otros endpoints
        return "read", "product_list"
    
    def get_user_identifier(self, request: Request) -> str:
        """Obtener identificador del usuario para rate limiting"""
        # Priorizar user_id si está autenticado
        if hasattr(request.state, 'user_id') and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Usar IP como fallback
        client_ip = request.client.host
        
        # Considerar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        
        return f"ip:{client_ip}"
    
    def sliding_window_check(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Implementar sliding window rate limiting"""
        if not self.redis_client:
            return RateLimitResult(allowed=True, remaining=limit.requests, reset_time=int(time.time()) + limit.window)
        
        current_time = int(time.time())
        window_start = current_time - limit.window
        
        try:
            pipe = self.redis_client.pipeline()
            
            # Limpiar entradas antiguas
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Contar requests actuales
            pipe.zcard(key)
            
            # Agregar request actual si está permitido
            pipe.zadd(key, {str(current_time): current_time})
            
            # Establecer TTL
            pipe.expire(key, limit.window)
            
            results = pipe.execute()
            current_count = results[1]
            
            # Si excede el límite, remover la entrada que acabamos de agregar
            if current_count >= limit.requests:
                self.redis_client.zrem(key, str(current_time))
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + limit.window,
                    retry_after=limit.block_duration if limit.block_duration > 0 else limit.window,
                    limit_type="sliding_window",
                    current_usage=current_count
                )
            
            return RateLimitResult(
                allowed=True,
                remaining=max(0, limit.requests - current_count - 1),
                reset_time=current_time + limit.window,
                limit_type="sliding_window",
                current_usage=current_count + 1
            )
            
        except Exception as e:
            logger.error(f"Sliding window rate limit error: {e}")
            return RateLimitResult(allowed=True, remaining=limit.requests, reset_time=current_time + limit.window)
    
    def token_bucket_check(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Implementar token bucket rate limiting"""
        if not self.redis_client:
            return RateLimitResult(allowed=True, remaining=limit.requests, reset_time=int(time.time()) + limit.window)
        
        current_time = int(time.time())
        bucket_key = f"{key}:bucket"
        
        try:
            # Obtener estado actual del bucket
            bucket_data = self.redis_client.get(bucket_key)
            
            if bucket_data:
                bucket_info = json.loads(bucket_data)
                last_refill = bucket_info['last_refill']
                tokens = bucket_info['tokens']
            else:
                last_refill = current_time
                tokens = limit.requests
            
            # Calcular tokens a agregar basado en tiempo transcurrido
            time_passed = current_time - last_refill
            tokens_to_add = time_passed * (limit.requests / limit.window)
            tokens = min(limit.requests, tokens + tokens_to_add)
            
            # Verificar si hay tokens disponibles
            if tokens >= 1:
                tokens -= 1
                allowed = True
                remaining = int(tokens)
            else:
                allowed = False
                remaining = 0
            
            # Actualizar bucket
            bucket_info = {
                'tokens': tokens,
                'last_refill': current_time
            }
            self.redis_client.setex(bucket_key, limit.window, json.dumps(bucket_info))
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=current_time + int((1 - tokens) * (limit.window / limit.requests)),
                limit_type="token_bucket",
                current_usage=limit.requests - remaining
            )
            
        except Exception as e:
            logger.error(f"Token bucket rate limit error: {e}")
            return RateLimitResult(allowed=True, remaining=limit.requests, reset_time=current_time + limit.window)
    
    def check_rate_limit(self, request: Request) -> RateLimitResult:
        """Verificar rate limit para un request"""
        if not self.enabled:
            return RateLimitResult(allowed=True, remaining=1000, reset_time=int(time.time()) + 3600)
        
        # Clasificar endpoint
        limit_category, limit_name = self.classify_endpoint(request)
        
        # Obtener configuración de límite
        if limit_category not in self.limits or limit_name not in self.limits[limit_category]:
            # Usar límite por defecto
            limit = RateLimit(requests=100, window=3600)
        else:
            limit = self.limits[limit_category][limit_name]
        
        # Obtener identificador de usuario
        identifier = self.get_user_identifier(request)
        
        # Generar clave de rate limit
        key = self.get_limit_key(identifier, request.url.path, limit_category, limit_name)
        
        # Aplicar algoritmo específico
        if limit.limit_type == LimitType.TOKEN_BUCKET:
            result = self.token_bucket_check(key, limit)
        else:  # SLIDING_WINDOW por defecto
            result = self.sliding_window_check(key, limit)
        
        # Log si se excede el límite
        if not result.allowed:
            logger.warning(
                f"Advanced rate limit exceeded",
                identifier=identifier,
                endpoint=request.url.path,
                limit_category=limit_category,
                limit_name=limit_name,
                current_usage=result.current_usage,
                limit_requests=limit.requests,
                limit_window=limit.window,
                user_agent=request.headers.get("user-agent", "unknown")
            )
        
        return result
    
    def is_blocked(self, identifier: str) -> bool:
        """Verificar si un identificador está bloqueado"""
        if not self.redis_client:
            return False
        
        block_key = f"blocked:{identifier}"
        return self.redis_client.exists(block_key) > 0
    
    def block_identifier(self, identifier: str, duration: int, reason: str = "rate_limit_exceeded"):
        """Bloquear un identificador por un tiempo determinado"""
        if not self.redis_client:
            return
        
        block_key = f"blocked:{identifier}"
        block_data = {
            "blocked_at": int(time.time()),
            "duration": duration,
            "reason": reason
        }
        
        self.redis_client.setex(block_key, duration, json.dumps(block_data))
        
        logger.warning(
            f"Identifier blocked",
            identifier=identifier,
            duration=duration,
            reason=reason
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del rate limiter"""
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            # Contar claves activas
            rate_limit_keys = len(self.redis_client.keys("rate_limit:*"))
            blocked_keys = len(self.redis_client.keys("blocked:*"))
            bucket_keys = len(self.redis_client.keys("*:bucket"))
            
            return {
                "active_rate_limits": rate_limit_keys,
                "blocked_identifiers": blocked_keys,
                "token_buckets": bucket_keys,
                "total_categories": len(self.limits),
                "redis_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limiter stats: {e}")
            return {"error": str(e)}


# Instancia global
advanced_rate_limiter = AdvancedRateLimiter()


# Middleware para usar el rate limiter avanzado
class AdvancedRateLimitMiddleware:
    """Middleware que usa el rate limiter avanzado"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Crear request object
        from fastapi import Request
        request = Request(scope, receive)
        
        # Verificar si está bloqueado
        identifier = advanced_rate_limiter.get_user_identifier(request)
        if advanced_rate_limiter.is_blocked(identifier):
            response = {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"x-blocked", b"true"]
                ]
            }
            await send(response)
            
            body = {
                "type": "http.response.body",
                "body": b'{"detail": "Identifier temporarily blocked due to rate limit violations"}'
            }
            await send(body)
            return
        
        # Verificar rate limit
        result = advanced_rate_limiter.check_rate_limit(request)
        
        if not result.allowed:
            # Si tiene block_duration configurado, bloquear el identificador
            limit_category, limit_name = advanced_rate_limiter.classify_endpoint(request)
            if (limit_category in advanced_rate_limiter.limits and 
                limit_name in advanced_rate_limiter.limits[limit_category]):
                limit_config = advanced_rate_limiter.limits[limit_category][limit_name]
                if limit_config.block_duration > 0:
                    advanced_rate_limiter.block_identifier(
                        identifier, 
                        limit_config.block_duration, 
                        f"rate_limit_exceeded_{limit_category}_{limit_name}"
                    )
            
            response = {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"x-ratelimit-limit", str(result.current_usage + result.remaining).encode()],
                    [b"x-ratelimit-remaining", str(result.remaining).encode()],
                    [b"x-ratelimit-reset", str(result.reset_time).encode()],
                    [b"retry-after", str(result.retry_after or 60).encode()]
                ]
            }
            await send(response)
            
            body = {
                "type": "http.response.body",
                "body": json.dumps({
                    "detail": "Rate limit exceeded",
                    "limit_type": result.limit_type,
                    "remaining": result.remaining,
                    "reset_time": result.reset_time,
                    "retry_after": result.retry_after
                }).encode()
            }
            await send(body)
            return
        
        # Continuar con la aplicación
        await self.app(scope, receive, send)