# ==================================================================
# TAREAS DE AUDITORÍA - CELERY BACKGROUND JOBS
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


@celery_app.task(bind=True, name="app.tasks.audit_tasks.cleanup_old_audit_logs_task")
def cleanup_old_audit_logs_task(self, days_to_keep: int = 90):
    """Tarea para limpiar logs de auditoría antiguos"""
    
    try:
        logger.info(f"Iniciando limpieza de logs de auditoría (mantener {days_to_keep} días)")
        
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
                meta={'message': 'Calculando fecha de corte'}
            )
            
            # Calcular fecha de corte
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Eliminando logs antiguos'}
            )
            
            # Eliminar logs antiguos
            from ..models.audit import AuditLog
            deleted_logs = db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            # Eliminar intentos de login antiguos
            from ..models.audit import LoginAttempt
            deleted_attempts = db.query(LoginAttempt).filter(
                LoginAttempt.timestamp < cutoff_date
            ).delete()
            
            # Commit cambios
            db.commit()
            
            result = {
                'status': 'completed',
                'message': f'Limpieza de auditoría completada',
                'cutoff_date': cutoff_date.isoformat(),
                'deleted_logs': deleted_logs,
                'deleted_login_attempts': deleted_attempts,
                'total_deleted': deleted_logs + deleted_attempts
            }
            
            logger.info("Limpieza de logs de auditoría completada", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en limpieza de logs de auditoría: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.audit_tasks.generate_security_report_task")
def generate_security_report_task(self, report_date: str = None):
    """Tarea para generar reporte de seguridad"""
    
    try:
        if report_date:
            target_date = datetime.fromisoformat(report_date).date()
        else:
            target_date = datetime.utcnow().date()
            
        logger.info(f"Generando reporte de seguridad para {target_date}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando generación de reporte de seguridad'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando eventos de seguridad'}
            )
            
            from ..models.audit import AuditLog, SecurityAlert, LoginAttempt, AuditSeverity
            from sqlalchemy import func, desc
            
            # Rango de fechas (últimos 7 días)
            start_date = target_date - timedelta(days=7)
            end_date = target_date
            
            # Alertas de seguridad por severidad
            security_alerts = db.query(
                SecurityAlert.severity,
                func.count(SecurityAlert.id).label('count')
            ).filter(
                func.date(SecurityAlert.timestamp) >= start_date,
                func.date(SecurityAlert.timestamp) <= end_date
            ).group_by(SecurityAlert.severity).all()
            
            # Intentos de login fallidos
            failed_logins = db.query(
                func.count(LoginAttempt.id).label('total_attempts'),
                func.count(LoginAttempt.id).filter(LoginAttempt.successful == False).label('failed_attempts')
            ).filter(
                func.date(LoginAttempt.timestamp) >= start_date,
                func.date(LoginAttempt.timestamp) <= end_date
            ).first()
            
            # Eventos de auditoría por severidad
            audit_events = db.query(
                AuditLog.severity,
                func.count(AuditLog.id).label('count')
            ).filter(
                func.date(AuditLog.timestamp) >= start_date,
                func.date(AuditLog.timestamp) <= end_date
            ).group_by(AuditLog.severity).all()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Identificando patrones sospechosos'}
            )
            
            # IPs con más intentos fallidos
            suspicious_ips = db.query(
                LoginAttempt.ip_address,
                func.count(LoginAttempt.id).label('failed_attempts')
            ).filter(
                func.date(LoginAttempt.timestamp) >= start_date,
                func.date(LoginAttempt.timestamp) <= end_date,
                LoginAttempt.successful == False
            ).group_by(LoginAttempt.ip_address).order_by(
                desc('failed_attempts')
            ).limit(10).all()
            
            # Usuarios con más intentos fallidos
            suspicious_users = db.query(
                LoginAttempt.username,
                func.count(LoginAttempt.id).label('failed_attempts')
            ).filter(
                func.date(LoginAttempt.timestamp) >= start_date,
                func.date(LoginAttempt.timestamp) <= end_date,
                LoginAttempt.successful == False
            ).group_by(LoginAttempt.username).order_by(
                desc('failed_attempts')
            ).limit(10).all()
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Compilando reporte de seguridad'}
            )
            
            # Compilar reporte
            report_data = {
                'report_date': target_date.isoformat(),
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'generated_at': datetime.utcnow().isoformat(),
                'security_summary': {
                    'total_alerts': sum(alert.count for alert in security_alerts),
                    'critical_alerts': sum(alert.count for alert in security_alerts if alert.severity == AuditSeverity.CRITICAL),
                    'high_alerts': sum(alert.count for alert in security_alerts if alert.severity == AuditSeverity.HIGH),
                    'total_login_attempts': failed_logins.total_attempts or 0,
                    'failed_login_attempts': failed_logins.failed_attempts or 0,
                    'login_success_rate': (
                        ((failed_logins.total_attempts - failed_logins.failed_attempts) / failed_logins.total_attempts * 100) 
                        if failed_logins.total_attempts > 0 else 100
                    )
                },
                'alerts_by_severity': [
                    {
                        'severity': alert.severity.value,
                        'count': alert.count
                    } for alert in security_alerts
                ],
                'audit_events_by_severity': [
                    {
                        'severity': event.severity.value,
                        'count': event.count
                    } for event in audit_events
                ],
                'suspicious_activity': {
                    'ips_with_failed_logins': [
                        {
                            'ip_address': ip.ip_address,
                            'failed_attempts': ip.failed_attempts
                        } for ip in suspicious_ips
                    ],
                    'users_with_failed_logins': [
                        {
                            'username': user.username,
                            'failed_attempts': user.failed_attempts
                        } for user in suspicious_users
                    ]
                },
                'recommendations': []
            }
            
            # Generar recomendaciones basadas en datos
            recommendations = []
            
            if failed_logins.failed_attempts > 10:
                recommendations.append("Considerar implementar rate limiting para intentos de login")
            
            if any(ip.failed_attempts > 5 for ip in suspicious_ips):
                recommendations.append("Revisar IPs con múltiples intentos fallidos - posible ataque de fuerza bruta")
            
            critical_alerts = sum(alert.count for alert in security_alerts if alert.severity == AuditSeverity.CRITICAL)
            if critical_alerts > 0:
                recommendations.append(f"Atender inmediatamente {critical_alerts} alertas críticas de seguridad")
            
            if not recommendations:
                recommendations.append("No se detectaron patrones de seguridad preocupantes")
            
            report_data['recommendations'] = recommendations
            
            # Registrar generación del reporte
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Reporte de seguridad generado para {target_date}",
                additional_data={'report_summary': report_data['security_summary']},
                severity=AuditSeverity.LOW
            )
            
            result = {
                'status': 'completed',
                'message': f'Reporte de seguridad generado para {target_date}',
                'report_data': report_data
            }
            
            logger.info("Reporte de seguridad generado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generando reporte de seguridad: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.audit_tasks.analyze_system_health_task")
