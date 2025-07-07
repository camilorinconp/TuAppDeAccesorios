# ==================================================================
# TAREAS DE INVENTARIO - CELERY BACKGROUND JOBS
# ==================================================================

from typing import List, Dict, Any
from celery import current_task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..celery_app import celery_app
from ..database import get_db_session_maker
from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.inventory_tasks.check_low_stock_task")
def check_low_stock_task(self, threshold: int = 5):
    """Tarea para verificar productos con stock bajo"""
    
    try:
        logger.info(f"Iniciando verificación de stock bajo (umbral: {threshold})")
        
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
                meta={'message': 'Consultando productos con stock bajo'}
            )
            
            # Obtener productos con stock bajo
            from ..crud import get_products_with_low_stock
            low_stock_products = get_products_with_low_stock(db, threshold)
            
            # Categorizar por criticidad
            critical_products = [p for p in low_stock_products if p.stock_quantity == 0]
            warning_products = [p for p in low_stock_products if 0 < p.stock_quantity <= threshold]
            
            result = {
                'status': 'completed',
                'message': f'Verificación completada: {len(low_stock_products)} productos con stock bajo',
                'threshold': threshold,
                'summary': {
                    'total_low_stock': len(low_stock_products),
                    'critical_products': len(critical_products),
                    'warning_products': len(warning_products)
                },
                'critical_products': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'sku': p.sku,
                        'stock_quantity': p.stock_quantity
                    } for p in critical_products[:10]  # Limitar a 10 para el resultado
                ],
                'warning_products': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'sku': p.sku,
                        'stock_quantity': p.stock_quantity
                    } for p in warning_products[:10]  # Limitar a 10
                ]
            }
            
            # Si hay productos críticos, enviar notificación
            if critical_products:
                from .notification_tasks import send_low_stock_alert_task
                send_low_stock_alert_task.delay(
                    product_ids=[p.id for p in critical_products],
                    alert_type='critical'
                )
            
            logger.info("Verificación de stock bajo completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en verificación de stock bajo: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.inventory_tasks.update_stock_levels_task")
