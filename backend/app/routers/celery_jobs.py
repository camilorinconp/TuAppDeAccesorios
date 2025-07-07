# ==================================================================
# ROUTER DE GESTIÓN DE TRABAJOS CELERY
# ==================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import GenericResponse
from ..logging_config import get_logger
from ..celery_app import celery_app

# Importar tareas
from ..tasks.product_tasks import (
    cleanup_cache_task,
    optimize_database_task,
    warm_up_cache_task,
    sync_product_data_task,
    bulk_update_products_task
)
from ..tasks.inventory_tasks import (
    check_low_stock_task,
    update_stock_levels_task,
    reconcile_inventory_task,
    check_overdue_consignments_task
)
from ..tasks.report_tasks import (
    generate_daily_inventory_report,
    generate_sales_report,
    generate_consignment_report
)
from ..tasks.audit_tasks import (
    cleanup_old_audit_logs_task,
    generate_security_report_task,
    analyze_system_health_task,
    backup_critical_data_task
)
from ..tasks.notification_tasks import (
    send_low_stock_alert_task,
    send_overdue_consignments_alert_task,
    send_daily_summary_task
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/celery",
    tags=["celery_jobs"],
    responses={404: {"description": "Not found"}},
)


# ==================================================================
# GESTIÓN DE TRABAJOS - INICIO Y MONITOREO
# ==================================================================

@router.get("/jobs/active", response_model=Dict[str, Any])
async def get_active_jobs(
    current_user: User = Depends(get_current_user)
):
    """Obtener trabajos activos de Celery"""
    
    try:
        # Verificar permisos (solo admin puede ver trabajos)
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ver trabajos de Celery"
            )
        
        # Obtener trabajos activos
        active_tasks = celery_app.control.inspect().active()
        
        # Formatear resultado
        active_jobs = []
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    active_jobs.append({
                        'task_id': task.get('id'),
                        'task_name': task.get('name'),
                        'worker': worker,
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'time_start': task.get('time_start')
                    })
        
        return {
            'active_jobs': active_jobs,
            'total_active': len(active_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo trabajos activos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo trabajos activos: {str(e)}"
        )


@router.get("/jobs/scheduled", response_model=Dict[str, Any])
async def get_scheduled_jobs(
    current_user: User = Depends(get_current_user)
):
    """Obtener trabajos programados de Celery"""
    
    try:
        # Verificar permisos
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ver trabajos programados"
            )
        
        # Obtener trabajos programados
        scheduled_tasks = celery_app.control.inspect().scheduled()
        
        # Formatear resultado
        scheduled_jobs = []
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    scheduled_jobs.append({
                        'task_id': task.get('request', {}).get('id'),
                        'task_name': task.get('request', {}).get('name'),
                        'worker': worker,
                        'eta': task.get('eta'),
                        'priority': task.get('priority')
                    })
        
        return {
            'scheduled_jobs': scheduled_jobs,
            'total_scheduled': len(scheduled_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo trabajos programados: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo trabajos programados: {str(e)}"
        )


@router.get("/jobs/status/{task_id}", response_model=Dict[str, Any])
async def get_job_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obtener estado de un trabajo específico"""
    
    try:
        # Verificar permisos
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ver estado de trabajos"
            )
        
        # Obtener resultado de la tarea
        task_result = celery_app.AsyncResult(task_id)
        
        result = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result,
            'traceback': task_result.traceback,
            'date_done': task_result.date_done.isoformat() if task_result.date_done else None
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del trabajo {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estado del trabajo: {str(e)}"
        )


@router.delete("/jobs/{task_id}", response_model=GenericResponse)
async def cancel_job(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancelar un trabajo específico"""
    
    try:
        # Verificar permisos
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden cancelar trabajos"
            )
        
        # Cancelar tarea
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info(f"Trabajo {task_id} cancelado por usuario {current_user.username}")
        
        return GenericResponse(
            message=f"Trabajo {task_id} cancelado exitosamente"
        )
        
    except Exception as e:
        logger.error(f"Error cancelando trabajo {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelando trabajo: {str(e)}"
        )


# ==================================================================
# TAREAS DE PRODUCTOS
# ==================================================================