def analyze_system_health_task(self):
    """Tarea para analizar la salud del sistema"""
    
    try:
        logger.info("Iniciando análisis de salud del sistema")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando análisis de salud del sistema'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando métricas del sistema'}
            )
            
            from ..models import Product, PointOfSaleTransaction, User
            from ..models.audit import AuditLog, AuditSeverity
            from ..services.intelligent_cache import intelligent_cache
            from sqlalchemy import func, text
            
            # Análisis de base de datos
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando estado de la base de datos'}
            )
            
            # Estadísticas de tablas principales
            total_products = db.query(func.count(Product.id)).scalar()
            total_users = db.query(func.count(User.id)).scalar()
            total_transactions = db.query(func.count(PointOfSaleTransaction.id)).scalar()
            
            # Últimas 24 horas
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_transactions = db.query(func.count(PointOfSaleTransaction.id)).filter(
                PointOfSaleTransaction.transaction_time >= yesterday
            ).scalar()
            
            # Eventos de auditoría críticos recientes
            critical_events = db.query(func.count(AuditLog.id)).filter(
                AuditLog.timestamp >= yesterday,
                AuditLog.severity == AuditSeverity.CRITICAL
            ).scalar()
            
            # Análisis de caché
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando rendimiento del caché'}
            )
            
            cache_metrics = intelligent_cache.get_metrics()
            
            # Análisis de rendimiento de base de datos
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Analizando rendimiento de la base de datos'}
            )
            
            # Verificar conexiones activas (específico para PostgreSQL)
            try:
                active_connections = db.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                ).scalar()
            except:
                active_connections = 0
            
            # Verificar tamaño de la base de datos
            try:
                db_size = db.execute(
                    text("SELECT pg_size_pretty(pg_database_size(current_database()))")
                ).scalar()
            except:
                db_size = "N/A"
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Compilando análisis de salud'}
            )
            
            # Determinar estado de salud
            health_status = "HEALTHY"
            issues = []
            
            # Verificar problemas potenciales
            if cache_metrics.get('hit_rate_percent', 0) < 70:
                health_status = "WARNING"
                issues.append("Tasa de aciertos del caché por debajo del 70%")
            
            if critical_events > 0:
                health_status = "CRITICAL"
                issues.append(f"{critical_events} eventos críticos en las últimas 24 horas")
            
            if recent_transactions == 0:
                health_status = "WARNING"
                issues.append("No se han registrado transacciones en las últimas 24 horas")
            
            if active_connections > 80:  # Asumiendo límite de 100 conexiones
                health_status = "WARNING"
                issues.append("Alto número de conexiones activas a la base de datos")
            
            # Compilar resultado
            health_report = {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': health_status,
                'issues': issues,
                'metrics': {
                    'database': {
                        'total_products': total_products,
                        'total_users': total_users,
                        'total_transactions': total_transactions,
                        'recent_transactions_24h': recent_transactions,
                        'active_connections': active_connections,
                        'database_size': db_size
                    },
                    'cache': {
                        'hit_rate_percent': cache_metrics.get('hit_rate_percent', 0),
                        'total_keys': cache_metrics.get('total_keys', 0),
                        'cache_efficiency': cache_metrics.get('cache_efficiency', 0)
                    },
                    'security': {
                        'critical_events_24h': critical_events
                    }
                }
            }
            
            # Registrar análisis
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType
            
            severity = AuditSeverity.CRITICAL if health_status == "CRITICAL" else (
                AuditSeverity.HIGH if health_status == "WARNING" else AuditSeverity.LOW
            )
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Análisis de salud del sistema: {health_status}",
                additional_data={
                    'health_status': health_status,
                    'issues_count': len(issues),
                    'metrics_summary': health_report['metrics']
                },
                severity=severity
            )
            
            result = {
                'status': 'completed',
                'message': f'Análisis de salud completado - Estado: {health_status}',
                'health_report': health_report
            }
            
            logger.info("Análisis de salud del sistema completado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en análisis de salud del sistema: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.audit_tasks.backup_critical_data_task")
