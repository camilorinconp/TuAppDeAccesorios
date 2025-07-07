# ==================================================================
# TAREAS DE REPORTES - CELERY BACKGROUND JOBS
# ==================================================================

from typing import List, Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from ..celery_app import celery_app
from ..database import get_db_session_maker
from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.report_tasks.generate_daily_inventory_report")
def generate_daily_inventory_report(self, report_date: str = None):
    """Tarea para generar reporte diario de inventario"""
    
    try:
        if report_date:
            target_date = datetime.fromisoformat(report_date).date()
        else:
            target_date = datetime.utcnow().date()
        
        logger.info(f"Generando reporte diario de inventario para {target_date}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando generación de reporte de inventario'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Recopilando datos de inventario'}
            )
            
            from ..models import Product, PointOfSaleTransaction, PointOfSaleItem
            from sqlalchemy import func, desc
            
            # Estadísticas generales de inventario
            total_products = db.query(func.count(Product.id)).scalar()
            total_stock_value = db.query(func.sum(Product.stock_quantity * Product.cost_price)).scalar() or 0
            total_retail_value = db.query(func.sum(Product.stock_quantity * Product.selling_price)).scalar() or 0
            
            # Productos con stock bajo
            low_stock_products = db.query(Product).filter(Product.stock_quantity <= 5).all()
            
            # Productos sin stock
            out_of_stock_products = db.query(Product).filter(Product.stock_quantity == 0).all()
            
            # Productos más vendidos (últimos 30 días)
            thirty_days_ago = target_date - timedelta(days=30)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando productos más vendidos'}
            )
            
            top_selling_products = db.query(
                Product,
                func.sum(PointOfSaleItem.quantity_sold).label('total_sold'),
                func.sum(PointOfSaleItem.quantity_sold * PointOfSaleItem.price_at_time_of_sale).label('total_revenue')
            ).join(
                PointOfSaleItem, Product.id == PointOfSaleItem.product_id
            ).join(
                PointOfSaleTransaction, PointOfSaleItem.transaction_id == PointOfSaleTransaction.id
            ).filter(
                func.date(PointOfSaleTransaction.transaction_time) >= thirty_days_ago
            ).group_by(Product.id).order_by(desc('total_sold')).limit(10).all()
            
            # Movimientos del día
            daily_sales = db.query(
                func.count(PointOfSaleTransaction.id).label('transactions'),
                func.sum(PointOfSaleTransaction.total_amount).label('revenue'),
                func.sum(PointOfSaleItem.quantity_sold).label('units_sold')
            ).join(
                PointOfSaleItem, PointOfSaleTransaction.id == PointOfSaleItem.transaction_id
            ).filter(
                func.date(PointOfSaleTransaction.transaction_time) == target_date
            ).first()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Compilando reporte final'}
            )
            
            # Compilar reporte
            report_data = {
                'report_date': target_date.isoformat(),
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_products': total_products,
                    'total_stock_value': float(total_stock_value),
                    'total_retail_value': float(total_retail_value),
                    'profit_potential': float(total_retail_value - total_stock_value),
                    'low_stock_count': len(low_stock_products),
                    'out_of_stock_count': len(out_of_stock_products)
                },
                'daily_activity': {
                    'transactions': daily_sales.transactions or 0,
                    'revenue': float(daily_sales.revenue or 0),
                    'units_sold': daily_sales.units_sold or 0
                },
                'alerts': {
                    'low_stock_products': [
                        {
                            'id': p.id,
                            'name': p.name,
                            'sku': p.sku,
                            'current_stock': p.stock_quantity,
                            'value_at_risk': float(p.stock_quantity * p.selling_price)
                        } for p in low_stock_products[:20]
                    ],
                    'out_of_stock_products': [
                        {
                            'id': p.id,
                            'name': p.name,
                            'sku': p.sku,
                            'last_cost': float(p.cost_price),
                            'last_selling_price': float(p.selling_price)
                        } for p in out_of_stock_products[:20]
                    ]
                },
                'top_performers': [
                    {
                        'product': {
                            'id': item.Product.id,
                            'name': item.Product.name,
                            'sku': item.Product.sku
                        },
                        'units_sold': item.total_sold,
                        'revenue': float(item.total_revenue),
                        'current_stock': item.Product.stock_quantity
                    } for item in top_selling_products
                ]
            }
            
            # Guardar reporte en auditoría
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Reporte diario de inventario generado para {target_date}",
                additional_data=report_data,
                severity=AuditSeverity.LOW
            )
            
            result = {
                'status': 'completed',
                'message': f'Reporte diario de inventario generado para {target_date}',
                'report_data': report_data
            }
            
            logger.info("Reporte diario de inventario generado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generando reporte diario de inventario: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.report_tasks.generate_sales_report")
