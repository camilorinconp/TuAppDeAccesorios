# ==================================================================
# UTILS DE BÚSQUEDA SEGURA - PREVENCIÓN SQL INJECTION
# ==================================================================

import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, asc, desc, text
from ..models import Product


class SearchSanitizer:
    """Sanitizador de consultas de búsqueda para prevenir SQL injection"""
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitiza una consulta de búsqueda eliminando caracteres peligrosos
        y escapando caracteres especiales de SQL
        """
        if not query or not isinstance(query, str):
            return ""
        
        # Remover caracteres peligrosos
        query = query.strip()
        
        # Escapar caracteres especiales de LIKE pattern
        # % y _ son wildcards en SQL LIKE
        query = query.replace('\\', '\\\\')  # Escapar backslashes primero
        query = query.replace('%', '\\%')    # Escapar wildcards %
        query = query.replace('_', '\\_')    # Escapar wildcards _
        
        # Remover caracteres SQL peligrosos
        dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_', "'", '"']
        for char in dangerous_chars:
            query = query.replace(char, '')
        
        # Limitar longitud para prevenir DoS
        query = query[:100]
        
        return query
    
    @staticmethod
    def prepare_like_pattern(query: str, position: str = 'both') -> str:
        """
        Prepara un patrón LIKE seguro
        position: 'both' (%query%), 'start' (query%), 'end' (%query)
        """
        sanitized = SearchSanitizer.sanitize_query(query)
        
        if position == 'both':
            return f"%{sanitized}%"
        elif position == 'start':
            return f"{sanitized}%"
        elif position == 'end':
            return f"%{sanitized}"
        else:
            return sanitized


def search_products_secure(db: Session, query: str, limit: int = 10) -> list[Product]:
    """
    Búsqueda segura de productos por nombre, SKU y descripción
    Previene SQL injection mediante sanitización de entrada
    """
    if not query or len(query.strip()) < 1:
        return []
    
    # Sanitizar la consulta
    safe_query = SearchSanitizer.sanitize_query(query)
    
    if not safe_query:
        return []
    
    # Preparar patrones LIKE seguros
    pattern_both = SearchSanitizer.prepare_like_pattern(safe_query, 'both')
    pattern_start = SearchSanitizer.prepare_like_pattern(safe_query, 'start')
    
    # Ejecutar búsqueda con parámetros preparados
    try:
        results = db.query(Product).filter(
            or_(
                Product.name.ilike(pattern_both),
                Product.sku.ilike(pattern_both),
                Product.description.ilike(pattern_both)
            )
        ).order_by(
            # Priorizar coincidencias exactas en SKU (inicio)
            Product.sku.ilike(pattern_start).desc(),
            # Luego coincidencias exactas en nombre (inicio)
            Product.name.ilike(pattern_start).desc(),
            # Finalmente por nombre alfabéticamente
            asc(Product.name)
        ).limit(limit).all()
        
        return results
        
    except Exception as e:
        # Log el error pero no expongas detalles al usuario
        import logging
        logging.error(f"Error en búsqueda segura: {str(e)}")
        return []


def search_products_fulltext(db: Session, query: str, limit: int = 10) -> list[Product]:
    """
    Búsqueda full-text avanzada usando el nuevo motor de búsqueda
    """
    try:
        from .fulltext_search import FullTextSearchEngine
        
        # Usar el motor de búsqueda avanzado
        results = FullTextSearchEngine.search_products_advanced(
            db=db,
            query=query,
            limit=limit,
            use_postgresql=True,
            boost_exact_matches=True,
            include_fuzzy=True
        )
        
        return results
        
    except Exception as e:
        import logging
        logging.error(f"Error en búsqueda full-text, usando fallback: {str(e)}")
        # Fallback a búsqueda segura básica
        return search_products_secure(db, query, limit)


class SearchPerformanceTracker:
    """Tracker para monitorear performance de búsquedas"""
    
    @staticmethod
    def log_search_metrics(query: str, results_count: int, execution_time: float):
        """Log métricas de búsqueda para análisis posterior"""
        import logging
        
        logger = logging.getLogger("search.performance")
        logger.info(
            f"Search executed",
            extra={
                "query_length": len(query),
                "results_count": results_count,
                "execution_time_ms": execution_time * 1000,
                "query_hash": hash(query.lower())  # Para análisis sin exponer queries
            }
        )