def update_stock_levels_task(self, stock_updates: List[Dict[str, Any]]):
    """Tarea para actualizar niveles de stock masivamente"""
    
    try:
        logger.info(f"Iniciando actualización masiva de stock para {len(stock_updates)} productos")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Preparando actualización de stock'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            updated_products = []
            errors = []
            total_updates = len(stock_updates)
            
            for i, update in enumerate(stock_updates):
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'Actualizando stock {i+1}/{total_updates}',
                        'progress': int((i / total_updates) * 100)
                    }
                )
                
                try:
                    product_id = update.get('product_id')
                    new_stock = update.get('stock_quantity')
                    reason = update.get('reason', 'bulk_update')
                    
                    if not product_id or new_stock is None:
                        raise ValueError("product_id y stock_quantity son requeridos")
                    
                    # Obtener producto
                    from ..models import Product
                    product = db.query(Product).filter(Product.id == product_id).first()
                    
                    if not product:
                        raise ValueError(f"Producto {product_id} no encontrado")
                    
                    # Registrar cambio para auditoría
                    old_stock = product.stock_quantity
                    
                    # Actualizar stock
                    product.stock_quantity = new_stock
                    
                    # Registrar en auditoría
                    from ..services.audit_service import AuditService
                    from ..models.audit import AuditActionType, AuditSeverity
                    
                    AuditService.log_event(
                        db=db,
                        action_type=AuditActionType.UPDATE,
                        description=f"Actualización masiva de stock: {old_stock} -> {new_stock}",
                        table_name="products",
                        record_id=str(product_id),
                        old_values={'stock_quantity': old_stock},
                        new_values={'stock_quantity': new_stock},
                        additional_data={'reason': reason, 'batch_update': True},
                        severity=AuditSeverity.MEDIUM
                    )
                    
                    updated_products.append({
                        'product_id': product_id,
                        'old_stock': old_stock,
                        'new_stock': new_stock
                    })
                    
                except Exception as update_error:
                    logger.warning(f"Error actualizando stock para producto {update.get('product_id', 'unknown')}: {str(update_error)}")
                    errors.append({
                        'update_data': update,
                        'error': str(update_error)
                    })
            
            # Commit todas las actualizaciones
            if updated_products:
                db.commit()
                
                # Invalidar caché de productos
                from ..services.intelligent_cache import ProductCacheManager
                ProductCacheManager.invalidate_all_products()
            
            result = {
                'status': 'completed',
                'message': f'Actualización de stock completada: {len(updated_products)} productos actualizados',
                'updated_products': updated_products,
                'errors': errors,
                'success_rate': len(updated_products) / total_updates * 100 if total_updates > 0 else 0
            }
            
            logger.info("Actualización masiva de stock completada", extra=result)
            return result
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en actualización masiva de stock: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=180, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.inventory_tasks.reconcile_inventory_task")
def reconcile_inventory_task(self, location: str = "main_warehouse"):
    """Tarea para reconciliar inventario"""
    
    try:
        logger.info(f"Iniciando reconciliación de inventario para ubicación: {location}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando reconciliación de inventario'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando discrepancias de inventario'}
            )
            
            # Obtener todos los productos
            from ..models import Product
            products = db.query(Product).all()
            
            discrepancies = []
            reconciled_products = []
            
            for i, product in enumerate(products):
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'Reconciliando producto {i+1}/{len(products)}',
                        'progress': int((i / len(products)) * 100)
                    }
                )
                
                # Aquí iría lógica específica de reconciliación
                # Por ejemplo, comparar con sistema externo, conteos físicos, etc.
                
                # Por ahora, simular verificación de consistencia básica
                if product.stock_quantity < 0:
                    discrepancies.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'sku': product.sku,
                        'current_stock': product.stock_quantity,
                        'issue': 'Stock negativo',
                        'suggested_action': 'Ajustar a 0'
                    })
                    
                    # Corregir stock negativo
                    product.stock_quantity = 0
                    reconciled_products.append(product.id)
                
                # Verificar precios inconsistentes
                if product.selling_price < product.cost_price:
                    discrepancies.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'sku': product.sku,
                        'issue': 'Precio de venta menor que costo',
                        'cost_price': float(product.cost_price),
                        'selling_price': float(product.selling_price),
                        'suggested_action': 'Revisar precios'
                    })
            
            # Commit correcciones automáticas
            if reconciled_products:
                db.commit()
                
                # Registrar en auditoría
                from ..services.audit_service import AuditService
                from ..models.audit import AuditActionType, AuditSeverity
                
                AuditService.log_event(
                    db=db,
                    action_type=AuditActionType.UPDATE,
                    description=f"Reconciliación de inventario: {len(reconciled_products)} productos corregidos",
                    additional_data={
                        'location': location,
                        'reconciled_products': reconciled_products,
                        'total_discrepancies': len(discrepancies)
                    },
                    severity=AuditSeverity.MEDIUM
                )
            
            result = {
                'status': 'completed',
                'message': f'Reconciliación completada: {len(discrepancies)} discrepancias encontradas',
                'location': location,
                'summary': {
                    'total_products_checked': len(products),
                    'discrepancies_found': len(discrepancies),
                    'auto_corrected': len(reconciled_products)
                },
                'discrepancies': discrepancies[:20],  # Limitar para el resultado
                'reconciled_products': reconciled_products
            }
            
            logger.info("Reconciliación de inventario completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en reconciliación de inventario: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=600, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.inventory_tasks.check_overdue_consignments_task")
def check_overdue_consignments_task(self):
    """Tarea para verificar consignaciones vencidas"""
    
    try:
        logger.info("Iniciando verificación de consignaciones vencidas")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Consultando consignaciones vencidas'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            # Obtener préstamos vencidos
            from ..crud import get_overdue_loans
            overdue_loans = get_overdue_loans(db)
            
            result = {
                'status': 'completed',
                'message': f'Verificación completada: {len(overdue_loans)} consignaciones vencidas',
                'overdue_count': len(overdue_loans),
                'overdue_loans': [
                    {
                        'id': loan.id,
                        'distributor_name': loan.distributor.name,
                        'product_name': loan.product.name,
                        'quantity_loaned': loan.quantity_loaned,
                        'return_due_date': loan.return_due_date.isoformat(),
                        'days_overdue': (datetime.utcnow().date() - loan.return_due_date).days
                    } for loan in overdue_loans[:20]  # Limitar para el resultado
                ]
            }
            
            # Si hay préstamos vencidos, enviar notificación
            if overdue_loans:
                from .notification_tasks import send_overdue_consignments_alert_task
                send_overdue_consignments_alert_task.delay(
                    loan_ids=[loan.id for loan in overdue_loans]
                )
            
            logger.info("Verificación de consignaciones vencidas completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en verificación de consignaciones vencidas: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=3)