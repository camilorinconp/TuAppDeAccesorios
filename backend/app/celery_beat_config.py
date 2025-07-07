# ==================================================================
# CONFIGURACIÓN DE TAREAS PROGRAMADAS - CELERY BEAT
# ==================================================================

from celery.schedules import crontab
from datetime import timedelta

# ==================================================================
# CONFIGURACIÓN DE TAREAS PERIÓDICAS
# ==================================================================

CELERY_BEAT_SCHEDULE = {
    # ================================================================
    # TAREAS DE MANTENIMIENTO DIARIO
    # ================================================================
    
    'daily-inventory-report': {
        'task': 'app.tasks.report_tasks.generate_daily_inventory_report',
        'schedule': crontab(hour=6, minute=0),  # Todos los días a las 6:00 AM
        'options': {'queue': 'reports'}
    },
    
    'daily-summary-notification': {
        'task': 'app.tasks.notification_tasks.send_daily_summary_task',
        'schedule': crontab(hour=7, minute=30),  # Todos los días a las 7:30 AM
        'options': {'queue': 'notifications'}
    },
    
    'daily-security-report': {
        'task': 'app.tasks.audit_tasks.generate_security_report_task',
        'schedule': crontab(hour=8, minute=0),  # Todos los días a las 8:00 AM
        'options': {'queue': 'audit'}
    },
    
    # ================================================================
    # TAREAS DE VERIFICACIÓN DE INVENTARIO
    # ================================================================
    
    'check-low-stock-morning': {
        'task': 'app.tasks.inventory_tasks.check_low_stock_task',
        'schedule': crontab(hour=9, minute=0),  # Todos los días a las 9:00 AM
        'args': [5],  # threshold = 5
        'options': {'queue': 'inventory'}
    },
    
    'check-low-stock-afternoon': {
        'task': 'app.tasks.inventory_tasks.check_low_stock_task',
        'schedule': crontab(hour=15, minute=0),  # Todos los días a las 3:00 PM
        'args': [5],  # threshold = 5
        'options': {'queue': 'inventory'}
    },
    
    'check-overdue-consignments': {
        'task': 'app.tasks.inventory_tasks.check_overdue_consignments_task',
        'schedule': crontab(hour=10, minute=0),  # Todos los días a las 10:00 AM
        'options': {'queue': 'inventory'}
    },
    
    # ================================================================
    # TAREAS DE OPTIMIZACIÓN Y MANTENIMIENTO
    # ================================================================
    
    'cleanup-cache-hourly': {
        'task': 'app.tasks.product_tasks.cleanup_cache_task',
        'schedule': timedelta(hours=1),  # Cada hora
        'options': {'queue': 'maintenance'}
    },
    
    'optimize-database-daily': {
        'task': 'app.tasks.product_tasks.optimize_database_task',
        'schedule': crontab(hour=2, minute=0),  # Todos los días a las 2:00 AM
        'options': {'queue': 'maintenance'}
    },
    
    'warm-up-cache-morning': {
        'task': 'app.tasks.product_tasks.warm_up_cache_task',
        'schedule': crontab(hour=7, minute=0),  # Todos los días a las 7:00 AM
        'options': {'queue': 'maintenance'}
    },
    
    'system-health-check': {
        'task': 'app.tasks.audit_tasks.analyze_system_health_task',
        'schedule': crontab(hour=12, minute=0),  # Todos los días al mediodía
        'options': {'queue': 'audit'}
    },
    
    # ================================================================
    # TAREAS DE LIMPIEZA Y AUDITORÍA
    # ================================================================
    
    'cleanup-audit-logs-weekly': {
        'task': 'app.tasks.audit_tasks.cleanup_old_audit_logs_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Domingos a las 3:00 AM
        'args': [90],  # Mantener 90 días
        'options': {'queue': 'audit'}
    },
    
    'backup-critical-data-daily': {
        'task': 'app.tasks.audit_tasks.backup_critical_data_task',
        'schedule': crontab(hour=1, minute=0),  # Todos los días a la 1:00 AM
        'args': ['incremental'],
        'options': {'queue': 'backup'}
    },
    
    'backup-critical-data-weekly': {
        'task': 'app.tasks.audit_tasks.backup_critical_data_task',
        'schedule': crontab(hour=0, minute=0, day_of_week=0),  # Domingos a medianoche
        'args': ['full'],
        'options': {'queue': 'backup'}
    },
    
    # ================================================================
    # TAREAS DE SINCRONIZACIÓN Y REPORTES SEMANALES
    # ================================================================
    
    'weekly-sales-report': {
        'task': 'app.tasks.report_tasks.generate_sales_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Lunes a las 9:00 AM
        'kwargs': {
            'start_date': '{{ (now() - timedelta(days=7)).strftime("%Y-%m-%d") }}',
            'end_date': '{{ (now() - timedelta(days=1)).strftime("%Y-%m-%d") }}',
            'group_by': 'day'
        },
        'options': {'queue': 'reports'}
    },
    
    'weekly-consignment-report': {
        'task': 'app.tasks.report_tasks.generate_consignment_report',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Lunes a las 10:00 AM
        'options': {'queue': 'reports'}
    },
    
    'inventory-reconciliation-weekly': {
        'task': 'app.tasks.inventory_tasks.reconcile_inventory_task',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Domingos a las 4:00 AM
        'args': ['main_warehouse'],
        'options': {'queue': 'inventory'}
    },
    
    'sync-product-data-daily': {
        'task': 'app.tasks.product_tasks.sync_product_data_task',
        'schedule': crontab(hour=5, minute=0),  # Todos los días a las 5:00 AM
        'options': {'queue': 'maintenance'}
    },
    
    # ================================================================
    # TAREAS DE REPORTES MENSUALES
    # ================================================================
    
    'monthly-sales-report': {
        'task': 'app.tasks.report_tasks.generate_sales_report',
        'schedule': crontab(hour=8, minute=0, day_of_month=1),  # Primer día del mes a las 8:00 AM
        'kwargs': {
            'start_date': '{{ (now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d") }}',
            'end_date': '{{ (now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d") }}',
            'group_by': 'week'
        },
        'options': {'queue': 'reports'}
    },
}

