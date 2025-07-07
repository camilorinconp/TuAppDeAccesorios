# ==================================================================
# ROUTER DE BÚSQUEDA AVANZADA - ENDPOINTS PARA FULL-TEXT SEARCH
# ==================================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import time

from .. import schemas
from ..dependencies import get_db
from ..utils.fulltext_search import (
    FullTextSearchEngine, 
    SearchSuggestionEngine, 
    SearchAnalytics
)
from ..utils.search import SearchPerformanceTracker
from ..logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/search/products", response_model=List[schemas.Product])
def search_products_advanced(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    use_fulltext: bool = Query(True, description="Usar búsqueda full-text avanzada"),
    boost_exact: bool = Query(True, description="Priorizar coincidencias exactas"),
    include_fuzzy: bool = Query(True, description="Incluir búsqueda difusa"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada de productos con full-text search
    Soporta múltiples estrategias de búsqueda y optimizaciones
    """
    start_time = time.time()
    
    try:
        if use_fulltext:
            # Usar motor de búsqueda avanzado
            results = FullTextSearchEngine.search_products_advanced(
                db=db,
                query=q,
                limit=limit,
                use_postgresql=True,
                boost_exact_matches=boost_exact,
                include_fuzzy=include_fuzzy
            )
        else:
            # Usar búsqueda básica mejorada
            results = FullTextSearchEngine.search_products_advanced(
                db=db,
                query=q,
                limit=limit,
                use_postgresql=False,
                boost_exact_matches=boost_exact,
                include_fuzzy=False
            )
        
        execution_time = time.time() - start_time
        
        # Registrar métricas de performance
        SearchPerformanceTracker.log_search_metrics(
            query=q,
            results_count=len(results),
            execution_time=execution_time
        )
        
        # Registrar analíticas de búsqueda
        SearchAnalytics.log_search_analytics(
            db=db,
            query=q,
            results_count=len(results),
            execution_time_ms=execution_time * 1000
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "Error en búsqueda avanzada de productos",
            query=q,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la búsqueda de productos"
        )


@router.get("/search/suggestions")
def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Término parcial para sugerencias"),
    limit: int = Query(5, ge=1, le=10, description="Número máximo de sugerencias"),
    db: Session = Depends(get_db)
):
    """
    Obtiene sugerencias de búsqueda basadas en productos existentes
    Útil para autocompletado en tiempo real
    """
    try:
        suggestions = SearchSuggestionEngine.get_search_suggestions(
            db=db,
            partial_query=q,
            limit=limit
        )
        
        return {
            "query": q,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(
            "Error obteniendo sugerencias de búsqueda",
            query=q,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo sugerencias de búsqueda"
        )


@router.get("/search/popular")
def get_popular_searches(
    limit: int = Query(10, ge=1, le=20, description="Número de búsquedas populares"),
    days: int = Query(30, ge=1, le=90, description="Días hacia atrás para analizar"),
    db: Session = Depends(get_db)
):
    """
    Obtiene las búsquedas más populares en un período de tiempo
    Útil para análisis y optimización de contenido
    """
    try:
        popular_searches = SearchAnalytics.get_popular_searches(
            db=db,
            limit=limit,
            days=days
        )
        
        return {
            "popular_searches": popular_searches,
            "period_days": days,
            "count": len(popular_searches),
            "generated_at": time.time()
        }
        
    except Exception as e:
        logger.error(
            "Error obteniendo búsquedas populares",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo búsquedas populares"
        )


@router.post("/search/analytics/click")
def log_search_click(
    query: str = Query(..., description="Término de búsqueda original"),
    product_id: int = Query(..., description="ID del producto clickeado"),
    position: int = Query(..., ge=0, description="Posición en resultados (0-indexed)"),
    db: Session = Depends(get_db)
):
    """
    Registra cuando un usuario hace click en un resultado de búsqueda
    Útil para mejorar el ranking y relevancia de resultados
    """
    try:
        # Registrar click para analíticas
        SearchAnalytics.log_search_analytics(
            db=db,
            query=query,
            results_count=0,  # No aplicable para clicks
            execution_time_ms=0,  # No aplicable para clicks
            clicked_result_id=product_id
        )
        
        # Log estructurado para análisis posterior
        logger.info(
            "search_result_clicked",
            query=query,
            product_id=product_id,
            position=position,
            timestamp=time.time()
        )
        
        return {
            "message": "Click registrado exitosamente",
            "query": query,
            "product_id": product_id,
            "position": position
        }
        
    except Exception as e:
        logger.error(
            "Error registrando click de búsqueda",
            query=query,
            product_id=product_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registrando click de búsqueda"
        )


@router.get("/search/test-engines")
def test_search_engines(
    q: str = Query(..., min_length=1, description="Término de búsqueda para testing"),
    limit: int = Query(10, ge=1, le=20, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Endpoint de testing para comparar diferentes motores de búsqueda
    Útil para debugging y optimización
    """
    try:
        start_time = time.time()
        
        # Probar motor full-text
        fulltext_start = time.time()
        fulltext_results = FullTextSearchEngine.search_products_advanced(
            db=db,
            query=q,
            limit=limit,
            use_postgresql=True,
            boost_exact_matches=True,
            include_fuzzy=True
        )
        fulltext_time = time.time() - fulltext_start
        
        # Probar motor básico
        basic_start = time.time()
        basic_results = FullTextSearchEngine.search_products_advanced(
            db=db,
            query=q,
            limit=limit,
            use_postgresql=False,
            boost_exact_matches=True,
            include_fuzzy=False
        )
        basic_time = time.time() - basic_start
        
        # Probar búsqueda segura original
        from ..utils.search import search_products_secure
        secure_start = time.time()
        secure_results = search_products_secure(db, q, limit)
        secure_time = time.time() - secure_start
        
        total_time = time.time() - start_time
        
        return {
            "query": q,
            "engines": {
                "fulltext": {
                    "results_count": len(fulltext_results),
                    "execution_time_ms": fulltext_time * 1000,
                    "results": [{"id": p.id, "name": p.name, "sku": p.sku} for p in fulltext_results[:5]]
                },
                "basic": {
                    "results_count": len(basic_results),
                    "execution_time_ms": basic_time * 1000,
                    "results": [{"id": p.id, "name": p.name, "sku": p.sku} for p in basic_results[:5]]
                },
                "secure": {
                    "results_count": len(secure_results),
                    "execution_time_ms": secure_time * 1000,
                    "results": [{"id": p.id, "name": p.name, "sku": p.sku} for p in secure_results[:5]]
                }
            },
            "total_execution_time_ms": total_time * 1000,
            "recommendation": "fulltext" if fulltext_time < basic_time else "basic"
        }
        
    except Exception as e:
        logger.error(
            "Error en testing de motores de búsqueda",
            query=q,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en testing de motores de búsqueda"
        )