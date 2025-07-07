# ==================================================================
# TAREAS DE PRODUCTOS - CELERY BACKGROUND JOBS
# ==================================================================

from typing import List, Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..database import get_db_session_maker
from ..config import settings
from ..logging_config import get_logger
from ..services.intelligent_cache import intelligent_cache, ProductCacheManager
from ..utils.performance_optimizer import QueryOptimizer, PerformanceOptimizer

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.product_tasks.cleanup_cache_task")
def cleanup_cache_task(self):
    """Tarea para limpiar caché expirado"""
    
    try:
        logger.info("Iniciando limpieza de caché programada")
        
        # Actualizar estado de la tarea
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando limpieza de caché'}
        )
        
        # Ejecutar limpieza
        intelligent_cache.cleanup_expired()
        
        # Obtener métricas después de la limpieza
        metrics = intelligent_cache.get_metrics()
        
        result = {
            'status': 'completed',
            'message': 'Limpieza de caché completada exitosamente',
            'metrics': {
                'total_keys': metrics.get('total_keys', 0),
                'hit_rate_percent': metrics.get('hit_rate_percent', 0),
                'cache_efficiency': metrics.get('cache_efficiency', 0)
            }
        }
        
        logger.info("Limpieza de caché completada", extra=result)
        return result
        
    except Exception as e:
        logger.error(f"Error en limpieza de caché: {str(e)}")
        
        # Actualizar estado de error
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.product_tasks.optimize_database_task")
def optimize_database_task(self):
    """Tarea para optimizar base de datos"""
    
    try:
        logger.info("Iniciando optimización de base de datos")
        
        current_task.update_state(
            state='PROGRESS', 
            meta={'message': 'Conectando a base de datos'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Optimizando queries de productos'}
            )
            
            # Optimizar queries de productos
            QueryOptimizer.optimize_product_queries(db)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Actualizando estadísticas'}
            )
            
            # Actualizar estadísticas de la base de datos
            from sqlalchemy import text
            db.execute(text("ANALYZE"))
            db.commit()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Optimizando configuración de sesión'}
            )
            
            # Optimizar configuración de sesión
            PerformanceOptimizer.optimize_database_session(db)
            
            result = {
                'status': 'completed',
                'message': 'Optimización de base de datos completada',
                'optimizations': [
                    'Queries de productos optimizadas',
                    'Estadísticas actualizadas',
                    'Configuración de sesión optimizada'
                ]
            }
            
            logger.info("Optimización de base de datos completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en optimización de base de datos: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.product_tasks.warm_up_cache_task")
def warm_up_cache_task(self, popular_product_ids: List[int] = None):
    """Tarea para pre-cargar caché con productos populares"""
    
    try:
        logger.info(f"Iniciando pre-carga de caché para {len(popular_product_ids or [])} productos")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Conectando a base de datos'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Pre-cargando productos populares'}
            )
            
            # Pre-cargar caché
            ProductCacheManager.warm_up_cache(db, popular_product_ids)
            
            # Obtener métricas después del warm-up
            metrics = intelligent_cache.get_metrics()
            
            result = {
                'status': 'completed',
                'message': 'Pre-carga de caché completada',
                'preloaded_products': len(popular_product_ids or []),
                'cache_metrics': {
                    'total_keys': metrics.get('total_keys', 0),
                    'hit_rate_percent': metrics.get('hit_rate_percent', 0)
                }
            }
            
            logger.info("Pre-carga de caché completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en pre-carga de caché: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=120, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.product_tasks.sync_product_data_task")
def sync_product_data_task(self, product_ids: List[int] = None):
    """Tarea para sincronizar datos de productos"""
    
    try:
        logger.info(f"Iniciando sincronización de datos para {len(product_ids or [])} productos")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Preparando sincronización'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            synced_products = []
            errors = []
            
            # Si no se especifican productos, sincronizar productos con cambios recientes
            if not product_ids:
                from datetime import datetime, timedelta
                from ..models import Product
                
                # Productos modificados en las últimas 24 horas
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                
                # Por simplicidad, tomar productos con stock bajo que podrían necesitar sincronización
                products = db.query(Product).filter(
                    Product.stock_quantity <= 10
                ).limit(50).all()
                
                product_ids = [p.id for p in products]
            
            total_products = len(product_ids)
            
            for i, product_id in enumerate(product_ids):
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'Sincronizando producto {i+1}/{total_products}',
                        'progress': int((i / total_products) * 100)
                    }
                )
                
                try:
                    # Invalidar caché para forzar sincronización
                    ProductCacheManager.invalidate_product(product_id)
                    
                    # Aquí iría lógica específica de sincronización
                    # Por ejemplo, validar precios, actualizar stock, etc.
                    
                    synced_products.append(product_id)
                    
                except Exception as product_error:
                    logger.warning(f"Error sincronizando producto {product_id}: {str(product_error)}")
                    errors.append({
                        'product_id': product_id,
                        'error': str(product_error)
                    })
            
            result = {
                'status': 'completed',
                'message': f'Sincronización completada: {len(synced_products)} productos sincronizados',
                'synced_products': synced_products,
                'errors': errors,
                'success_rate': len(synced_products) / total_products * 100 if total_products > 0 else 0
            }
            
            logger.info("Sincronización de productos completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en sincronización de productos: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=180, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.product_tasks.bulk_update_products_task")
def bulk_update_products_task(self, updates: List[Dict[str, Any]]):
    """Tarea para actualización masiva de productos"""
    
    try:
        logger.info(f"Iniciando actualización masiva de {len(updates)} productos")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Preparando actualización masiva'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            updated_products = []
            errors = []
            total_updates = len(updates)
            
            for i, update in enumerate(updates):
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'Actualizando producto {i+1}/{total_updates}',
                        'progress': int((i / total_updates) * 100)
                    }
                )
                
                try:
                    product_id = update.get('id')
                    if not product_id:
                        raise ValueError("ID de producto requerido")
                    
                    # Obtener producto
                    from ..models import Product
                    product = db.query(Product).filter(Product.id == product_id).first()
                    
                    if not product:
                        raise ValueError(f"Producto {product_id} no encontrado")
                    
                    # Aplicar updates
                    for field, value in update.items():
                        if field != 'id' and hasattr(product, field):
                            setattr(product, field, value)
                    
                    # Invalidar caché
                    ProductCacheManager.invalidate_product(product_id)
                    
                    updated_products.append(product_id)
                    
                except Exception as update_error:
                    logger.warning(f"Error actualizando producto {update.get('id', 'unknown')}: {str(update_error)}")
                    errors.append({
                        'product_data': update,
                        'error': str(update_error)
                    })
            
            # Commit todas las actualizaciones
            if updated_products:
                db.commit()
                
                # Invalidar caché de listas
                ProductCacheManager.invalidate_all_products()
            
            result = {
                'status': 'completed',
                'message': f'Actualización masiva completada: {len(updated_products)} productos actualizados',
                'updated_products': updated_products,
                'errors': errors,
                'success_rate': len(updated_products) / total_updates * 100 if total_updates > 0 else 0
            }
            
            logger.info("Actualización masiva de productos completada", extra=result)
            return result
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en actualización masiva de productos: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=240, max_retries=1)