@router.post("/products/cleanup-cache", response_model=Dict[str, Any])
async def trigger_cleanup_cache(
    current_user: User = Depends(get_current_user)
):
    """Ejecutar limpieza de caché"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ejecutar tareas de limpieza"
            )
        
        task = cleanup_cache_task.delay()
        
        logger.info(f"Tarea de limpieza de caché iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de limpieza de caché iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando limpieza de caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando limpieza de caché: {str(e)}"
        )


@router.post("/products/optimize-database", response_model=Dict[str, Any])
async def trigger_optimize_database(
    current_user: User = Depends(get_current_user)
):
    """Ejecutar optimización de base de datos"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ejecutar optimización de base de datos"
            )
        
        task = optimize_database_task.delay()
        
        logger.info(f"Tarea de optimización de base de datos iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de optimización de base de datos iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando optimización de base de datos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando optimización de base de datos: {str(e)}"
        )


@router.post("/products/warm-up-cache", response_model=Dict[str, Any])
async def trigger_warm_up_cache(
    product_ids: Optional[List[int]] = None,
    current_user: User = Depends(get_current_user)
):
    """Ejecutar pre-carga de caché"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden ejecutar pre-carga de caché"
            )
        
        task = warm_up_cache_task.delay(product_ids)
        
        logger.info(f"Tarea de pre-carga de caché iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de pre-carga de caché iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando pre-carga de caché: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando pre-carga de caché: {str(e)}"
        )


# ==================================================================
# TAREAS DE INVENTARIO
# ==================================================================

@router.post("/inventory/check-low-stock", response_model=Dict[str, Any])
async def trigger_check_low_stock(
    threshold: int = 5,
    current_user: User = Depends(get_current_user)
):
    """Ejecutar verificación de stock bajo"""
    
    try:
        if current_user.role not in ["admin", "manager", "employee"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes para ejecutar verificación de stock"
            )
        
        task = check_low_stock_task.delay(threshold)
        
        logger.info(f"Tarea de verificación de stock bajo iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de verificación de stock bajo iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando verificación de stock bajo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando verificación de stock bajo: {str(e)}"
        )


@router.post("/inventory/reconcile", response_model=Dict[str, Any])
async def trigger_reconcile_inventory(
    location: str = "main_warehouse",
    current_user: User = Depends(get_current_user)
):
    """Ejecutar reconciliación de inventario"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden ejecutar reconciliación de inventario"
            )
        
        task = reconcile_inventory_task.delay(location)
        
        logger.info(f"Tarea de reconciliación de inventario iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de reconciliación de inventario iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando reconciliación de inventario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando reconciliación de inventario: {str(e)}"
        )


@router.post("/inventory/check-overdue-consignments", response_model=Dict[str, Any])
async def trigger_check_overdue_consignments(
    current_user: User = Depends(get_current_user)
):
    """Ejecutar verificación de consignaciones vencidas"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden verificar consignaciones vencidas"
            )
        
        task = check_overdue_consignments_task.delay()
        
        logger.info(f"Tarea de verificación de consignaciones vencidas iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de verificación de consignaciones vencidas iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando verificación de consignaciones vencidas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando verificación de consignaciones vencidas: {str(e)}"
        )


# ==================================================================
# TAREAS DE REPORTES
# ==================================================================

@router.post("/reports/daily-inventory", response_model=Dict[str, Any])
async def trigger_daily_inventory_report(
    report_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Ejecutar generación de reporte diario de inventario"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden generar reportes de inventario"
            )
        
        task = generate_daily_inventory_report.delay(report_date)
        
        logger.info(f"Tarea de reporte diario de inventario iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de reporte diario de inventario iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando reporte diario de inventario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando reporte diario de inventario: {str(e)}"
        )


@router.post("/reports/sales", response_model=Dict[str, Any])
async def trigger_sales_report(
    start_date: str,
    end_date: str,
    group_by: str = "day",
    current_user: User = Depends(get_current_user)
):
    """Ejecutar generación de reporte de ventas"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden generar reportes de ventas"
            )
        
        # Validar group_by
        if group_by not in ["day", "week", "month"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_by debe ser 'day', 'week' o 'month'"
            )
        
        task = generate_sales_report.delay(start_date, end_date, group_by)
        
        logger.info(f"Tarea de reporte de ventas iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de reporte de ventas iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando reporte de ventas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando reporte de ventas: {str(e)}"
        )