# ==================================================================
# CONFIGURACIÓN DE COLAS Y ROUTING
# ==================================================================

CELERY_TASK_ROUTES = {
    # Tareas de productos y caché
    'app.tasks.product_tasks.*': {'queue': 'maintenance'},
    
    # Tareas de inventario
    'app.tasks.inventory_tasks.*': {'queue': 'inventory'},
    
    # Tareas de reportes
    'app.tasks.report_tasks.*': {'queue': 'reports'},
    
    # Tareas de auditoría y seguridad
    'app.tasks.audit_tasks.*': {'queue': 'audit'},
    
    # Tareas de notificaciones
    'app.tasks.notification_tasks.*': {'queue': 'notifications'},
}

# ==================================================================
# CONFIGURACIÓN DE TIMEOUT Y RETRIES
# ==================================================================

CELERY_TASK_ANNOTATIONS = {
    # Tareas de productos
    'app.tasks.product_tasks.cleanup_cache_task': {
        'rate_limit': '10/m',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    'app.tasks.product_tasks.optimize_database_task': {
        'rate_limit': '1/h',
        'time_limit': 1800,  # 30 minutos
        'soft_time_limit': 1500
    },
    'app.tasks.product_tasks.warm_up_cache_task': {
        'rate_limit': '5/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
    'app.tasks.product_tasks.sync_product_data_task': {
        'rate_limit': '3/m',
        'time_limit': 900,
        'soft_time_limit': 720
    },
    'app.tasks.product_tasks.bulk_update_products_task': {
        'rate_limit': '2/m',
        'time_limit': 1200,
        'soft_time_limit': 900
    },
    
    # Tareas de inventario
    'app.tasks.inventory_tasks.check_low_stock_task': {
        'rate_limit': '10/m',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    'app.tasks.inventory_tasks.update_stock_levels_task': {
        'rate_limit': '5/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
    'app.tasks.inventory_tasks.reconcile_inventory_task': {
        'rate_limit': '1/h',
        'time_limit': 1800,
        'soft_time_limit': 1500
    },
    'app.tasks.inventory_tasks.check_overdue_consignments_task': {
        'rate_limit': '5/m',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    
    # Tareas de reportes
    'app.tasks.report_tasks.generate_daily_inventory_report': {
        'rate_limit': '3/m',
        'time_limit': 900,
        'soft_time_limit': 720
    },
    'app.tasks.report_tasks.generate_sales_report': {
        'rate_limit': '2/m',
        'time_limit': 1200,
        'soft_time_limit': 900
    },
    'app.tasks.report_tasks.generate_consignment_report': {
        'rate_limit': '3/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
    
    # Tareas de auditoría
    'app.tasks.audit_tasks.cleanup_old_audit_logs_task': {
        'rate_limit': '1/h',
        'time_limit': 1800,
        'soft_time_limit': 1500
    },
    'app.tasks.audit_tasks.generate_security_report_task': {
        'rate_limit': '3/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
    'app.tasks.audit_tasks.analyze_system_health_task': {
        'rate_limit': '5/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
    'app.tasks.audit_tasks.backup_critical_data_task': {
        'rate_limit': '1/h',
        'time_limit': 3600,  # 1 hora
        'soft_time_limit': 3000
    },
    
    # Tareas de notificaciones
    'app.tasks.notification_tasks.send_low_stock_alert_task': {
        'rate_limit': '20/m',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    'app.tasks.notification_tasks.send_overdue_consignments_alert_task': {
        'rate_limit': '10/m',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    'app.tasks.notification_tasks.send_daily_summary_task': {
        'rate_limit': '5/m',
        'time_limit': 600,
        'soft_time_limit': 480
    },
}

# ==================================================================
# CONFIGURACIÓN DE TIMEZONE
# ==================================================================

CELERY_TIMEZONE = 'America/Bogota'  # Zona horaria de Colombia
CELERY_ENABLE_UTC = True