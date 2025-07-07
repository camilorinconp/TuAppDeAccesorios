# ==================================================================
# CONFIGURACIÓN CELERY - BACKGROUND JOBS Y TAREAS ASÍNCRONAS
# ==================================================================

import os
from celery import Celery
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

# Configuración de Redis como broker y backend
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Crear instancia de Celery
celery_app = Celery(
    "tuapp_workers",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.tasks.product_tasks",
        "app.tasks.inventory_tasks", 
        "app.tasks.report_tasks",
        "app.tasks.audit_tasks",
        "app.tasks.notification_tasks"
    ]
)

# Importar configuración de Celery Beat
from .celery_beat_config import (
    CELERY_BEAT_SCHEDULE,
    CELERY_TASK_ROUTES,
    CELERY_TASK_ANNOTATIONS,
    CELERY_TIMEZONE,
    CELERY_ENABLE_UTC
)

# Configuración de Celery
celery_app.conf.update(
    # Configuración del broker
    broker_url=redis_url,
    result_backend=redis_url,
    
    # Configuración de tareas
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=CELERY_TIMEZONE,
    enable_utc=CELERY_ENABLE_UTC,
    
    # Configuración de workers
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Configuración de resultados
    result_expires=3600,  # 1 hora
    result_persistent=True,
    
    # Configuración de Celery Beat (tareas programadas)
    beat_schedule=CELERY_BEAT_SCHEDULE,
    beat_schedule_filename='celerybeat-schedule',
    
    # Configuración de routing
    task_routes=CELERY_TASK_ROUTES,
    
    # Configuración de anotaciones de tareas (timeouts, rate limits, etc.)
    task_annotations=CELERY_TASK_ANNOTATIONS,
    
    # Configuración de colas
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Configuración de retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Configuración de monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Configuración de seguridad
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Configuración de compresión
    task_compression='gzip',
    result_compression='gzip',
)

# Configuración de logging para Celery
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configurar tareas periódicas adicionales"""
    logger.info("Configurando tareas periódicas de Celery")

@celery_app.on_after_finalize.connect  
def setup_celery_logging(sender, **kwargs):
    """Configurar logging de Celery"""
    import logging
    
    # Configurar nivel de logging para Celery
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('celery.task').setLevel(logging.INFO)
    logging.getLogger('celery.worker').setLevel(logging.INFO)
    
    logger.info("Logging de Celery configurado")

# Event handlers para monitoreo
from celery.signals import task_prerun, task_postrun, task_failure

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handler antes de ejecutar tarea"""
    logger.info(f"Iniciando tarea: {sender.name} (ID: {task_id})")

@task_postrun.connect  
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handler después de ejecutar tarea"""
    logger.info(f"Tarea completada: {sender.name} (ID: {task_id}, Estado: {state})")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Handler para fallos de tareas"""
    logger.error(f"Tarea falló: {sender.name} (ID: {task_id}, Error: {exception})")

# Configuración adicional para desarrollo
if settings.environment == "development":
    celery_app.conf.update(
        worker_log_level="DEBUG",
        worker_redirect_stdouts_level="DEBUG"
    )

logger.info("Celery configurado correctamente")