# ==================================================================
# TAREAS DE AUDITORÍA
# ==================================================================

@router.post("/audit/cleanup-logs", response_model=Dict[str, Any])
async def trigger_cleanup_audit_logs(
    days_to_keep: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Ejecutar limpieza de logs de auditoría"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ejecutar limpieza de logs de auditoría"
            )
        
        task = cleanup_old_audit_logs_task.delay(days_to_keep)
        
        logger.info(f"Tarea de limpieza de logs de auditoría iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de limpieza de logs de auditoría iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando limpieza de logs de auditoría: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando limpieza de logs de auditoría: {str(e)}"
        )


@router.post("/audit/security-report", response_model=Dict[str, Any])
async def trigger_security_report(
    report_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Ejecutar generación de reporte de seguridad"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden generar reportes de seguridad"
            )
        
        task = generate_security_report_task.delay(report_date)
        
        logger.info(f"Tarea de reporte de seguridad iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de reporte de seguridad iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando reporte de seguridad: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando reporte de seguridad: {str(e)}"
        )


@router.post("/audit/system-health", response_model=Dict[str, Any])
async def trigger_system_health_analysis(
    current_user: User = Depends(get_current_user)
):
    """Ejecutar análisis de salud del sistema"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ejecutar análisis de salud del sistema"
            )
        
        task = analyze_system_health_task.delay()
        
        logger.info(f"Tarea de análisis de salud del sistema iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de análisis de salud del sistema iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando análisis de salud del sistema: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando análisis de salud del sistema: {str(e)}"
        )


# ==================================================================
# TAREAS DE MANTENIMIENTO
# ==================================================================

@router.post("/maintenance/backup", response_model=Dict[str, Any])
async def trigger_backup_critical_data(
    backup_type: str = "incremental",
    current_user: User = Depends(get_current_user)
):
    """Ejecutar respaldo de datos críticos"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ejecutar respaldos de datos"
            )
        
        # Validar backup_type
        if backup_type not in ["incremental", "full"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="backup_type debe ser 'incremental' o 'full'"
            )
        
        task = backup_critical_data_task.delay(backup_type)
        
        logger.info(f"Tarea de respaldo de datos críticos iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de respaldo de datos críticos iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando respaldo de datos críticos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando respaldo de datos críticos: {str(e)}"
        )


@router.post("/maintenance/send-daily-summary", response_model=Dict[str, Any])
async def trigger_daily_summary(
    current_user: User = Depends(get_current_user)
):
    """Ejecutar envío de resumen diario"""
    
    try:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores y gerentes pueden enviar resumen diario"
            )
        
        task = send_daily_summary_task.delay()
        
        logger.info(f"Tarea de envío de resumen diario iniciada por {current_user.username}")
        
        return {
            'task_id': task.id,
            'message': 'Tarea de envío de resumen diario iniciada exitosamente',
            'status': 'PENDING'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando envío de resumen diario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando envío de resumen diario: {str(e)}"
        )


# ==================================================================
# INFORMACIÓN DEL SISTEMA CELERY
# ==================================================================

@router.get("/stats", response_model=Dict[str, Any])
async def get_celery_stats(
    current_user: User = Depends(get_current_user)
):
    """Obtener estadísticas de Celery"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ver estadísticas de Celery"
            )
        
        # Obtener estadísticas
        stats = celery_app.control.inspect().stats()
        
        return {
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de Celery: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas de Celery: {str(e)}"
        )


@router.get("/workers", response_model=Dict[str, Any])
async def get_celery_workers(
    current_user: User = Depends(get_current_user)
):
    """Obtener información de workers de Celery"""
    
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden ver información de workers"
            )
        
        # Obtener workers registrados
        registered = celery_app.control.inspect().registered()
        
        # Obtener workers activos
        active = celery_app.control.inspect().active()
        
        return {
            'registered_workers': registered,
            'active_workers': active,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo información de workers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo información de workers: {str(e)}"
        )