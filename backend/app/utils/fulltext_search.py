# ==================================================================
# BÚSQUEDA FULL-TEXT AVANZADA - POSTGRESQL Y ELASTICSEARCH
# ==================================================================

from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_, and_, desc
import re
import unicodedata
from datetime import datetime

from ..models import Product
from ..logging_config import get_logger
from .search import SearchSanitizer

logger = get_logger(__name__)


class FullTextSearchEngine:
    """Motor de búsqueda full-text con múltiples estrategias"""
    
    @staticmethod
    def search_products_advanced(
        db: Session,
        query: str,
        limit: int = 10,
        use_postgresql: bool = True,
        boost_exact_matches: bool = True,
        include_fuzzy: bool = True
    ) -> List[Product]:
        """
        Búsqueda avanzada de productos con múltiples estrategias
        
        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            limit: Límite de resultados
            use_postgresql: Si usar características de PostgreSQL
            boost_exact_matches: Si priorizar coincidencias exactas
            include_fuzzy: Si incluir búsqueda difusa
        """
        
        if not query or len(query.strip()) < 1:
            return []
        
        # Sanitizar y normalizar query
        normalized_query = FullTextSearchEngine._normalize_search_term(query)
        safe_query = SearchSanitizer.sanitize_query(normalized_query)
        
        if not safe_query:
            return []
        
        try:
            if use_postgresql and FullTextSearchEngine._is_postgresql(db):
                return FullTextSearchEngine._search_postgresql_fulltext(
                    db, safe_query, limit, boost_exact_matches, include_fuzzy
                )
            else:
                return FullTextSearchEngine._search_basic_like(
                    db, safe_query, limit, boost_exact_matches
                )
                
        except Exception as e:
            logger.error(
                "Error en búsqueda full-text",
                query=query,
                error=str(e)
            )
            # Fallback a búsqueda básica
            return FullTextSearchEngine._search_basic_like(db, safe_query, limit, False)
    
    @staticmethod
    def _search_postgresql_fulltext(
        db: Session,
        query: str,
        limit: int,
        boost_exact_matches: bool,
        include_fuzzy: bool
    ) -> List[Product]:
        """Búsqueda usando características full-text de PostgreSQL"""
        
        try:
            # Preparar términos de búsqueda
            search_terms = FullTextSearchEngine._prepare_search_terms(query)
            
            # Query base usando to_tsvector y to_tsquery
            base_query = """
            SELECT p.*, 
                   ts_rank_cd(
                       to_tsvector('spanish', 
                           COALESCE(p.name, '') || ' ' || 
                           COALESCE(p.sku, '') || ' ' || 
                           COALESCE(p.description, '')
                       ), 
                       to_tsquery('spanish', :search_query)
                   ) as rank,
                   similarity(p.name, :original_query) as name_similarity,
                   similarity(p.sku, :original_query) as sku_similarity
            FROM products p
            WHERE (
                to_tsvector('spanish', 
                    COALESCE(p.name, '') || ' ' || 
                    COALESCE(p.sku, '') || ' ' || 
                    COALESCE(p.description, '')
                ) @@ to_tsquery('spanish', :search_query)
                OR similarity(p.name, :original_query) > 0.3
                OR similarity(p.sku, :original_query) > 0.4
            """
            
            if boost_exact_matches:
                base_query += """
                OR p.name ILIKE :exact_pattern
                OR p.sku ILIKE :exact_pattern
                """
            
            if include_fuzzy:
                base_query += """
                OR p.name % :original_query
                OR p.sku % :original_query
                """
            
            base_query += """
            )
            ORDER BY 
                CASE 
                    WHEN p.sku ILIKE :exact_pattern THEN 1
                    WHEN p.name ILIKE :exact_pattern THEN 2
                    ELSE 3
                END,
                rank DESC,
                name_similarity DESC,
                sku_similarity DESC,
                p.name ASC
            LIMIT :limit
            """
            
            # Preparar parámetros
            params = {
                'search_query': FullTextSearchEngine._build_tsquery(search_terms),
                'original_query': query,
                'exact_pattern': f'%{query}%',
                'limit': limit
            }
            
            result = db.execute(text(base_query), params)
            product_ids = [row[0] for row in result.fetchall()]
            
            # Obtener objetos Product completos manteniendo el orden
            if product_ids:
                products = db.query(Product).filter(Product.id.in_(product_ids)).all()
                # Reordenar según el orden de la búsqueda
                products_dict = {p.id: p for p in products}
                return [products_dict[pid] for pid in product_ids if pid in products_dict]
            
            return []
            
        except Exception as e:
            logger.warning(
                "Error en búsqueda PostgreSQL full-text, usando fallback",
                error=str(e),
                query=query
            )
            return FullTextSearchEngine._search_basic_like(db, query, limit, boost_exact_matches)
    
    @staticmethod
    def _search_basic_like(
        db: Session,
        query: str,
        limit: int,
        boost_exact_matches: bool
    ) -> List[Product]:
        """Búsqueda básica usando LIKE patterns mejorados"""
        
        try:
            # Preparar patrones de búsqueda
            exact_pattern = f'%{query}%'
            start_pattern = f'{query}%'
            words = query.lower().split()
            
            # Query base
            query_filters = []
            
            # Coincidencias exactas (mayor prioridad)
            if boost_exact_matches:
                exact_filters = [
                    Product.sku.ilike(exact_pattern),
                    Product.name.ilike(exact_pattern),
                    Product.description.ilike(exact_pattern)
                ]
                query_filters.extend(exact_filters)
            
            # Coincidencias por palabras individuales
            for word in words:
                if len(word) >= 2:  # Evitar palabras muy cortas
                    word_pattern = f'%{word}%'
                    query_filters.extend([
                        Product.name.ilike(word_pattern),
                        Product.sku.ilike(word_pattern),
                        Product.description.ilike(word_pattern)
                    ])
            
            if not query_filters:
                return []
            
            # Ejecutar query con ordenamiento inteligente
            results = db.query(Product).filter(
                or_(*query_filters)
            ).order_by(
                # Prioridad 1: Coincidencia exacta en SKU
                Product.sku.ilike(exact_pattern).desc(),
                # Prioridad 2: Coincidencia exacta en nombre
                Product.name.ilike(exact_pattern).desc(),
                # Prioridad 3: Coincidencia al inicio del nombre
                Product.name.ilike(start_pattern).desc(),
                # Prioridad 4: Coincidencia al inicio del SKU
                Product.sku.ilike(start_pattern).desc(),
                # Finalmente por nombre alfabético
                Product.name.asc()
            ).limit(limit).all()
            
            return results
            
        except Exception as e:
            logger.error(
                "Error en búsqueda básica LIKE",
                error=str(e),
                query=query
            )
            return []
    
    @staticmethod
    def _normalize_search_term(term: str) -> str:
        """Normaliza términos de búsqueda removiendo acentos y caracteres especiales"""
        
        if not term:
            return ""
        
        # Remover acentos y normalizar unicode
        normalized = unicodedata.normalize('NFD', term.lower())
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # Remover caracteres especiales pero mantener espacios y guiones
        normalized = re.sub(r'[^\w\s\-]', ' ', normalized)
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @staticmethod
    def _prepare_search_terms(query: str) -> List[str]:
        """Prepara términos de búsqueda para PostgreSQL full-text"""
        
        # Dividir en palabras y limpiar
        words = [word.strip() for word in query.split() if len(word.strip()) >= 2]
        
        # Agregar variaciones y sinónimos comunes
        enhanced_terms = []
        for word in words:
            enhanced_terms.append(word)
            
            # Agregar variaciones comunes para productos de accesorios
            variations = FullTextSearchEngine._get_term_variations(word)
            enhanced_terms.extend(variations)
        
        return list(set(enhanced_terms))  # Remover duplicados
    
    @staticmethod
    def _get_term_variations(term: str) -> List[str]:
        """Obtiene variaciones y sinónimos para términos comunes"""
        
        # Diccionario de sinónimos y variaciones para accesorios
        variations_map = {
            'celular': ['movil', 'telefono', 'smartphone', 'cell'],
            'cargador': ['cable', 'adaptador', 'charger'],
            'funda': ['case', 'carcasa', 'protector'],
            'audifonos': ['auriculares', 'earphones', 'headphones'],
            'protector': ['mica', 'cristal', 'glass', 'screen'],
            'samsung': ['galaxy', 'sam'],
            'iphone': ['apple', 'ios'],
            'huawei': ['honor'],
            'xiaomi': ['redmi', 'poco'],
            'negro': ['black', 'dark'],
            'blanco': ['white', 'claro'],
            'azul': ['blue'],
            'rojo': ['red'],
            'verde': ['green'],
            'original': ['genuino', 'authentic'],
            'compatible': ['generico', 'universal']
        }
        
        term_lower = term.lower()
        variations = []
        
        # Buscar en el mapa de variaciones
        for key, values in variations_map.items():
            if term_lower == key:
                variations.extend(values)
            elif term_lower in values:
                variations.append(key)
                variations.extend([v for v in values if v != term_lower])
        
        return variations
    
    @staticmethod
    def _build_tsquery(terms: List[str]) -> str:
        """Construye query PostgreSQL tsquery"""
        
        if not terms:
            return ""
        
        # Construir query con operadores OR entre términos
        tsquery_parts = []
        for term in terms:
            # Escapar caracteres especiales para tsquery
            escaped_term = re.sub(r'[^\w]', ' ', term).strip()
            if escaped_term:
                tsquery_parts.append(f"'{escaped_term}':*")
        
        return " | ".join(tsquery_parts) if tsquery_parts else ""
    
    @staticmethod
    def _is_postgresql(db: Session) -> bool:
        """Verifica si la base de datos es PostgreSQL"""
        
        try:
            # Intentar una función específica de PostgreSQL
            result = db.execute(text("SELECT version()")).fetchone()
            return result and 'PostgreSQL' in str(result[0])
        except:
            return False