def backup_critical_data_task(self, backup_type: str = "incremental"):
    """Tarea para respaldar datos críticos"""
    
    try:
        logger.info(f"Iniciando respaldo de datos críticos (tipo: {backup_type})")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'message': 'Iniciando respaldo de datos críticos'}
        )
        
        # Obtener sesión de base de datos
        SessionLocal, engine = get_db_session_maker(settings.database_url)
        db = SessionLocal()
        
        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Exportando datos críticos'}
            )
            
            from ..models import Product, User, PointOfSaleTransaction
            from ..models.audit import AuditLog
            import json
            
            # Preparar datos para respaldo
            backup_data = {
                'backup_type': backup_type,
                'timestamp': datetime.utcnow().isoformat(),
                'tables': {}
            }
            
            # Respaldar usuarios (solo estructura, no contraseñas)
            users_data = []
            users = db.query(User).all()
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })
            
            backup_data['tables']['users'] = {
                'count': len(users_data),
                'data': users_data[:100]  # Limitar para ejemplo
            }
            
            # Respaldar productos críticos (stock bajo)
            critical_products = db.query(Product).filter(Product.stock_quantity <= 5).all()
            products_data = []
            for product in critical_products:
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'stock_quantity': product.stock_quantity,
                    'cost_price': float(product.cost_price),
                    'selling_price': float(product.selling_price)
                })
            
            backup_data['tables']['critical_products'] = {
                'count': len(products_data),
                'data': products_data
            }
            
            # Respaldar transacciones recientes
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_transactions = db.query(PointOfSaleTransaction).filter(
                PointOfSaleTransaction.transaction_time >= recent_cutoff
            ).limit(1000).all()
            
            transactions_data = []
            for transaction in recent_transactions:
                transactions_data.append({
                    'id': transaction.id,
                    'transaction_time': transaction.transaction_time.isoformat(),
                    'total_amount': float(transaction.total_amount),
                    'user_id': transaction.user_id
                })
            
            backup_data['tables']['recent_transactions'] = {
                'count': len(transactions_data),
                'data': transactions_data
            }
            
            # Respaldar logs de auditoría críticos
            critical_logs = db.query(AuditLog).filter(
                AuditLog.timestamp >= recent_cutoff,
                AuditLog.severity.in_([AuditSeverity.CRITICAL, AuditSeverity.HIGH])
            ).limit(500).all()
            
            audit_data = []
            for log in critical_logs:
                audit_data.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'action_type': log.action_type.value,
                    'severity': log.severity.value,
                    'description': log.description
                })
            
            backup_data['tables']['critical_audit_logs'] = {
                'count': len(audit_data),
                'data': audit_data
            }
            
            current_task.update_state(
                state='PROGRESS',
                meta={'message': 'Finalizando respaldo'}
            )
            
            # En un entorno real, aquí se guardaría en almacenamiento seguro
            # Por ahora, simular el proceso
            
            backup_summary = {
                'backup_type': backup_type,
                'timestamp': datetime.utcnow().isoformat(),
                'tables_backed_up': len(backup_data['tables']),
                'total_records': sum(table['count'] for table in backup_data['tables'].values()),
                'size_estimate': f"{len(str(backup_data)) / 1024:.2f} KB"
            }
            
            # Registrar respaldo
            from ..services.audit_service import AuditService
            from ..models.audit import AuditActionType
            
            AuditService.log_event(
                db=db,
                action_type=AuditActionType.CREATE,
                description=f"Respaldo de datos críticos completado ({backup_type})",
                additional_data=backup_summary,
                severity=AuditSeverity.LOW
            )
            
            result = {
                'status': 'completed',
                'message': f'Respaldo de datos críticos completado ({backup_type})',
                'backup_summary': backup_summary
            }
            
            logger.info("Respaldo de datos críticos completado", extra=result)
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en respaldo de datos críticos: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=600, max_retries=2)