def generate_sales_report(self, start_date: str, end_date: str, group_by: str = 'day'):
    """Tarea para generar reporte de ventas por período"""
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        logger.info(f"Generando reporte de ventas del {start_date} al {end_date}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando generación de reporte de ventas'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Consultando datos de ventas'}
            )
            
            from ..models import PointOfSaleTransaction, PointOfSaleItem, Product, User
            from sqlalchemy import func
            
            # Consulta base de ventas
            base_query = db.query(PointOfSaleTransaction).filter(
                PointOfSaleTransaction.transaction_time >= start_dt,
                PointOfSaleTransaction.transaction_time <= end_dt
            )
            
            # Estadísticas generales
            total_transactions = base_query.count()
            total_revenue = base_query.with_entities(
                func.sum(PointOfSaleTransaction.total_amount)
            ).scalar() or 0
            
            # Ventas por día/semana/mes según group_by
            if group_by == 'day':
                date_group = func.date(PointOfSaleTransaction.transaction_time)
                date_format = '%Y-%m-%d'
            elif group_by == 'week':
                date_group = func.date_trunc('week', PointOfSaleTransaction.transaction_time)
                date_format = '%Y-W%U'
            else:  # month
                date_group = func.date_trunc('month', PointOfSaleTransaction.transaction_time)
                date_format = '%Y-%m'
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': f'Agrupando ventas por {group_by}'}
            )
            
            sales_by_period = db.query(
                date_group.label('period'),
                func.count(PointOfSaleTransaction.id).label('transactions'),
                func.sum(PointOfSaleTransaction.total_amount).label('revenue')
            ).filter(
                PointOfSaleTransaction.transaction_time >= start_dt,
                PointOfSaleTransaction.transaction_time <= end_dt
            ).group_by(date_group).order_by(date_group).all()
            
            # Top productos vendidos en el período
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando productos más vendidos'}
            )
            
            top_products = db.query(
                Product,
                func.sum(PointOfSaleItem.quantity_sold).label('total_sold'),
                func.sum(PointOfSaleItem.quantity_sold * PointOfSaleItem.price_at_time_of_sale).label('total_revenue'),
                func.count(PointOfSaleItem.id).label('transaction_count')
            ).join(
                PointOfSaleItem, Product.id == PointOfSaleItem.product_id
            ).join(
                PointOfSaleTransaction, PointOfSaleItem.transaction_id == PointOfSaleTransaction.id
            ).filter(
                PointOfSaleTransaction.transaction_time >= start_dt,
                PointOfSaleTransaction.transaction_time <= end_dt
            ).group_by(Product.id).order_by(func.sum(PointOfSaleItem.quantity_sold).desc()).limit(20).all()
            
            # Ventas por vendedor/usuario
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando ventas por usuario'}
            )
            
            sales_by_user = db.query(
                User,
                func.count(PointOfSaleTransaction.id).label('transactions'),
                func.sum(PointOfSaleTransaction.total_amount).label('revenue')
            ).join(
                PointOfSaleTransaction, User.id == PointOfSaleTransaction.user_id
            ).filter(
                PointOfSaleTransaction.transaction_time >= start_dt,
                PointOfSaleTransaction.transaction_time <= end_dt
            ).group_by(User.id).order_by(func.sum(PointOfSaleTransaction.total_amount).desc()).all()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Compilando reporte final'}
            )
            
            # Compilar reporte
            report_data = {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'group_by': group_by
                },
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_transactions': total_transactions,
                    'total_revenue': float(total_revenue),
                    'average_transaction': float(total_revenue / total_transactions) if total_transactions > 0 else 0,
                    'days_in_period': (end_dt - start_dt).days + 1
                },
                'sales_by_period': [
                    {
                        'period': period.period.strftime(date_format) if hasattr(period.period, 'strftime') else str(period.period),
                        'transactions': period.transactions,
                        'revenue': float(period.revenue or 0)
                    } for period in sales_by_period
                ],
                'top_products': [
                    {
                        'product': {
                            'id': item.Product.id,
                            'name': item.Product.name,
                            'sku': item.Product.sku
                        },
                        'units_sold': item.total_sold,
                        'revenue': float(item.total_revenue),
                        'transaction_count': item.transaction_count,
                        'average_per_transaction': float(item.total_sold / item.transaction_count) if item.transaction_count > 0 else 0
                    } for item in top_products
                ],
                'sales_by_user': [
                    {
                        'user': {
                            'id': item.User.id,
                            'username': item.User.username
                        },
                        'transactions': item.transactions,
                        'revenue': float(item.revenue or 0),
                        'average_per_transaction': float(item.revenue / item.transactions) if item.transactions > 0 else 0
                    } for item in sales_by_user
                ]
            }
            
            # Guardar reporte en auditoría
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Reporte de ventas generado ({start_date} a {end_date})",
                additional_data={'report_summary': report_data['summary']},
                severity=AuditSeverity.LOW
            )
            
            result = {
                'status': 'completed',
                'message': f'Reporte de ventas generado del {start_date} al {end_date}',
                'report_data': report_data
            }
            
            logger.info("Reporte de ventas generado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generando reporte de ventas: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.report_tasks.generate_consignment_report")
