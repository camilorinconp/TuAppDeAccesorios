# ==================================================================
# SISTEMA DE CACHÉ INTELIGENTE - GESTIÓN AUTOMÁTICA Y PREDICTIVA
# ==================================================================

from typing import Optional, Dict, Any, List, Union, Callable
from datetime import datetime, timedelta
import time
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from ..cache import cache_manager
from ..logging_config import get_logger
from ..models import Product

logger = get_logger(__name__)


class CachePriority(Enum):
    """Niveles de prioridad para caché"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class CacheStrategy(Enum):
    """Estrategias de caché"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    PREDICTIVE = "predictive"  # Predictivo basado en patrones


@dataclass
class CacheMetrics:
    """Métricas de caché"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    last_accessed: Optional[datetime] = None
    access_frequency: int = 0
    average_response_time: float = 0.0


class IntelligentCache:
    """Sistema de caché inteligente con gestión automática"""
    
    def __init__(self):
        self.metrics: Dict[str, CacheMetrics] = {}
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.last_cleanup = datetime.utcnow()
        
    def get(
        self, 
        key: str, 
        fetch_function: Callable = None,
        ttl: int = 3600,
        priority: CachePriority = CachePriority.MEDIUM,
        strategy: CacheStrategy = CacheStrategy.LRU
    ) -> Any:
        """
        Obtiene valor del caché con lógica inteligente
        
        Args:
            key: Clave del caché
            fetch_function: Función para obtener datos si no están en caché
            ttl: Tiempo de vida en segundos
            priority: Prioridad del elemento
            strategy: Estrategia de caché a usar
        """
        
        start_time = time.time()
        
        try:
            # Intentar obtener del caché
            cached_value = self._get_from_cache(key)
            
            if cached_value is not None:
                # Cache hit
                self._record_access(key, hit=True, response_time=time.time() - start_time)
                self._update_access_pattern(key)
                
                # Verificar si necesita pre-renovación
                self._check_preemptive_refresh(key, fetch_function, ttl)
                
                return cached_value
            
            # Cache miss - obtener datos
            if fetch_function:
                fresh_data = fetch_function()
                
                # Guardar en caché con estrategia inteligente
                self._set_in_cache(
                    key=key,
                    value=fresh_data,
                    ttl=self._calculate_intelligent_ttl(key, ttl, priority),
                    priority=priority,
                    strategy=strategy
                )
                
                response_time = time.time() - start_time
                self._record_access(key, hit=False, response_time=response_time)
                self._update_access_pattern(key)
                
                return fresh_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error en caché inteligente para clave {key}: {str(e)}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        priority: CachePriority = CachePriority.MEDIUM,
        strategy: CacheStrategy = CacheStrategy.LRU
    ):
        """Establece valor en caché con lógica inteligente"""
        
        try:
            intelligent_ttl = self._calculate_intelligent_ttl(key, ttl, priority)
            self._set_in_cache(key, value, intelligent_ttl, priority, strategy)
            
        except Exception as e:
            logger.error(f"Error estableciendo caché para clave {key}: {str(e)}")
    
    def invalidate(self, key: str):
        """Invalida entrada específica del caché"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if redis_client:
                redis_client.delete(key)
            
            # Limpiar métricas locales
            if key in self.metrics:
                del self.metrics[key]
            if key in self.access_patterns:
                del self.access_patterns[key]
                
            logger.debug(f"Caché invalidado para clave: {key}")
            
        except Exception as e:
            logger.error(f"Error invalidando caché para clave {key}: {str(e)}")
    
    def invalidate_pattern(self, pattern: str):
        """Invalida entradas del caché que coincidan con un patrón"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if redis_client:
                # Buscar claves que coincidan con el patrón
                matching_keys = redis_client.keys(pattern)
                if matching_keys:
                    redis_client.delete(*matching_keys)
                    logger.info(f"Invalidadas {len(matching_keys)} entradas con patrón: {pattern}")
            
        except Exception as e:
            logger.error(f"Error invalidando patrón {pattern}: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del sistema de caché"""
        
        try:
            total_hits = sum(m.hits for m in self.metrics.values())
            total_misses = sum(m.misses for m in self.metrics.values())
            total_requests = total_hits + total_misses
            
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            # Top claves más accedidas
            top_keys = sorted(
                self.metrics.items(),
                key=lambda x: x[1].access_frequency,
                reverse=True
            )[:10]
            
            return {
                'total_hits': total_hits,
                'total_misses': total_misses,
                'hit_rate_percent': round(hit_rate, 2),
                'total_keys': len(self.metrics),
                'top_accessed_keys': [
                    {
                        'key': key,
                        'access_frequency': metrics.access_frequency,
                        'last_accessed': metrics.last_accessed.isoformat() if metrics.last_accessed else None
                    }
                    for key, metrics in top_keys
                ],
                'cache_efficiency': self._calculate_cache_efficiency()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de caché: {str(e)}")
            return {}
    
    def cleanup_expired(self):
        """Limpia entradas expiradas y optimiza el caché"""
        
        try:
            current_time = datetime.utcnow()
            
            # Solo limpiar cada 5 minutos
            if current_time - self.last_cleanup < timedelta(minutes=5):
                return
            
            # Limpiar patrones de acceso antiguos (> 24 horas)
            cutoff_time = current_time - timedelta(hours=24)
            
            for key in list(self.access_patterns.keys()):
                self.access_patterns[key] = [
                    access_time for access_time in self.access_patterns[key]
                    if access_time > cutoff_time
                ]
                
                # Remover si no hay accesos recientes
                if not self.access_patterns[key]:
                    del self.access_patterns[key]
                    if key in self.metrics:
                        del self.metrics[key]
            
            self.last_cleanup = current_time
            logger.debug(f"Cleanup de caché completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup de caché: {str(e)}")
    
    def _get_from_cache(self, key: str) -> Any:
        """Obtiene valor del caché Redis"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if not redis_client:
                return None
            
            cached_data = redis_client.get(key)
            if cached_data:
                import pickle
                return pickle.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error obteniendo del caché {key}: {str(e)}")
            return None
    
    def _set_in_cache(
        self,
        key: str,
        value: Any,
        ttl: int,
        priority: CachePriority,
        strategy: CacheStrategy
    ):
        """Establece valor en caché Redis"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if not redis_client:
                return
            
            import pickle
            serialized_data = pickle.dumps(value)
            
            # Establecer con TTL
            redis_client.setex(key, ttl, serialized_data)
            
            # Actualizar métricas
            if key not in self.metrics:
                self.metrics[key] = CacheMetrics()
            
            self.metrics[key].size_bytes = len(serialized_data)
            
            logger.debug(f"Valor cacheado: {key} (TTL: {ttl}s, Size: {len(serialized_data)} bytes)")
            
        except Exception as e:
            logger.debug(f"Error estableciendo caché {key}: {str(e)}")
    
    def _calculate_intelligent_ttl(
        self,
        key: str,
        base_ttl: int,
        priority: CachePriority
    ) -> int:
        """Calcula TTL inteligente basado en patrones de acceso"""
        
        try:
            # TTL base según prioridad
            priority_multipliers = {
                CachePriority.CRITICAL: 2.0,
                CachePriority.HIGH: 1.5,
                CachePriority.MEDIUM: 1.0,
                CachePriority.LOW: 0.5
            }
            
            ttl = int(base_ttl * priority_multipliers[priority])
            
            # Ajustar basado en frecuencia de acceso
            if key in self.metrics:
                frequency = self.metrics[key].access_frequency
                
                # Más accesos = TTL más largo
                if frequency > 100:
                    ttl = int(ttl * 1.5)
                elif frequency > 50:
                    ttl = int(ttl * 1.2)
                elif frequency < 5:
                    ttl = int(ttl * 0.8)
            
            # Ajustar basado en patrón de acceso reciente
            if key in self.access_patterns:
                recent_accesses = len([
                    access for access in self.access_patterns[key]
                    if access > datetime.utcnow() - timedelta(hours=1)
                ])
                
                if recent_accesses > 10:
                    ttl = int(ttl * 1.3)
            
            # Límites razonables
            return max(60, min(ttl, 86400))  # Entre 1 minuto y 24 horas
            
        except Exception as e:
            logger.debug(f"Error calculando TTL inteligente: {str(e)}")
            return base_ttl
    
    def _record_access(self, key: str, hit: bool, response_time: float):
        """Registra acceso para métricas"""
        
        try:
            if key not in self.metrics:
                self.metrics[key] = CacheMetrics()
            
            metrics = self.metrics[key]
            
            if hit:
                metrics.hits += 1
            else:
                metrics.misses += 1
            
            metrics.access_frequency += 1
            metrics.last_accessed = datetime.utcnow()
            
            # Actualizar promedio de tiempo de respuesta
            if metrics.average_response_time == 0:
                metrics.average_response_time = response_time
            else:
                # Media móvil simple
                metrics.average_response_time = (
                    metrics.average_response_time * 0.9 + response_time * 0.1
                )
            
        except Exception as e:
            logger.debug(f"Error registrando acceso: {str(e)}")
    
    def _update_access_pattern(self, key: str):
        """Actualiza patrón de acceso para predicciones"""
        
        try:
            if key not in self.access_patterns:
                self.access_patterns[key] = []
            
            self.access_patterns[key].append(datetime.utcnow())
            
            # Mantener solo últimos 100 accesos para eficiencia
            if len(self.access_patterns[key]) > 100:
                self.access_patterns[key] = self.access_patterns[key][-100:]
                
        except Exception as e:
            logger.debug(f"Error actualizando patrón de acceso: {str(e)}")
    
    def _check_preemptive_refresh(self, key: str, fetch_function: Callable, ttl: int):
        """Verifica si se necesita renovación preemptiva del caché"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if not redis_client or not fetch_function:
                return
            
            # Verificar TTL restante
            remaining_ttl = redis_client.ttl(key)
            
            # Si queda menos del 20% del TTL y es una clave frecuentemente accedida
            if remaining_ttl > 0 and remaining_ttl < (ttl * 0.2):
                if key in self.metrics and self.metrics[key].access_frequency > 10:
                    
                    # Renovar en background (fire-and-forget)
                    try:
                        fresh_data = fetch_function()
                        self._set_in_cache(
                            key=key,
                            value=fresh_data,
                            ttl=ttl,
                            priority=CachePriority.MEDIUM,
                            strategy=CacheStrategy.LRU
                        )
                        
                        logger.debug(f"Renovación preemptiva para clave: {key}")
                        
                    except Exception as e:
                        logger.debug(f"Error en renovación preemptiva: {str(e)}")
            
        except Exception as e:
            logger.debug(f"Error verificando renovación preemptiva: {str(e)}")
    
    def _calculate_cache_efficiency(self) -> float:
        """Calcula eficiencia general del caché"""
        
        try:
            if not self.metrics:
                return 0.0
            
            total_hits = sum(m.hits for m in self.metrics.values())
            total_requests = sum(m.hits + m.misses for m in self.metrics.values())
            
            if total_requests == 0:
                return 0.0
            
            hit_rate = total_hits / total_requests
            
            # Penalizar por claves con pocos accesos (ruido)
            active_keys = sum(1 for m in self.metrics.values() if m.access_frequency > 2)
            key_efficiency = active_keys / len(self.metrics)
            
            # Combinar métricas para eficiencia general
            return (hit_rate * 0.7 + key_efficiency * 0.3) * 100
            
        except Exception as e:
            logger.debug(f"Error calculando eficiencia: {str(e)}")
            return 0.0


# Instancia global del caché inteligente
intelligent_cache = IntelligentCache()


class ProductCacheManager:
    """Gestor especializado de caché para productos"""
    
    @staticmethod
    def get_product(product_id: int, fetch_function: Callable = None) -> Optional[Product]:
        """Obtiene producto con caché inteligente"""
        
        key = f"product:{product_id}"
        
        return intelligent_cache.get(
            key=key,
            fetch_function=fetch_function,
            ttl=3600,  # 1 hora
            priority=CachePriority.HIGH,
            strategy=CacheStrategy.LRU
        )
    
    @staticmethod
    def get_products_list(skip: int = 0, limit: int = 20, fetch_function: Callable = None) -> Optional[List[Product]]:
        """Obtiene lista de productos con caché"""
        
        key = f"products:list:{skip}:{limit}"
        
        return intelligent_cache.get(
            key=key,
            fetch_function=fetch_function,
            ttl=1800,  # 30 minutos
            priority=CachePriority.MEDIUM,
            strategy=CacheStrategy.LRU
        )
    
    @staticmethod
    def get_search_results(query: str, limit: int = 10, fetch_function: Callable = None) -> Optional[List[Product]]:
        """Obtiene resultados de búsqueda con caché"""
        
        # Normalizar query para cache key
        normalized_query = query.lower().strip()
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:8]
        key = f"search:{query_hash}:{limit}"
        
        return intelligent_cache.get(
            key=key,
            fetch_function=fetch_function,
            ttl=900,  # 15 minutos
            priority=CachePriority.MEDIUM,
            strategy=CacheStrategy.LFU
        )
    
    @staticmethod
    def invalidate_product(product_id: int):
        """Invalida caché de un producto específico"""
        
        # Invalidar producto individual
        intelligent_cache.invalidate(f"product:{product_id}")
        
        # Invalidar listas que podrían contener este producto
        intelligent_cache.invalidate_pattern("products:list:*")
        intelligent_cache.invalidate_pattern("search:*")
        
        logger.info(f"Caché invalidado para producto: {product_id}")
    
    @staticmethod
    def invalidate_all_products():
        """Invalida todo el caché relacionado con productos"""
        
        intelligent_cache.invalidate_pattern("product:*")
        intelligent_cache.invalidate_pattern("products:*")
        intelligent_cache.invalidate_pattern("search:*")
        
        logger.info("Todo el caché de productos invalidado")
    
    @staticmethod
    def warm_up_cache(db, popular_product_ids: List[int] = None):
        """Pre-carga caché con productos populares"""
        
        try:
            from ..crud import get_product, get_products
            
            # Pre-cargar productos populares
            if popular_product_ids:
                for product_id in popular_product_ids:
                    try:
                        def fetch_product():
                            return get_product(db, product_id)
                        
                        ProductCacheManager.get_product(
                            product_id=product_id,
                            fetch_function=fetch_product
                        )
                    except Exception as e:
                        logger.debug(f"Error pre-cargando producto {product_id}: {str(e)}")
            
            # Pre-cargar primera página de productos
            def fetch_first_page():
                return get_products(db, skip=0, limit=20)
            
            ProductCacheManager.get_products_list(
                skip=0,
                limit=20,
                fetch_function=fetch_first_page
            )
            
            logger.info(f"Caché pre-cargado con {len(popular_product_ids or [])} productos populares")
            
        except Exception as e:
            logger.error(f"Error pre-cargando caché: {str(e)}")


# Funciones de conveniencia
def cache_product_operation(ttl: int = 3600, priority: CachePriority = CachePriority.MEDIUM):
    """Decorador para cachear operaciones de productos"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generar clave basada en función y argumentos
            key = f"op:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            def fetch_function():
                return func(*args, **kwargs)
            
            return intelligent_cache.get(
                key=key,
                fetch_function=fetch_function,
                ttl=ttl,
                priority=priority
            )
        
        return wrapper
    
    return decorator