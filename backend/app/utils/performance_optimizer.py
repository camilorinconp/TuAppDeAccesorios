# ==================================================================
# OPTIMIZADOR DE PERFORMANCE - CACHÉ Y OPTIMIZACIONES AVANZADAS
# ==================================================================

from typing import Optional, Dict, Any, List, Union
from functools import wraps
import time
import json
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..cache import cache_manager
from ..logging_config import get_logger

logger = get_logger(__name__)


class PerformanceOptimizer:
    """Optimizador centralizado de performance"""
    
    @staticmethod
    def optimize_database_session(db: Session):
        """Optimiza una sesión de base de datos"""
        
        try:
            # Configurar parámetros de performance para la sesión
            optimizations = [
                "SET work_mem = '256MB'",
                "SET effective_cache_size = '1GB'", 
                "SET random_page_cost = 1.1",
                "SET effective_io_concurrency = 200"
            ]
            
            for optimization in optimizations:
                try:
                    db.execute(text(optimization))
                except Exception as e:
                    logger.debug(f"Optimización DB no aplicada: {optimization} - {str(e)}")
                    continue
                    
            logger.debug("Optimizaciones de sesión DB aplicadas")
            
        except Exception as e:
            logger.warning(f"Error aplicando optimizaciones DB: {str(e)}")
    
    @staticmethod
    def analyze_query_performance(db: Session, query: str, params: Dict = None) -> Dict[str, Any]:
        """Analiza el performance de una query SQL"""
        
        try:
            # Ejecutar EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            if params:
                result = db.execute(text(explain_query), params)
            else:
                result = db.execute(text(explain_query))
            
            explain_result = result.fetchone()[0]
            
            # Extraer métricas clave
            plan = explain_result[0]
            execution_time = plan.get('Execution Time', 0)
            planning_time = plan.get('Planning Time', 0)
            total_cost = plan.get('Plan', {}).get('Total Cost', 0)
            
            return {
                'execution_time_ms': execution_time,
                'planning_time_ms': planning_time,
                'total_cost': total_cost,
                'full_plan': explain_result,
                'recommendations': PerformanceOptimizer._generate_query_recommendations(plan)
            }
            
        except Exception as e:
            logger.error(f"Error analizando performance de query: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def _generate_query_recommendations(plan: Dict) -> List[str]:
        """Genera recomendaciones basadas en el plan de ejecución"""
        
        recommendations = []
        
        try:
            plan_node = plan.get('Plan', {})
            node_type = plan_node.get('Node Type', '')
            
            # Detectar problemas comunes
            if 'Seq Scan' in node_type:
                recommendations.append("Considerar agregar índice para evitar Sequential Scan")
            
            if plan_node.get('Rows Removed by Filter', 0) > 0:
                recommendations.append("Filtros ineficientes - considerar mejorar condiciones WHERE")
            
            if plan.get('Execution Time', 0) > 1000:  # > 1 segundo
                recommendations.append("Query lenta - considerar optimización o particionado")
            
            # Revisar nodos hijos recursivamente
            for subplan in plan_node.get('Plans', []):
                recommendations.extend(PerformanceOptimizer._generate_query_recommendations({'Plan': subplan}))
                
        except Exception as e:
            logger.debug(f"Error generando recomendaciones: {str(e)}")
        
        return list(set(recommendations))  # Remover duplicados


class AdvancedCache:
    """Sistema de caché avanzado con múltiples niveles"""
    
    @staticmethod
    def multi_level_cache(
        cache_key: str,
        ttl_memory: int = 300,  # 5 minutos en memoria
        ttl_redis: int = 3600,  # 1 hora en Redis
        compression: bool = True
    ):
        """Decorador para caché multi-nivel (memoria + Redis)"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generar clave única basada en función y argumentos
                full_key = AdvancedCache._generate_cache_key(cache_key, func.__name__, args, kwargs)
                
                # Nivel 1: Caché en memoria (más rápido)
                memory_result = AdvancedCache._get_from_memory_cache(full_key)
                if memory_result is not None:
                    logger.debug(f"Cache hit (memory): {full_key}")
                    return memory_result
                
                # Nivel 2: Caché en Redis
                redis_result = AdvancedCache._get_from_redis_cache(full_key, compression)
                if redis_result is not None:
                    logger.debug(f"Cache hit (redis): {full_key}")
                    # Guardar en memoria para próximas consultas
                    AdvancedCache._set_memory_cache(full_key, redis_result, ttl_memory)
                    return redis_result
                
                # Nivel 3: Ejecutar función y cachear resultado
                logger.debug(f"Cache miss: {full_key}")
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Guardar en ambos niveles si la ejecución fue costosa (> 100ms)
                if execution_time > 0.1:
                    AdvancedCache._set_memory_cache(full_key, result, ttl_memory)
                    AdvancedCache._set_redis_cache(full_key, result, ttl_redis, compression)
                    
                    logger.debug(f"Cached result (execution_time: {execution_time:.3f}s): {full_key}")
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
        """Genera clave de caché única"""
        
        # Crear hash basado en argumentos
        args_str = str(args) + str(sorted(kwargs.items()))
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        
        return f"{prefix}:{func_name}:{args_hash}"
    
    @staticmethod
    def _get_from_memory_cache(key: str) -> Any:
        """Obtiene valor del caché en memoria"""
        
        try:
            # Implementación simple con diccionario global (en producción usar algo como Redis)
            if not hasattr(AdvancedCache, '_memory_cache'):
                AdvancedCache._memory_cache = {}
            
            cache_entry = AdvancedCache._memory_cache.get(key)
            if cache_entry:
                if cache_entry['expires'] > time.time():
                    return cache_entry['value']
                else:
                    # Expirado, remover
                    del AdvancedCache._memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.debug(f"Error accessing memory cache: {str(e)}")
            return None
    
    @staticmethod
    def _set_memory_cache(key: str, value: Any, ttl: int):
        """Guarda valor en caché en memoria"""
        
        try:
            if not hasattr(AdvancedCache, '_memory_cache'):
                AdvancedCache._memory_cache = {}
            
            AdvancedCache._memory_cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            
            # Limpiar entradas expiradas ocasionalmente
            if len(AdvancedCache._memory_cache) > 1000:
                AdvancedCache._cleanup_memory_cache()
                
        except Exception as e:
            logger.debug(f"Error setting memory cache: {str(e)}")
    
    @staticmethod
    def _get_from_redis_cache(key: str, compression: bool = True) -> Any:
        """Obtiene valor del caché Redis"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if not redis_client:
                return None
            
            cached_data = redis_client.get(key)
            if cached_data:
                if compression:
                    import gzip
                    import pickle
                    return pickle.loads(gzip.decompress(cached_data))
                else:
                    import json
                    return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error accessing Redis cache: {str(e)}")
            return None
    
    @staticmethod
    def _set_redis_cache(key: str, value: Any, ttl: int, compression: bool = True):
        """Guarda valor en caché Redis"""
        
        try:
            redis_client = cache_manager.get_sync_client()
            if not redis_client:
                return
            
            if compression:
                import gzip
                import pickle
                data = gzip.compress(pickle.dumps(value))
            else:
                import json
                data = json.dumps(value, default=str)
            
            redis_client.setex(key, ttl, data)
            
        except Exception as e:
            logger.debug(f"Error setting Redis cache: {str(e)}")
    
    @staticmethod
    def _cleanup_memory_cache():
        """Limpia entradas expiradas del caché en memoria"""
        
        try:
            if not hasattr(AdvancedCache, '_memory_cache'):
                return
            
            current_time = time.time()
            expired_keys = [
                key for key, entry in AdvancedCache._memory_cache.items()
                if entry['expires'] <= current_time
            ]
            
            for key in expired_keys:
                del AdvancedCache._memory_cache[key]
            
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            logger.debug(f"Error cleaning memory cache: {str(e)}")


class QueryOptimizer:
    """Optimizador específico para queries de base de datos"""
    
    @staticmethod
    def optimize_product_queries(db: Session):
        """Optimiza queries específicas de productos"""
        
        try:
            # Actualizar estadísticas de la tabla products
            db.execute(text("ANALYZE products"))
            
            # Verificar y crear índices faltantes
            missing_indexes = QueryOptimizer._check_missing_indexes(db)
            for index_sql in missing_indexes:
                try:
                    db.execute(text(index_sql))
                    db.commit()
                    logger.info(f"Índice creado: {index_sql}")
                except Exception as e:
                    logger.warning(f"No se pudo crear índice: {str(e)}")
                    db.rollback()
            
            logger.info("Optimización de queries de productos completada")
            
        except Exception as e:
            logger.error(f"Error optimizando queries de productos: {str(e)}")
    
    @staticmethod
    def _check_missing_indexes(db: Session) -> List[str]:
        """Verifica índices faltantes y sugiere crearlos"""
        
        suggested_indexes = []
        
        try:
            # Verificar si existen índices específicos
            index_checks = [
                {
                    'name': 'idx_products_selling_price_stock',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_selling_price_stock ON products(selling_price, stock_quantity)',
                    'check': "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_products_selling_price_stock'"
                },
                {
                    'name': 'idx_products_name_gin',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_name_gin ON products USING gin(to_tsvector(\'spanish\', name))',
                    'check': "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_products_name_gin'"
                },
                {
                    'name': 'idx_pos_transactions_time_user',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pos_transactions_time_user ON point_of_sale_transactions(transaction_time, user_id)',
                    'check': "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_pos_transactions_time_user'"
                }
            ]
            
            for index_info in index_checks:
                try:
                    result = db.execute(text(index_info['check'])).fetchone()
                    if not result:
                        suggested_indexes.append(index_info['sql'])
                except Exception:
                    # Si no puede verificar, mejor sugerir crear el índice
                    suggested_indexes.append(index_info['sql'])
            
        except Exception as e:
            logger.debug(f"Error verificando índices: {str(e)}")
        
        return suggested_indexes


class PerformanceMonitor:
    """Monitor de performance en tiempo real"""
    
    @staticmethod
    def track_endpoint_performance(endpoint_name: str):
        """Decorador para trackear performance de endpoints"""
        
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await PerformanceMonitor._execute_with_tracking(
                    func, args, kwargs, endpoint_name, True
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return PerformanceMonitor._execute_with_tracking(
                    func, args, kwargs, endpoint_name, False
                )
            
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    async def _execute_with_tracking(func, args, kwargs, endpoint_name: str, is_async: bool):
        """Ejecuta función con tracking de performance"""
        
        start_time = time.time()
        start_memory = PerformanceMonitor._get_memory_usage()
        
        try:
            # Ejecutar función
            if is_async:
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Calcular métricas
            execution_time = time.time() - start_time
            end_memory = PerformanceMonitor._get_memory_usage()
            memory_delta = end_memory - start_memory
            
            # Registrar métricas
            PerformanceMonitor._record_performance_metrics(
                endpoint_name=endpoint_name,
                execution_time=execution_time,
                memory_delta=memory_delta,
                success=True
            )
            
            # Log si es particularmente lento
            if execution_time > 1.0:  # > 1 segundo
                logger.warning(
                    f"Endpoint lento detectado",
                    endpoint=endpoint_name,
                    execution_time=execution_time,
                    memory_delta=memory_delta
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Registrar error
            PerformanceMonitor._record_performance_metrics(
                endpoint_name=endpoint_name,
                execution_time=execution_time,
                memory_delta=0,
                success=False,
                error=str(e)
            )
            
            raise e
    
    @staticmethod
    def _get_memory_usage() -> float:
        """Obtiene uso actual de memoria en MB"""
        
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
        except:
            return 0.0
    
    @staticmethod
    def _record_performance_metrics(
        endpoint_name: str,
        execution_time: float,
        memory_delta: float,
        success: bool,
        error: str = None
    ):
        """Registra métricas de performance"""
        
        try:
            # Usar el sistema de métricas existente
            from ..metrics import metrics_registry
            
            # Registrar tiempo de ejecución
            metrics_registry.record_request_duration(
                endpoint=endpoint_name,
                method="GET",  # Simplificado
                status_code=200 if success else 500,
                duration=execution_time
            )
            
            # Log estructurado para análisis
            logger.info(
                "endpoint_performance",
                endpoint=endpoint_name,
                execution_time_ms=execution_time * 1000,
                memory_delta_mb=memory_delta,
                success=success,
                error=error
            )
            
        except Exception as e:
            logger.debug(f"Error registrando métricas de performance: {str(e)}")


# Decoradores específicos para casos comunes
def cache_expensive_operation(ttl: int = 3600, compression: bool = True):
    """Decorador para cachear operaciones costosas"""
    return AdvancedCache.multi_level_cache(
        cache_key="expensive_ops",
        ttl_memory=min(ttl // 10, 300),  # 10% del TTL en memoria, máximo 5 min
        ttl_redis=ttl,
        compression=compression
    )


def optimize_db_session(func):
    """Decorador para optimizar sesiones de base de datos"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Buscar Session en argumentos
        db_session = None
        for arg in args:
            if isinstance(arg, Session):
                db_session = arg
                break
        
        if not db_session and 'db' in kwargs:
            db_session = kwargs['db']
        
        # Aplicar optimizaciones si encontramos una sesión
        if db_session:
            PerformanceOptimizer.optimize_database_session(db_session)
        
        return func(*args, **kwargs)
    
    return wrapper


def monitor_performance(endpoint_name: str = None):
    """Decorador para monitorear performance de funciones"""
    
    def decorator(func):
        name = endpoint_name or f"{func.__module__}.{func.__name__}"
        return PerformanceMonitor.track_endpoint_performance(name)(func)
    
    return decorator