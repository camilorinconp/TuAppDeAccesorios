# ==================================================================
# TASKS PACKAGE - TAREAS BACKGROUND CON CELERY
# ==================================================================

"""
Paquete de tareas en background para TuAppDeAccesorios

Incluye:
- product_tasks: Tareas relacionadas con productos
- inventory_tasks: Tareas de inventario y stock
- report_tasks: Generación de reportes
- audit_tasks: Tareas de auditoría y limpieza
- notification_tasks: Notificaciones y alertas
"""

from .product_tasks import *
from .inventory_tasks import *
from .report_tasks import *
from .audit_tasks import *
from .notification_tasks import *