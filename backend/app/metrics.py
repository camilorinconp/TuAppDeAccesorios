"""
Sistema de métricas para monitoreo de la aplicación
"""
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from contextlib import contextmanager

@dataclass
class MetricPoint:
    """Punto de métrica individual"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class Counter:
    """Contador simple"""
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def increment(self, amount: int = 1):
        self.value += amount
    
    def reset(self):
        self.value = 0

@dataclass
class Gauge:
    """Gauge para valores que pueden subir y bajar"""
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float):
        self.value = value
    
    def increment(self, amount: float = 1.0):
        self.value += amount
    
    def decrement(self, amount: float = 1.0):
        self.value -= amount

@dataclass
class Histogram:
    """Histograma para distribución de valores"""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def observe(self, value: float):
        self.values.append(value)
    
    def get_stats(self) -> Dict[str, float]:
        if not self.values:
            return {
                'count': 0,
                'sum': 0.0,
                'min': 0.0,
                'max': 0.0,
                'avg': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0
            }
        
        sorted_values = sorted(self.values)
        count = len(sorted_values)
        total = sum(sorted_values)
        
        def percentile(p: float) -> float:
            k = (count - 1) * p
            f = int(k)
            c = k - f
            if f == count - 1:
                return sorted_values[f]
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        
        return {
            'count': count,
            'sum': total,
            'min': min(sorted_values),
            'max': max(sorted_values),
            'avg': total / count,
            'p50': percentile(0.5),
            'p95': percentile(0.95),
            'p99': percentile(0.99)
        }

class MetricsRegistry:
    """Registro central de métricas"""
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()
        
        # Métricas de sistema
        self._request_count = Counter()
        self._request_duration = Histogram()
        self._error_count = Counter()
        self._cache_hits = Counter()
        self._cache_misses = Counter()
        self._db_query_duration = Histogram()
        self._active_connections = Gauge()
        
        # Registrar métricas predefinidas
        self._counters.update({
            'http_requests_total': self._request_count,
            'http_errors_total': self._error_count,
            'cache_hits_total': self._cache_hits,
            'cache_misses_total': self._cache_misses,
        })
        
        self._histograms.update({
            'http_request_duration_seconds': self._request_duration,
            'db_query_duration_seconds': self._db_query_duration,
        })
        
        self._gauges.update({
            'active_connections': self._active_connections,
        })
    
    def counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> Counter:
        """Obtiene o crea un contador"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(tags=tags or {})
            return self._counters[name]
    
    def gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Gauge:
        """Obtiene o crea un gauge"""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(tags=tags or {})
            return self._gauges[name]
    
    def histogram(self, name: str, tags: Optional[Dict[str, str]] = None) -> Histogram:
        """Obtiene o crea un histograma"""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(tags=tags or {})
            return self._histograms[name]
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Registra métricas de una request HTTP"""
        tags = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code)
        }
        
        # Contador de requests
        self._request_count.increment()
        
        # Duración de request
        self._request_duration.observe(duration)
        
        # Contar errores
        if status_code >= 400:
            self._error_count.increment()
    
    def record_cache_hit(self, cache_type: str = "default"):
        """Registra un cache hit"""
        self._cache_hits.increment()
    
    def record_cache_miss(self, cache_type: str = "default"):
        """Registra un cache miss"""
        self._cache_misses.increment()
    
    def record_db_query(self, query_type: str, duration: float):
        """Registra métricas de consulta a base de datos"""
        self._db_query_duration.observe(duration)
    
    def set_active_connections(self, count: int):
        """Establece el número de conexiones activas"""
        self._active_connections.set(count)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtiene todas las métricas"""
        with self._lock:
            metrics = {}
            
            # Contadores
            for name, counter in self._counters.items():
                metrics[f"{name}_total"] = {
                    'type': 'counter',
                    'value': counter.value,
                    'tags': counter.tags
                }
            
            # Gauges
            for name, gauge in self._gauges.items():
                metrics[name] = {
                    'type': 'gauge',
                    'value': gauge.value,
                    'tags': gauge.tags
                }
            
            # Histogramas
            for name, histogram in self._histograms.items():
                stats = histogram.get_stats()
                for stat_name, stat_value in stats.items():
                    metrics[f"{name}_{stat_name}"] = {
                        'type': 'histogram_stat',
                        'value': stat_value,
                        'tags': histogram.tags
                    }
            
            return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas principales"""
        cache_hits = self._cache_hits.value
        cache_misses = self._cache_misses.value
        cache_total = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        request_stats = self._request_duration.get_stats()
        db_stats = self._db_query_duration.get_stats()
        
        return {
            'requests': {
                'total': self._request_count.value,
                'errors': self._error_count.value,
                'error_rate': (self._error_count.value / max(self._request_count.value, 1)) * 100,
                'avg_duration_ms': request_stats['avg'] * 1000,
                'p95_duration_ms': request_stats['p95'] * 1000
            },
            'cache': {
                'hits': cache_hits,
                'misses': cache_misses,
                'hit_rate': cache_hit_rate
            },
            'database': {
                'query_count': db_stats['count'],
                'avg_duration_ms': db_stats['avg'] * 1000,
                'p95_duration_ms': db_stats['p95'] * 1000
            },
            'system': {
                'active_connections': self._active_connections.value
            }
        }

# Instancia global del registro de métricas
metrics_registry = MetricsRegistry()

# Context managers para métricas automáticas

@contextmanager
def measure_time(histogram: Histogram):
    """Context manager para medir tiempo automáticamente"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        histogram.observe(duration)

