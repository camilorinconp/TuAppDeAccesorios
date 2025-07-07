from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_db, get_current_admin_user
from ..cache import cache_manager, invalidate_products_cache
from ..config import settings

router = APIRouter(prefix="/admin/cache", tags=["cache-admin"])

@router.get("/stats")
async def get_cache_stats(
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Obtiene estadísticas del caché (solo para administradores)"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    stats = cache_manager.get_stats()
    return {
        "cache_enabled": True,
        "redis_url": settings.redis_url,
        "stats": stats
    }

@router.post("/invalidate/products")
async def invalidate_products_cache_endpoint(
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Invalida caché de productos"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        invalidate_products_cache()
        return {"message": "Cache de productos invalidado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@router.post("/invalidate/distributors")
async def invalidate_distributors_cache(
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Invalida caché de distribuidores"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        cache_manager.delete_pattern("cache:distributors:*")
        return {"message": "Cache de distribuidores invalidado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@router.post("/invalidate/all")
async def invalidate_all_cache(
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Invalida todo el caché (usar con precaución)"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        cache_manager.flush_all()
        return {"message": "Todo el caché ha sido invalidado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@router.get("/health")
async def cache_health_check() -> Dict[str, Any]:
    """Verifica el estado de salud del caché"""
    if not settings.redis_cache_enabled:
        return {
            "cache_enabled": False,
            "status": "disabled"
        }
    
    try:
        # Hacer una operación simple para verificar conectividad
        test_key = "health_check_test"
        cache_manager.set(test_key, "test", 10)
        result = cache_manager.get(test_key)
        cache_manager.delete(test_key)
        
        return {
            "cache_enabled": True,
            "status": "healthy" if result == "test" else "unhealthy",
            "redis_url": settings.redis_url
        }
    except Exception as e:
        return {
            "cache_enabled": True,
            "status": "error",
            "error": str(e)
        }

@router.get("/keys")
async def get_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Obtiene claves del caché que coincidan con un patrón"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        client = cache_manager.get_sync_client()
        keys = client.keys(pattern)
        
        # Limitar el número de claves retornadas
        limited_keys = keys[:limit] if len(keys) > limit else keys
        
        return {
            "pattern": pattern,
            "total_matches": len(keys),
            "returned_count": len(limited_keys),
            "keys": [key.decode('utf-8') if isinstance(key, bytes) else key for key in limited_keys]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache keys: {str(e)}")

@router.delete("/key/{key}")
async def delete_cache_key(
    key: str,
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Elimina una clave específica del caché"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        success = cache_manager.delete(key)
        if success:
            return {"message": f"Clave '{key}' eliminada exitosamente"}
        else:
            return {"message": f"Clave '{key}' no encontrada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cache key: {str(e)}")

@router.get("/key/{key}")
async def get_cache_key_value(
    key: str,
    current_user: models.User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Obtiene el valor de una clave específica del caché"""
    if not settings.redis_cache_enabled:
        raise HTTPException(status_code=503, detail="Cache not enabled")
    
    try:
        value = cache_manager.get(key)
        exists = cache_manager.exists(key)
        
        return {
            "key": key,
            "exists": exists,
            "value": value,
            "type": type(value).__name__ if value is not None else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache key value: {str(e)}")