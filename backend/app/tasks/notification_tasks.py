# ==================================================================
# TAREAS DE NOTIFICACIONES - CELERY BACKGROUND JOBS
# ==================================================================

from typing import List, Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..database import get_db_session_maker
from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.notification_tasks.send_low_stock_alert_task")
def send_low_stock_alert_task(self, product_ids: List[int], alert_type: str = 'warning'):
    """Tarea para enviar alertas de stock bajo"""
    
    try:
        logger.info(f"Enviando alerta de stock bajo para {len(product_ids)} productos (tipo: {alert_type})")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Preparando alertas de stock bajo'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Obteniendo información de productos'}
            )
            
            # Obtener información de productos
            from ..models import Product
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
            
            # Crear mensaje de alerta
            if alert_type == 'critical':
                subject = "🚨 ALERTA CRÍTICA: Productos sin stock"
                urgency = "CRÍTICA"
            else:
                subject = "⚠️ Aviso: Productos con stock bajo"
                urgency = "MEDIA"
            
            # Construir mensaje
            message_parts = [
                f"Se ha detectado una situación de stock {urgency.lower()}:",
                "",
                "Productos afectados:"
            ]
            
            for product in products:
                status = "SIN STOCK" if product.stock_quantity == 0 else f"STOCK BAJO ({product.stock_quantity})"
                message_parts.append(f"• {product.name} (SKU: {product.sku}) - {status}")
            
            message_parts.extend([
                "",
                "Acciones recomendadas:",
                "1. Revisar proveedores para reposición",
                "2. Verificar productos alternativos",
                "3. Actualizar estado en sistema de ventas",
                "",
                f"Total productos afectados: {len(products)}",
                f"Nivel de urgencia: {urgency}"
            ])
            
            alert_message = "\n".join(message_parts)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Enviando notificaciones'}
            )
            
            # Registrar alerta en auditoría
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            severity = AuditSeverity.CRITICAL if alert_type == 'critical' else AuditSeverity.HIGH
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Alerta de stock {alert_type} enviada",
                additional_data={
                    'alert_type': alert_type,
                    'product_ids': product_ids,
                    'products_count': len(products),
                    'subject': subject
                },
                severity=severity
            )
            
            # Simular envío de notificación (en producción sería email, SMS, etc.)
            notification_channels = []
            
            # Email (simulado)
            notification_channels.append({
                'channel': 'email',
                'status': 'sent',
                'recipients': ['admin@tuappdeaccesorios.com', 'inventario@tuappdeaccesorios.com'],
                'message': 'Email de alerta enviado exitosamente'
            })
            
            # Notificación interna del sistema
            notification_channels.append({
                'channel': 'system',
                'status': 'sent',
                'message': 'Alerta registrada en sistema de auditoría'
            })
            
            # Si es crítico, enviar SMS también (simulado)
            if alert_type == 'critical':
                notification_channels.append({
                    'channel': 'sms',
                    'status': 'sent',
                    'recipients': ['+57300XXXXXXX'],
                    'message': 'SMS de alerta crítica enviado'
                })
            
            result = {
                'status': 'completed',
                'message': f'Alertas de stock {alert_type} enviadas exitosamente',
                'alert_type': alert_type,
                'products_count': len(products),
                'notification_channels': notification_channels,
                'alert_content': {
                    'subject': subject,
                    'urgency': urgency,
                    'products': [
                        {
                            'id': p.id,
                            'name': p.name,
                            'sku': p.sku,
                            'stock': p.stock_quantity
                        } for p in products
                    ]
                }
            }
            
            logger.info("Alertas de stock bajo enviadas", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error enviando alertas de stock bajo: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=120, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.notification_tasks.send_overdue_consignments_alert_task")
def send_overdue_consignments_alert_task(self, loan_ids: List[int]):
    """Tarea para enviar alertas de consignaciones vencidas"""
    
    try:
        logger.info(f"Enviando alerta de consignaciones vencidas para {len(loan_ids)} préstamos")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Preparando alertas de consignaciones vencidas'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Obteniendo información de préstamos'}
            )
            
            # Obtener información de préstamos vencidos
            from ..models import ConsignmentLoan
            from sqlalchemy.orm import joinedload
            from datetime import datetime
            
            loans = db.query(ConsignmentLoan).options(
                joinedload(ConsignmentLoan.distributor),
                joinedload(ConsignmentLoan.product)
            ).filter(ConsignmentLoan.id.in_(loan_ids)).all()
            
            # Construir mensaje de alerta
            subject = "📅 Alerta: Consignaciones vencidas requieren atención"
            
            message_parts = [
                "Se han detectado consignaciones que han superado su fecha de devolución:",
                "",
                "Préstamos vencidos:"
            ]
            
            for loan in loans:
                days_overdue = (datetime.utcnow().date() - loan.return_due_date).days
                message_parts.append(
                    f"• Distribuidor: {loan.distributor.name}"
                    f"\n  Producto: {loan.product.name} (SKU: {loan.product.sku})"
                    f"\n  Cantidad: {loan.quantity_loaned} unidades"
                    f"\n  Vencido hace: {days_overdue} días"
                    f"\n  Fecha límite: {loan.return_due_date.strftime('%d/%m/%Y')}"
                    f"\n"
                )
            
            message_parts.extend([
                "Acciones recomendadas:",
                "1. Contactar distribuidores para reporte de ventas",
                "2. Solicitar devolución de productos no vendidos",
                "3. Revisar términos de consignación",
                "4. Actualizar estado de préstamos",
                "",
                f"Total préstamos vencidos: {len(loans)}"
            ])
            
            alert_message = "\n".join(message_parts)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Enviando notificaciones'}
            )
            
            # Registrar alerta en auditoría
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description="Alerta de consignaciones vencidas enviada",
                additional_data={
                    'loan_ids': loan_ids,
                    'loans_count': len(loans),
                    'subject': subject
                },
                severity=AuditSeverity.HIGH
            )
            
            # Enviar notificaciones
            notification_channels = [
                {
                    'channel': 'email',
                    'status': 'sent',
                    'recipients': ['admin@tuappdeaccesorios.com', 'consignaciones@tuappdeaccesorios.com'],
                    'message': 'Email de alerta enviado exitosamente'
                },
                {
                    'channel': 'system',
                    'status': 'sent',
                    'message': 'Alerta registrada en sistema de auditoría'
                }
            ]
            
            result = {
                'status': 'completed',
                'message': f'Alertas de consignaciones vencidas enviadas exitosamente',
                'loans_count': len(loans),
                'notification_channels': notification_channels,
                'alert_content': {
                    'subject': subject,
                    'overdue_loans': [
                        {
                            'id': loan.id,
                            'distributor': loan.distributor.name,
                            'product': loan.product.name,
                            'sku': loan.product.sku,
                            'quantity': loan.quantity_loaned,
                            'due_date': loan.return_due_date.isoformat(),
                            'days_overdue': (datetime.utcnow().date() - loan.return_due_date).days
                        } for loan in loans
                    ]
                }
            }
            
            logger.info("Alertas de consignaciones vencidas enviadas", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error enviando alertas de consignaciones vencidas: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=180, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.notification_tasks.send_daily_summary_task")
def send_daily_summary_task(self):
    """Tarea para enviar resumen diario"""
    
    try:
        logger.info("Enviando resumen diario del sistema")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Generando resumen diario'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            from datetime import datetime, timedelta
            from ..models import Product, PointOfSaleTransaction, ConsignmentLoan
            from sqlalchemy import func
            
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Recopilando estadísticas'}
            )
            
            # Estadísticas de productos
            total_products = db.query(func.count(Product.id)).scalar()
            low_stock_products = db.query(func.count(Product.id)).filter(Product.stock_quantity <= 5).scalar()
            out_of_stock = db.query(func.count(Product.id)).filter(Product.stock_quantity == 0).scalar()
            
            # Estadísticas de ventas del día anterior
            sales_yesterday = db.query(func.count(PointOfSaleTransaction.id)).filter(
                func.date(PointOfSaleTransaction.transaction_time) == yesterday
            ).scalar()
            
            revenue_yesterday = db.query(func.sum(PointOfSaleTransaction.total_amount)).filter(
                func.date(PointOfSaleTransaction.transaction_time) == yesterday
            ).scalar() or 0
            
            # Consignaciones activas
            active_consignments = db.query(func.count(ConsignmentLoan.id)).filter(
                ConsignmentLoan.status == 'en_prestamo'
            ).scalar()
            
            # Construir resumen
            subject = f"📊 Resumen diario TuAppDeAccesorios - {today.strftime('%d/%m/%Y')}"
            
            message_parts = [
                f"Resumen de actividades del {yesterday.strftime('%d/%m/%Y')}:",
                "",
                "💰 VENTAS:",
                f"• Transacciones: {sales_yesterday}",
                f"• Ingresos: ${revenue_yesterday:,.2f}",
                "",
                "📦 INVENTARIO:",
                f"• Total productos: {total_products}",
                f"• Stock bajo (≤5): {low_stock_products}",
                f"• Sin stock: {out_of_stock}",
                "",
                "🤝 CONSIGNACIONES:",
                f"• Préstamos activos: {active_consignments}",
                "",
                "🎯 INDICADORES:",
            ]
            
            # Indicadores de salud
            if out_of_stock > 0:
                message_parts.append("❌ Productos sin stock requieren atención")
            if low_stock_products > 10:
                message_parts.append("⚠️ Alto número de productos con stock bajo")
            if sales_yesterday == 0:
                message_parts.append("⚠️ No se registraron ventas ayer")
            else:
                message_parts.append("✅ Actividad de ventas normal")
            
            if active_consignments > 0:
                message_parts.append(f"📋 {active_consignments} consignaciones requieren seguimiento")
            
            summary_message = "\n".join(message_parts)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Enviando resumen'}
            )
            
            # Simular envío
            notification_channels = [
                {
                    'channel': 'email',
                    'status': 'sent',
                    'recipients': ['admin@tuappdeaccesorios.com'],
                    'message': 'Resumen diario enviado por email'
                }
            ]
            
            result = {
                'status': 'completed',
                'message': 'Resumen diario enviado exitosamente',
                'summary_date': yesterday.isoformat(),
                'notification_channels': notification_channels,
                'statistics': {
                    'sales': {
                        'transactions': sales_yesterday,
                        'revenue': float(revenue_yesterday)
                    },
                    'inventory': {
                        'total_products': total_products,
                        'low_stock': low_stock_products,
                        'out_of_stock': out_of_stock
                    },
                    'consignments': {
                        'active': active_consignments
                    }
                }
            }
            
            logger.info("Resumen diario enviado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error enviando resumen diario: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)