class SearchSuggestionEngine:
    """Motor de sugerencias de búsqueda"""
    
    @staticmethod
    def get_search_suggestions(
        db: Session,
        partial_query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtiene sugerencias de búsqueda basadas en productos existentes"""
        
        if not partial_query or len(partial_query.strip()) < 2:
            return []
        
        try:
            normalized_query = FullTextSearchEngine._normalize_search_term(partial_query)
            safe_query = SearchSanitizer.sanitize_query(normalized_query)
            
            if not safe_query:
                return []
            
            # Buscar productos que coincidan parcialmente
            pattern = f'{safe_query}%'
            
            # Sugerencias basadas en nombres de productos
            name_suggestions = db.query(
                Product.name.label('suggestion'),
                func.count().label('frequency')
            ).filter(
                Product.name.ilike(pattern)
            ).group_by(Product.name).order_by(
                func.count().desc(),
                Product.name.asc()
            ).limit(limit).all()
            
            # Sugerencias basadas en SKUs
            sku_suggestions = db.query(
                Product.sku.label('suggestion'),
                func.count().label('frequency')
            ).filter(
                Product.sku.ilike(pattern)
            ).group_by(Product.sku).order_by(
                func.count().desc(),
                Product.sku.asc()
            ).limit(limit).all()
            
            # Combinar y formatear sugerencias
            suggestions = []
            seen = set()
            
            for suggestion, frequency in name_suggestions:
                if suggestion.lower() not in seen:
                    suggestions.append({
                        'text': suggestion,
                        'type': 'product_name',
                        'frequency': frequency,
                        'highlighted': FullTextSearchEngine._highlight_match(
                            suggestion, safe_query
                        )
                    })
                    seen.add(suggestion.lower())
            
            for suggestion, frequency in sku_suggestions:
                if suggestion.lower() not in seen and len(suggestions) < limit:
                    suggestions.append({
                        'text': suggestion,
                        'type': 'sku',
                        'frequency': frequency,
                        'highlighted': FullTextSearchEngine._highlight_match(
                            suggestion, safe_query
                        )
                    })
                    seen.add(suggestion.lower())
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(
                "Error generando sugerencias de búsqueda",
                query=partial_query,
                error=str(e)
            )
            return []
    
    @staticmethod
    def _highlight_match(text: str, query: str) -> str:
        """Resalta coincidencias en el texto"""
        
        try:
            # Escapar caracteres especiales para regex
            escaped_query = re.escape(query)
            
            # Reemplazar coincidencias con markup de resaltado
            highlighted = re.sub(
                f'({escaped_query})',
                r'<mark>\1</mark>',
                text,
                flags=re.IGNORECASE
            )
            
            return highlighted
            
        except Exception:
            return text


class SearchAnalytics:
    """Analytics y métricas de búsqueda"""
    
    @staticmethod
    def log_search_analytics(
        db: Session,
        query: str,
        results_count: int,
        execution_time_ms: float,
        user_id: Optional[int] = None,
        clicked_result_id: Optional[int] = None
    ):
        """Registra analíticas de búsqueda para optimización futura"""
        
        try:
            # En una implementación completa, esto se guardaría en una tabla específica
            # Por ahora, usar el sistema de auditoría existente
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            additional_data = {
                'query': query,
                'results_count': results_count,
                'execution_time_ms': execution_time_ms,
                'query_length': len(query),
                'word_count': len(query.split()),
                'clicked_result_id': clicked_result_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.SEARCH,
                description=f"Búsqueda: '{query}' - {results_count} resultados",
                user_id=user_id,
                severity=AuditSeverity.LOW,
                additional_data=additional_data,
                execution_time_ms=int(execution_time_ms)
            )
            
        except Exception as e:
            logger.error(
                "Error registrando analíticas de búsqueda",
                query=query,
                error=str(e)
            )
    
    @staticmethod
    def get_popular_searches(
        db: Session,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Obtiene las búsquedas más populares"""
        
        try:
            from ..models.audit import AuditLog, AuditActionType
            from datetime import timedelta
            
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Query para obtener búsquedas populares del log de auditoría
            popular_searches = db.query(
                AuditLog.additional_data['query'].astext.label('query'),
                func.count().label('search_count'),
                func.avg(
                    AuditLog.additional_data['results_count'].astext.cast(func.INTEGER)
                ).label('avg_results'),
                func.avg(AuditLog.execution_time_ms).label('avg_execution_time')
            ).filter(
                AuditLog.action_type == AuditActionType.SEARCH,
                AuditLog.timestamp >= since_date,
                AuditLog.additional_data['query'].astext.isnot(None)
            ).group_by(
                AuditLog.additional_data['query'].astext
            ).order_by(
                func.count().desc()
            ).limit(limit).all()
            
            return [
                {
                    'query': search.query,
                    'search_count': search.search_count,
                    'avg_results': float(search.avg_results or 0),
                    'avg_execution_time_ms': float(search.avg_execution_time or 0)
                }
                for search in popular_searches
            ]
            
        except Exception as e:
            logger.error(
                "Error obteniendo búsquedas populares",
                error=str(e)
            )
            return []