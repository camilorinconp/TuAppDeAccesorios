"""
Sistema de caché con Redis para la aplicación
"""
import json
import pickle
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
import redis
from functools import wraps
import hashlib
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestor de caché con Redis"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.async_redis_client: Optional[redis.Redis] = None
        
    def get_sync_client(self) -> redis.Redis:
        """Obtiene cliente Redis síncrono"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # Para manejar pickle
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        return self.redis_client
    
    async def get_async_client(self) -> redis.Redis:
        """Obtiene cliente Redis asíncrono - usando cliente sync por compatibilidad"""
        if self.async_redis_client is None:
            self.async_redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self.async_redis_client
    
    def _serialize(self, data: Any) -> bytes:
        """Serializa datos para almacenar en Redis"""
        try:
            # Intentar JSON primero (más eficiente)
            if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
                return json.dumps(data, default=str).encode('utf-8')
            else:
                # Usar pickle para objetos más complejos
                return pickle.dumps(data)
        except (TypeError, ValueError):
            return pickle.dumps(data)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserializa datos desde Redis"""
        try:
            # Intentar JSON primero
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Usar pickle como fallback
            return pickle.loads(data)
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera clave única para el caché"""
        # Crear hash de los argumentos
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"cache:{prefix}:{key_hash}"
    
    def set(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Establece valor en caché (síncrono)"""
        try:
            client = self.get_sync_client()
            serialized_data = self._serialize(value)
            
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                return client.setex(key, expire, serialized_data)
            else:
                return client.set(key, serialized_data)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def get(self, key: str) -> Any:
        """Obtiene valor del caché (síncrono)"""
        try:
            client = self.get_sync_client()
            data = client.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def aset(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Establece valor en caché (asíncrono)"""
        try:
            client = await self.get_async_client()
            serialized_data = self._serialize(value)
            
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                return await client.setex(key, expire, serialized_data)
            else:
                return await client.set(key, serialized_data)
        except Exception as e:
            logger.error(f"Error setting async cache key {key}: {e}")
            return False
    
    async def aget(self, key: str) -> Any:
        """Obtiene valor del caché (asíncrono)"""
        try:
            client = await self.get_async_client()
            data = await client.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Error getting async cache key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Elimina clave del caché"""
        try:
            client = self.get_sync_client()
            return bool(client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Elimina claves que coincidan con un patrón"""
        try:
            client = self.get_sync_client()
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error deleting cache pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Verifica si existe una clave en el caché"""
        try:
            client = self.get_sync_client()
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        try:
            client = self.get_sync_client()
            info = client.info()
            return {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calcula la tasa de aciertos del caché"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
    
    def flush_all(self) -> bool:
        """Limpia todo el caché (usar con cuidado)"""
        try:
            client = self.get_sync_client()
            return client.flushdb()
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False

# Instancia global del gestor de caché
cache_manager = CacheManager()

# Decoradores para cachear funciones

def cached(
    expire: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "func",
    skip_cache: bool = False
):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        expire: Tiempo de expiración en segundos o timedelta
        key_prefix: Prefijo para la clave del caché
        skip_cache: Si es True, omite el caché (útil para debug)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if skip_cache:
                return func(*args, **kwargs)
            
            # Generar clave del caché
            cache_key = cache_manager._generate_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )
            
            # Intentar obtener del caché
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Ejecutar función y cachear resultado
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            if result is not None:  # Solo cachear si hay resultado
                cache_manager.set(cache_key, result, expire)
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Invalida caché por patrón"""
    return cache_manager.delete_pattern(pattern)

def invalidate_cache_key(key: str):
    """Invalida una clave específica del caché"""
    return cache_manager.delete(key)

# Configuraciones específicas para diferentes tipos de datos

class CacheConfig:
    """Configuraciones de caché para diferentes tipos de datos"""
    
    # Productos - caché corto debido a cambios de stock
    PRODUCTS_TTL = timedelta(minutes=5)
    PRODUCT_SEARCH_TTL = timedelta(minutes=2)
    
    # Usuarios - caché largo (cambian poco)
    USERS_TTL = timedelta(hours=1)
    
    # Distribuidores - caché medio
    DISTRIBUTORS_TTL = timedelta(minutes=30)
    
    # Reportes - caché muy corto (datos críticos)
    REPORTS_TTL = timedelta(minutes=1)
    
    # Sesiones - TTL igual al token
    SESSIONS_TTL = timedelta(minutes=15)
    
    # Configuración general
    DEFAULT_TTL = timedelta(minutes=10)

# Funciones de utilidad para caché específico

def cache_product_list(products: List, skip: int = 0, limit: int = 20):
    """Cachea lista de productos"""
    key = f"products:list:{skip}:{limit}"
    cache_manager.set(key, products, CacheConfig.PRODUCTS_TTL)

def get_cached_product_list(skip: int = 0, limit: int = 20):
    """Obtiene lista de productos del caché"""
    key = f"products:list:{skip}:{limit}"
    return cache_manager.get(key)

def invalidate_products_cache():
    """Invalida todo el caché de productos"""
    cache_manager.delete_pattern("cache:products:*")
    cache_manager.delete_pattern("cache:product_search:*")

def cache_user_session(user_id: int, session_data: Dict):
    """Cachea datos de sesión de usuario"""
    key = f"session:user:{user_id}"
    cache_manager.set(key, session_data, CacheConfig.SESSIONS_TTL)

def get_cached_user_session(user_id: int):
    """Obtiene datos de sesión del caché"""
    key = f"session:user:{user_id}"
    return cache_manager.get(key)