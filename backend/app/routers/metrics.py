"""
Router para métricas y monitoreo
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from ..dependencies import get_current_user, get_current_distributor
from ..metrics import metrics_registry, business_metrics
from ..logging_config import get_logger
from ..models import User, Distributor

router = APIRouter(
    prefix="/admin/metrics",
    tags=["metrics"],
    responses={404: {"description": "Not found"}},
)

logger = get_logger(__name__)


@router.get("/")
async def get_all_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene todas las métricas del sistema
    """
    logger.audit(
        "metrics_access",
        user_id=current_user.id,
        action="get_all_metrics"
    )
    
    return {
        "metrics": metrics_registry.get_all_metrics(),
        "timestamp": metrics_registry.get_summary()
    }


@router.get("/summary")
async def get_metrics_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene resumen de métricas principales
    """
    logger.audit(
        "metrics_summary_access",
        user_id=current_user.id,
        action="get_metrics_summary"
    )
    
    return metrics_registry.get_summary()


@router.get("/business")
async def get_business_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene métricas específicas del negocio
    """
    logger.audit(
        "business_metrics_access",
        user_id=current_user.id,
        action="get_business_metrics"
    )
    
    # Obtener métricas de negocio del registry
    all_metrics = metrics_registry.get_all_metrics()
    
    # Filtrar solo métricas de negocio
    business_metrics_data = {
        key: value for key, value in all_metrics.items() 
        if key.startswith('business_')
    }
    
    return {
        "business_metrics": business_metrics_data,
        "summary": {
            "total_sales": business_metrics.sales_total.value,
            "total_products": business_metrics.total_products.value,
            "low_stock_products": business_metrics.low_stock_products.value,
            "total_inventory_value": business_metrics.total_inventory_value.value,
            "user_logins": business_metrics.user_logins.value,
            "distributor_logins": business_metrics.distributor_logins.value,
        }
    }


@router.post("/business/sale")
async def record_business_sale(
    sale_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Registra una venta en las métricas de negocio
    """
    try:
        amount = float(sale_data.get("amount", 0))
        item_count = int(sale_data.get("item_count", 0))
        
        business_metrics.record_sale(
            amount=amount,
            item_count=item_count,
            user_id=current_user.id
        )
        
        logger.business(
            "sale_recorded",
            sale_amount=amount,
            item_count=item_count,
            user_id=current_user.id
        )
        
        return {"message": "Venta registrada en métricas"}
        
    except Exception as e:
        logger.error(
            "Error recording business sale",
            error=e,
            user_id=current_user.id,
            sale_data=sale_data
        )
        raise HTTPException(status_code=400, detail="Error al registrar venta")


@router.post("/business/product")
async def record_business_product_action(
    action_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Registra acciones de productos en las métricas de negocio
    """
    try:
        action = action_data.get("action", "")
        
        if action == "created":
            business_metrics.record_product_created(user_id=current_user.id)
        elif action == "updated":
            business_metrics.record_product_updated(user_id=current_user.id)
        else:
            raise HTTPException(status_code=400, detail="Acción no válida")
        
        logger.business(
            f"product_{action}",
            user_id=current_user.id,
            product_action=action
        )
        
        return {"message": f"Acción de producto '{action}' registrada"}
        
    except Exception as e:
        logger.error(
            "Error recording product action",
            error=e,
            user_id=current_user.id,
            action_data=action_data
        )
        raise HTTPException(status_code=400, detail="Error al registrar acción")


@router.post("/business/inventory")
async def update_inventory_metrics(
    inventory_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza métricas de inventario
    """
    try:
        total_products = int(inventory_data.get("total_products", 0))
        low_stock_count = int(inventory_data.get("low_stock_count", 0))
        total_value = float(inventory_data.get("total_value", 0))
        
        business_metrics.update_inventory_metrics(
            total_products=total_products,
            low_stock_count=low_stock_count,
            total_value=total_value
        )
        
        logger.business(
            "inventory_metrics_updated",
            total_products=total_products,
            low_stock_count=low_stock_count,
            total_value=total_value,
            user_id=current_user.id
        )
        
        return {"message": "Métricas de inventario actualizadas"}
        
    except Exception as e:
        logger.error(
            "Error updating inventory metrics",
            error=e,
            user_id=current_user.id,
            inventory_data=inventory_data
        )
        raise HTTPException(status_code=400, detail="Error al actualizar métricas")


@router.get("/system/health")
async def get_system_health():
    """
    Obtiene estado de salud del sistema (endpoint público)
    """
    summary = metrics_registry.get_summary()
    
    # Determinar estado de salud basado en métricas
    health_status = "healthy"
    
    # Verificar tasa de errores
    error_rate = summary.get("requests", {}).get("error_rate", 0)
    if error_rate > 10:  # Más del 10% de errores
        health_status = "degraded"
    if error_rate > 25:  # Más del 25% de errores
        health_status = "unhealthy"
    
    # Verificar duración promedio de requests
    avg_duration = summary.get("requests", {}).get("avg_duration_ms", 0)
    if avg_duration > 2000:  # Más de 2 segundos
        health_status = "degraded"
    if avg_duration > 5000:  # Más de 5 segundos
        health_status = "unhealthy"
    
    return {
        "status": health_status,
        "timestamp": metrics_registry.get_summary(),
        "checks": {
            "error_rate": {
                "status": "ok" if error_rate < 10 else "warning" if error_rate < 25 else "error",
                "value": error_rate,
                "threshold": 10
            },
            "avg_response_time": {
                "status": "ok" if avg_duration < 2000 else "warning" if avg_duration < 5000 else "error",
                "value": avg_duration,
                "threshold": 2000
            },
            "cache_hit_rate": {
                "status": "ok" if summary.get("cache", {}).get("hit_rate", 0) > 50 else "warning",
                "value": summary.get("cache", {}).get("hit_rate", 0),
                "threshold": 50
            }
        }
    }


@router.delete("/reset")
async def reset_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Reinicia todas las métricas (solo para desarrollo)
    """
    logger.audit(
        "metrics_reset",
        user_id=current_user.id,
        action="reset_all_metrics"
    )
    
    # Reiniciar contadores
    for counter in metrics_registry._counters.values():
        counter.reset()
    
    # Reiniciar gauges
    for gauge in metrics_registry._gauges.values():
        gauge.set(0)
    
    # Limpiar histogramas
    for histogram in metrics_registry._histograms.values():
        histogram.values.clear()
    
    return {"message": "Métricas reiniciadas"}