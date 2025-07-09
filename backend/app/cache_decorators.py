"""
Decoradores de caché específicos para endpoints de TuAppDeAccesorios
"""
from functools import wraps
from fastapi import Request
from typing import Any, Optional, Union, Callable
from datetime import timedelta
import json
import hashlib

from .cache import cache_manager, CacheConfig
from .logging_config import get_logger

logger = get_logger(__name__)

def cache_endpoint(
    ttl: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "endpoint",
    include_user: bool = False,
    include_query_params: bool = True,
    invalidate_on_methods: list = None
):
    """
    Decorador para cachear endpoints de FastAPI
    
    Args:
        ttl: Tiempo de vida del cache
        key_prefix: Prefijo para la clave del cache
        include_user: Si incluir el user_id en la clave
        include_query_params: Si incluir parámetros de consulta
        invalidate_on_methods: Métodos HTTP que invalidan el cache
    """
    if invalidate_on_methods is None:
        invalidate_on_methods = ["POST", "PUT", "DELETE", "PATCH"]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraer request del primer argumento (convención FastAPI)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Si no hay request, ejecutar función sin cache
                return await func(*args, **kwargs)
            
            # Si es método que invalida cache, limpiar y ejecutar
            if request.method in invalidate_on_methods:
                pattern = f"cache:{key_prefix}:*"
                cache_manager.delete_pattern(pattern)
                logger.info(f"Cache invalidated for pattern: {pattern}")
                return await func(*args, **kwargs)
            
            # Generar clave de cache
            cache_key = _generate_endpoint_cache_key(
                request, key_prefix, include_user, include_query_params
            )
            
            # Intentar obtener del cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for endpoint: {request.url.path}")
                return cached_result
            
            # Ejecutar función y cachear resultado
            logger.debug(f"Cache miss for endpoint: {request.url.path}")
            result = await func(*args, **kwargs)
            
            # Cachear solo respuestas exitosas
            if result is not None:
                ttl_to_use = ttl or CacheConfig.DEFAULT_TTL
                cache_manager.set(cache_key, result, ttl_to_use)
                logger.debug(f"Cached endpoint result: {cache_key}")
            
            return result
        
        return wrapper
    return decorator

def _generate_endpoint_cache_key(
    request: Request, 
    prefix: str, 
    include_user: bool, 
    include_query_params: bool
) -> str:
    """Genera clave única para cache de endpoint"""
    
    key_parts = [prefix, request.url.path, request.method]
    
    # Incluir user_id si está disponible
    if include_user and hasattr(request.state, 'user_id'):
        key_parts.append(f"user:{request.state.user_id}")
    
    # Incluir parámetros de consulta
    if include_query_params and request.query_params:
        # Ordenar parámetros para consistencia
        sorted_params = sorted(request.query_params.items())
        params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        key_parts.append(f"params:{params_str}")
    
    # Crear hash para clave más corta
    key_data = ":".join(key_parts)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    
    return f"cache:{prefix}:{key_hash}"

# Decoradores específicos para diferentes tipos de endpoints

def cache_products_list(ttl: timedelta = CacheConfig.PRODUCTS_TTL):
    """Cache para listado de productos"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="products_list",
        include_user=False,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE"]
    )

def cache_product_search(ttl: timedelta = CacheConfig.PRODUCT_SEARCH_TTL):
    """Cache para búsqueda de productos"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="product_search",
        include_user=False,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE"]
    )

def cache_user_data(ttl: timedelta = CacheConfig.USERS_TTL):
    """Cache para datos de usuario"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="user_data",
        include_user=True,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE", "PATCH"]
    )

def cache_distributors_list(ttl: timedelta = CacheConfig.DISTRIBUTORS_TTL):
    """Cache para listado de distribuidores"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="distributors_list",
        include_user=False,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE"]
    )

def cache_reports(ttl: timedelta = CacheConfig.REPORTS_TTL):
    """Cache para reportes (TTL muy corto)"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="reports",
        include_user=True,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE", "PATCH"]
    )

def cache_dashboard(ttl: timedelta = timedelta(minutes=2)):
    """Cache para dashboard (datos críticos, TTL corto)"""
    return cache_endpoint(
        ttl=ttl,
        key_prefix="dashboard",
        include_user=True,
        include_query_params=True,
        invalidate_on_methods=["POST", "PUT", "DELETE", "PATCH"]
    )

# Funciones para invalidar cache específico

def invalidate_products_cache():
    """Invalida todo el cache relacionado con productos"""
    patterns = [
        "cache:products_list:*",
        "cache:product_search:*",
        "cache:dashboard:*"  # Dashboard también muestra productos
    ]
    
    for pattern in patterns:
        deleted = cache_manager.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} keys for pattern: {pattern}")

def invalidate_users_cache():
    """Invalida todo el cache relacionado con usuarios"""
    patterns = [
        "cache:user_data:*",
        "cache:dashboard:*"
    ]
    
    for pattern in patterns:
        deleted = cache_manager.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} keys for pattern: {pattern}")

def invalidate_distributors_cache():
    """Invalida todo el cache relacionado con distribuidores"""
    patterns = [
        "cache:distributors_list:*",
        "cache:dashboard:*"
    ]
    
    for pattern in patterns:
        deleted = cache_manager.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} keys for pattern: {pattern}")

def invalidate_all_cache():
    """Invalida todo el cache de la aplicación"""
    try:
        result = cache_manager.flush_all()
        logger.info(f"Flushed all cache: {result}")
        return result
    except Exception as e:
        logger.error(f"Error flushing all cache: {e}")
        return False

# Middleware para invalidación automática

class CacheInvalidationHelper:
    """Helper para invalidación automática de cache"""
    
    @staticmethod
    def invalidate_on_product_change():
        """Invalida cache cuando cambian productos"""
        invalidate_products_cache()
    
    @staticmethod
    def invalidate_on_user_change():
        """Invalida cache cuando cambian usuarios"""
        invalidate_users_cache()
    
    @staticmethod
    def invalidate_on_distributor_change():
        """Invalida cache cuando cambian distribuidores"""
        invalidate_distributors_cache()
    
    @staticmethod
    def invalidate_on_sale():
        """Invalida cache cuando hay una venta (afecta stock y reportes)"""
        patterns = [
            "cache:products_list:*",
            "cache:dashboard:*",
            "cache:reports:*"
        ]
        
        for pattern in patterns:
            deleted = cache_manager.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} keys after sale for pattern: {pattern}")

# Instancia global del helper
cache_invalidation = CacheInvalidationHelper()