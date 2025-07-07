# ==================================================================
# ROUTER DE PERFORMANCE - MÉTRICAS Y OPTIMIZACIÓN EN TIEMPO REAL
# ==================================================================

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_admin_user
from ..services.intelligent_cache import intelligent_cache, ProductCacheManager
from ..utils.performance_optimizer import PerformanceOptimizer, QueryOptimizer
from ..logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/performance/cache/metrics", dependencies=[Depends(get_current_admin_user)])
def get_cache_metrics():
    """
    Obtiene métricas del sistema de caché inteligente
    Requiere permisos de administrador
    """
    try:
        metrics = intelligent_cache.get_metrics()
        
        return {
            "cache_metrics": metrics,
            "status": "active" if metrics else "inactive",
            "generated_at": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo métricas de caché"
        )


@router.post("/performance/cache/cleanup", dependencies=[Depends(get_current_admin_user)])
def cleanup_cache():
    """
    Ejecuta limpieza manual del caché
    Requiere permisos de administrador
    """
    try:
        # Ejecutar cleanup
        intelligent_cache.cleanup_expired()
        
        return {
            "message": "Limpieza de caché ejecutada exitosamente",
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando limpieza de caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error ejecutando limpieza de caché"
        )


@router.post("/performance/cache/invalidate", dependencies=[Depends(get_current_admin_user)])
def invalidate_cache(
    cache_type: str = Query(..., description="Tipo de caché a invalidar (products, search, all)"),
    specific_id: Optional[int] = Query(None, description="ID específico para invalidar (solo products)")
):
    """
    Invalida caché específico o completo
    Requiere permisos de administrador
    """
    try:
        if cache_type == "products":
            if specific_id:
                ProductCacheManager.invalidate_product(specific_id)
                message = f"Caché invalidado para producto {specific_id}"
            else:
                ProductCacheManager.invalidate_all_products()
                message = "Caché de todos los productos invalidado"
        
        elif cache_type == "search":
            intelligent_cache.invalidate_pattern("search:*")
            message = "Caché de búsquedas invalidado"
        
        elif cache_type == "all":
            ProductCacheManager.invalidate_all_products()
            intelligent_cache.invalidate_pattern("*")
            message = "Todo el caché invalidado"
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de caché no válido. Use: products, search, all"
            )
        
        return {
            "message": message,
            "cache_type": cache_type,
            "specific_id": specific_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidando caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error invalidando caché"
        )


@router.post("/performance/cache/warmup", dependencies=[Depends(get_current_admin_user)])
def warmup_cache(
    popular_products: Optional[str] = Query(None, description="IDs de productos populares separados por comas"),
    db: Session = Depends(get_db)
):
    """
    Pre-carga caché con productos populares
    Requiere permisos de administrador
    """
    try:
        # Parsear IDs de productos populares
        popular_product_ids = []
        if popular_products:
            try:
                popular_product_ids = [int(x.strip()) for x in popular_products.split(',') if x.strip()]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="IDs de productos deben ser números enteros separados por comas"
                )
        
        # Si no se especifican productos, usar algunos por defecto
        if not popular_product_ids:
            # Obtener productos con más stock como proxy de popularidad
            from sqlalchemy import desc
            from ..models import Product
            
            popular_products_query = db.query(Product.id).order_by(
                desc(Product.stock_quantity)
            ).limit(10).all()
            
            popular_product_ids = [p.id for p in popular_products_query]
        
        # Pre-cargar caché
        ProductCacheManager.warm_up_cache(db, popular_product_ids)
        
        return {
            "message": "Caché pre-cargado exitosamente",
            "preloaded_products": len(popular_product_ids),
            "product_ids": popular_product_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pre-cargando caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error pre-cargando caché"
        )


@router.get("/performance/database/analyze", dependencies=[Depends(get_current_admin_user)])
def analyze_database_performance(
    query: Optional[str] = Query(None, description="Query SQL específica para analizar"),
    db: Session = Depends(get_db)
):
    """
    Analiza performance de la base de datos
    Requiere permisos de administrador
    """
    try:
        if query:
            # Analizar query específica
            analysis = PerformanceOptimizer.analyze_query_performance(db, query)
            
            return {
                "query_analysis": analysis,
                "query": query,
                "analyzed_at": "2024-01-01T00:00:00Z"  # Placeholder
            }
        else:
            # Análisis general de la base de datos
            return {
                "message": "Para análisis específico, proporcione una query en el parámetro 'query'",
                "available_optimizations": [
                    "Optimización de índices",
                    "Análisis de queries lentas", 
                    "Estadísticas de tablas",
                    "Configuración de performance"
                ]
            }
        
    except Exception as e:
        logger.error(f"Error analizando performance de base de datos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error analizando performance de base de datos"
        )