def generate_consignment_report(self, distributor_id: Optional[int] = None):
    """Tarea para generar reporte de consignaciones"""
    
    try:
        logger.info(f"Generando reporte de consignaciones{f' para distribuidor {distributor_id}' if distributor_id else ''}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando generación de reporte de consignaciones'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Consultando datos de consignaciones'}
            )
            
            from ..models import ConsignmentLoan, ConsignmentReport, Distributor, Product
            from sqlalchemy import func
            from sqlalchemy.orm import joinedload
            
            # Query base
            base_query = db.query(ConsignmentLoan).options(
                joinedload(ConsignmentLoan.distributor),
                joinedload(ConsignmentLoan.product)
            )
            
            if distributor_id:
                base_query = base_query.filter(ConsignmentLoan.distributor_id == distributor_id)
            
            # Estadísticas generales
            total_loans = base_query.count()
            active_loans = base_query.filter(ConsignmentLoan.status == 'en_prestamo').count()
            completed_loans = base_query.filter(ConsignmentLoan.status == 'devuelto').count()
            
            # Préstamos por estado
            loans_by_status = db.query(
                ConsignmentLoan.status,
                func.count(ConsignmentLoan.id).label('count'),
                func.sum(ConsignmentLoan.quantity_loaned).label('total_quantity')
            ).group_by(ConsignmentLoan.status)
            
            if distributor_id:
                loans_by_status = loans_by_status.filter(ConsignmentLoan.distributor_id == distributor_id)
            
            loans_by_status = loans_by_status.all()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando reportes de consignación'}
            )
            
            # Estadísticas de reportes
            reports_query = db.query(
                func.sum(ConsignmentReport.quantity_sold).label('total_sold'),
                func.sum(ConsignmentReport.quantity_returned).label('total_returned'),
                func.count(ConsignmentReport.id).label('total_reports')
            ).join(ConsignmentLoan, ConsignmentReport.loan_id == ConsignmentLoan.id)
            
            if distributor_id:
                reports_query = reports_query.filter(ConsignmentLoan.distributor_id == distributor_id)
            
            report_stats = reports_query.first()
            
            # Distribuidores con más préstamos activos
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando actividad por distribuidor'}
            )
            
            if not distributor_id:
                top_distributors = db.query(
                    Distributor,
                    func.count(ConsignmentLoan.id).label('total_loans'),
                    func.sum(ConsignmentLoan.quantity_loaned).label('total_quantity')
                ).join(
                    ConsignmentLoan, Distributor.id == ConsignmentLoan.distributor_id
                ).group_by(Distributor.id).order_by(
                    func.count(ConsignmentLoan.id).desc()
                ).limit(10).all()
            else:
                top_distributors = []
            
            # Productos más consignados
            top_products = db.query(
                Product,
                func.count(ConsignmentLoan.id).label('loan_count'),
                func.sum(ConsignmentLoan.quantity_loaned).label('total_loaned')
            ).join(
                ConsignmentLoan, Product.id == ConsignmentLoan.product_id
            )
            
            if distributor_id:
                top_products = top_products.filter(ConsignmentLoan.distributor_id == distributor_id)
            
            top_products = top_products.group_by(Product.id).order_by(
                func.sum(ConsignmentLoan.quantity_loaned).desc()
            ).limit(15).all()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Compilando reporte final'}
            )
            
            # Compilar reporte
            report_data = {
                'generated_at': datetime.utcnow().isoformat(),
                'distributor_id': distributor_id,
                'summary': {
                    'total_loans': total_loans,
                    'active_loans': active_loans,
                    'completed_loans': completed_loans,
                    'total_units_sold': report_stats.total_sold or 0,
                    'total_units_returned': report_stats.total_returned or 0,
                    'total_reports': report_stats.total_reports or 0
                },
                'loans_by_status': [
                    {
                        'status': item.status,
                        'count': item.count,
                        'total_quantity': item.total_quantity or 0
                    } for item in loans_by_status
                ],
                'top_distributors': [
                    {
                        'distributor': {
                            'id': item.Distributor.id,
                            'name': item.Distributor.name,
                            'contact_person': item.Distributor.contact_person
                        },
                        'total_loans': item.total_loans,
                        'total_quantity': item.total_quantity or 0
                    } for item in top_distributors
                ],
                'top_products': [
                    {
                        'product': {
                            'id': item.Product.id,
                            'name': item.Product.name,
                            'sku': item.Product.sku
                        },
                        'loan_count': item.loan_count,
                        'total_loaned': item.total_loaned or 0
                    } for item in top_products
                ]
            }
            
            # Guardar reporte en auditoría
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType, AuditSeverity
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Reporte de consignaciones generado{f' para distribuidor {distributor_id}' if distributor_id else ''}",
                additional_data={'report_summary': report_data['summary']},
                severity=AuditSeverity.LOW
            )
            
            result = {
                'status': 'completed',
                'message': f'Reporte de consignaciones generado exitosamente',
                'report_data': report_data
            }
            
            logger.info("Reporte de consignaciones generado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generando reporte de consignaciones: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)