@contextmanager
def measure_db_query(query_type: str = "unknown"):
    """Context manager para medir consultas a base de datos"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics_registry.record_db_query(query_type, duration)

# Decoradores para métricas automáticas

def measure_function_time(metric_name: str):
    """Decorador para medir tiempo de ejecución de funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            histogram = metrics_registry.histogram(metric_name)
            with measure_time(histogram):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def count_function_calls(metric_name: str):
    """Decorador para contar llamadas a funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            counter = metrics_registry.counter(metric_name)
            counter.increment()
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Funciones de utilidad para métricas de negocio

class BusinessMetrics:
    """Métricas específicas del negocio"""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        
        # Contadores de negocio
        self.sales_total = registry.counter('business_sales_total')
        self.products_created = registry.counter('business_products_created_total')
        self.products_updated = registry.counter('business_products_updated_total')
        self.user_logins = registry.counter('business_user_logins_total')
        self.distributor_logins = registry.counter('business_distributor_logins_total')
        
        # Gauges de negocio
        self.total_products = registry.gauge('business_total_products')
        self.low_stock_products = registry.gauge('business_low_stock_products')
        self.total_inventory_value = registry.gauge('business_total_inventory_value_pesos')
        
        # Histogramas de negocio
        self.sale_amounts = registry.histogram('business_sale_amount_pesos')
        self.cart_sizes = registry.histogram('business_cart_size_items')
    
    def record_sale(self, amount: float, item_count: int, user_id: Optional[int] = None):
        """Registra una venta"""
        self.sales_total.increment()
        self.sale_amounts.observe(amount)
        self.cart_sizes.observe(item_count)
    
    def record_product_created(self, user_id: Optional[int] = None):
        """Registra creación de producto"""
        self.products_created.increment()
    
    def record_product_updated(self, user_id: Optional[int] = None):
        """Registra actualización de producto"""
        self.products_updated.increment()
    
    def record_user_login(self, user_id: int, user_type: str = "user"):
        """Registra login de usuario"""
        if user_type == "distributor":
            self.distributor_logins.increment()
        else:
            self.user_logins.increment()
    
    def update_inventory_metrics(self, total_products: int, low_stock_count: int, total_value: float):
        """Actualiza métricas de inventario"""
        self.total_products.set(total_products)
        self.low_stock_products.set(low_stock_count)
        self.total_inventory_value.set(total_value)

# Instancia global de métricas de negocio
business_metrics = BusinessMetrics(metrics_registry)