@router.post("/performance/database/optimize", dependencies=[Depends(get_current_admin_user)])
def optimize_database(
    optimize_products: bool = Query(True, description="Optimizar queries de productos"),
    update_statistics: bool = Query(True, description="Actualizar estadísticas de tablas"),
    db: Session = Depends(get_db)
):
    """
    Ejecuta optimizaciones en la base de datos
    Requiere permisos de administrador
    """
    try:
        optimization_results = []
        
        if optimize_products:
            try:
                QueryOptimizer.optimize_product_queries(db)
                optimization_results.append("Queries de productos optimizadas")
            except Exception as e:
                optimization_results.append(f"Error optimizando productos: {str(e)}")
        
        if update_statistics:
            try:
                from sqlalchemy import text
                db.execute(text("ANALYZE"))
                db.commit()
                optimization_results.append("Estadísticas de base de datos actualizadas")
            except Exception as e:
                optimization_results.append(f"Error actualizando estadísticas: {str(e)}")
        
        # Optimizar configuración de sesión
        try:
            PerformanceOptimizer.optimize_database_session(db)
            optimization_results.append("Configuración de sesión optimizada")
        except Exception as e:
            optimization_results.append(f"Error optimizando sesión: {str(e)}")
        
        return {
            "message": "Optimizaciones ejecutadas",
            "results": optimization_results,
            "optimized_at": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando optimizaciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error ejecutando optimizaciones de base de datos"
        )


@router.get("/performance/health")
def get_performance_health():
    """
    Obtiene estado general de performance del sistema
    Endpoint público para monitoreo
    """
    try:
        # Métricas básicas de caché
        cache_metrics = intelligent_cache.get_metrics()
        
        # Estado general
        cache_healthy = cache_metrics.get('hit_rate_percent', 0) > 50
        cache_efficiency = cache_metrics.get('cache_efficiency', 0)
        
        health_status = "healthy" if cache_healthy else "degraded"
        
        return {
            "status": health_status,
            "cache": {
                "hit_rate_percent": cache_metrics.get('hit_rate_percent', 0),
                "efficiency": cache_efficiency,
                "total_keys": cache_metrics.get('total_keys', 0)
            },
            "recommendations": [
                "Caché funcionando correctamente" if cache_healthy else "Considerar optimizar caché",
                f"Eficiencia de caché: {cache_efficiency:.1f}%" if cache_efficiency else "Métricas de caché no disponibles"
            ],
            "checked_at": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de performance: {str(e)}")
        return {
            "status": "error",
            "error": "No se pudo obtener métricas de performance",
            "checked_at": "2024-01-01T00:00:00Z"  # Placeholder
        }


@router.get("/performance/recommendations", dependencies=[Depends(get_current_admin_user)])
def get_performance_recommendations(db: Session = Depends(get_db)):
    """
    Obtiene recomendaciones de optimización específicas
    Requiere permisos de administrador
    """
    try:
        recommendations = []
        
        # Analizar métricas de caché
        cache_metrics = intelligent_cache.get_metrics()
        hit_rate = cache_metrics.get('hit_rate_percent', 0)
        
        if hit_rate < 50:
            recommendations.append({
                "category": "cache",
                "priority": "high",
                "issue": f"Tasa de aciertos de caché baja ({hit_rate:.1f}%)",
                "recommendation": "Considerar ajustar TTL o estrategias de caché",
                "action": "Revisar patrones de acceso y optimizar claves de caché"
            })
        
        if cache_metrics.get('total_keys', 0) > 10000:
            recommendations.append({
                "category": "cache", 
                "priority": "medium",
                "issue": "Alto número de claves en caché",
                "recommendation": "Ejecutar limpieza de caché regularmente",
                "action": "Configurar limpieza automática más frecuente"
            })
        
        # Analizar base de datos (simplificado)
        try:
            from sqlalchemy import text
            table_sizes = db.execute(text("""
                SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
                LIMIT 5
            """)).fetchall()
            
            recommendations.append({
                "category": "database",
                "priority": "info", 
                "issue": "Información de tamaños de tablas",
                "recommendation": f"Tablas más grandes: {', '.join([f'{t[1]} ({t[2]})' for t in table_sizes])}",
                "action": "Monitorear crecimiento de tablas principales"
            })
            
        except Exception:
            # Si no es PostgreSQL o hay error, omitir análisis de DB
            pass
        
        # Recomendaciones generales
        if not recommendations:
            recommendations.append({
                "category": "general",
                "priority": "info",
                "issue": "Sistema funcionando correctamente",
                "recommendation": "Continuar monitoreando métricas regularmente",
                "action": "Mantener configuración actual"
            })
        
        return {
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "generated_at": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error generando recomendaciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando recomendaciones de performance"
        )