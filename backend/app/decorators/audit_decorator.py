# ==================================================================
# DECORADORES DE AUDITORÍA - AUTOMATIZACIÓN DE LOGGING
# ==================================================================

from functools import wraps
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Depends
from sqlalchemy.orm import Session
import time
import json
import inspect

from ..models.audit import AuditActionType, AuditSeverity
from ..services.audit_service import AuditService
from ..dependencies import get_db
from ..logging_config import get_logger

logger = get_logger(__name__)


def audit_operation(
    action_type: AuditActionType,
    description: Optional[str] = None,
    table_name: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.LOW,
    capture_args: bool = False,
    capture_result: bool = False
):
    """
    Decorador para auditar operaciones automáticamente
    
    Args:
        action_type: Tipo de acción que se está auditando
        description: Descripción personalizada (si no se provee, se genera automáticamente)
        table_name: Nombre de la tabla afectada
        severity: Nivel de severidad del evento
        capture_args: Si capturar los argumentos de la función
        capture_result: Si capturar el resultado de la función
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _execute_with_audit(
                func, args, kwargs, action_type, description, 
                table_name, severity, capture_args, capture_result, True
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _execute_with_audit(
                func, args, kwargs, action_type, description,
                table_name, severity, capture_args, capture_result, False
            )
        
        # Determinar si la función es async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def _execute_with_audit(
    func: Callable, 
    args: tuple, 
    kwargs: dict,
    action_type: AuditActionType,
    description: Optional[str],
    table_name: Optional[str],
    severity: AuditSeverity,
    capture_args: bool,
    capture_result: bool,
    is_async: bool
):
    """Ejecuta la función con auditoría"""
    
    start_time = time.time()
    db = None
    request = None
    user_info = {}
    
    try:
        # Extraer información del contexto
        db, request, user_info = _extract_context_info(args, kwargs)
        
        # Ejecutar la función
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        # Calcular tiempo de ejecución
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar datos para auditoría
        audit_description = description or f"Ejecutada operación: {func.__name__}"
        additional_data = {}
        
        if capture_args:
            additional_data["function_args"] = _serialize_args(args, kwargs)
        
        if capture_result:
            additional_data["function_result"] = _serialize_result(result)
        
        # Registrar evento de auditoría
        if db:
            AuditService.log_event(
                db=db,
                action_type=action_type,
                description=audit_description,
                user_id=user_info.get("user_id"),
                username=user_info.get("username"),
                user_role=user_info.get("user_role"),
                table_name=table_name,
                severity=severity,
                request=request,
                execution_time_ms=execution_time_ms,
                additional_data=additional_data if additional_data else None
            )
        
        return result
        
    except Exception as e:
        # Calcular tiempo de ejecución incluso en error
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Registrar error en auditoría
        if db:
            try:
                AuditService.log_event(
                    db=db,
                    action_type=action_type,
                    description=f"ERROR en operación: {func.__name__} - {str(e)}",
                    user_id=user_info.get("user_id"),
                    username=user_info.get("username"),
                    user_role=user_info.get("user_role"),
                    table_name=table_name,
                    severity=AuditSeverity.HIGH,
                    request=request,
                    execution_time_ms=execution_time_ms,
                    additional_data={
                        "error": str(e),
                        "function_name": func.__name__,
                        "error_type": type(e).__name__
                    }
                )
            except Exception as audit_error:
                logger.error(
                    "Error al registrar auditoría de error",
                    original_error=str(e),
                    audit_error=str(audit_error),
                    function_name=func.__name__
                )
        
        # Re-lanzar la excepción original
        raise e


def _extract_context_info(args: tuple, kwargs: dict) -> tuple:
    """Extrae información del contexto de la función"""
    
    db = None
    request = None
    user_info = {}
    
    # Buscar Session de base de datos
    for arg in args:
        if isinstance(arg, Session):
            db = arg
            break
    
    if not db and "db" in kwargs:
        db = kwargs["db"]
    
    # Buscar Request
    for arg in args:
        if isinstance(arg, Request):
            request = arg
            break
    
    if not request and "request" in kwargs:
        request = kwargs["request"]
    
    # Extraer información del usuario del request o argumentos
    if request and hasattr(request.state, "current_user"):
        user = request.state.current_user
        user_info = {
            "user_id": getattr(user, "id", None),
            "username": getattr(user, "username", None),
            "user_role": getattr(user, "role", None)
        }
    
    # Buscar información de usuario en kwargs
    for key in ["user_id", "current_user", "user"]:
        if key in kwargs:
            if key == "user_id":
                user_info["user_id"] = kwargs[key]
            elif hasattr(kwargs[key], "id"):
                user_info.update({
                    "user_id": getattr(kwargs[key], "id", None),
                    "username": getattr(kwargs[key], "username", None),
                    "user_role": getattr(kwargs[key], "role", None)
                })
    
    return db, request, user_info


def _serialize_args(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Serializa argumentos de función para auditoría"""
    
    try:
        serialized = {
            "args_count": len(args),
            "kwargs": {}
        }
        
        # Serializar kwargs, excluyendo objetos sensibles
        for key, value in kwargs.items():
            if key in ["password", "hashed_password", "secret", "token"]:
                serialized["kwargs"][key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool, list, dict)):
                serialized["kwargs"][key] = value
            elif hasattr(value, "__dict__"):
                serialized["kwargs"][key] = f"<{type(value).__name__} object>"
            else:
                serialized["kwargs"][key] = str(type(value))
        
        return serialized
        
    except Exception as e:
        return {"serialization_error": str(e)}


def _serialize_result(result: Any) -> Any:
    """Serializa resultado de función para auditoría"""
    
    try:
        if isinstance(result, (str, int, float, bool, list, dict)):
            return result
        elif hasattr(result, "__dict__"):
            # Para objetos complejos, solo incluir información básica
            return {
                "type": type(result).__name__,
                "id": getattr(result, "id", None),
                "repr": str(result)[:200]  # Limitar longitud
            }
        else:
            return {"type": type(result).__name__}
            
    except Exception as e:
        return {"serialization_error": str(e)}


# Decoradores específicos para operaciones comunes
def audit_create(table_name: str, description: Optional[str] = None):
    """Decorador específico para operaciones CREATE"""
    return audit_operation(
        action_type=AuditActionType.CREATE,
        description=description,
        table_name=table_name,
        severity=AuditSeverity.LOW,
        capture_result=True
    )


def audit_update(table_name: str, description: Optional[str] = None):
    """Decorador específico para operaciones UPDATE"""
    return audit_operation(
        action_type=AuditActionType.UPDATE,
        description=description,
        table_name=table_name,
        severity=AuditSeverity.MEDIUM,
        capture_args=True,
        capture_result=True
    )


def audit_delete(table_name: str, description: Optional[str] = None):
    """Decorador específico para operaciones DELETE"""
    return audit_operation(
        action_type=AuditActionType.DELETE,
        description=description,
        table_name=table_name,
        severity=AuditSeverity.HIGH,
        capture_args=True
    )


def audit_search(description: Optional[str] = None):
    """Decorador específico para operaciones de búsqueda"""
    return audit_operation(
        action_type=AuditActionType.SEARCH,
        description=description,
        severity=AuditSeverity.LOW,
        capture_args=True
    )


def audit_sale(description: Optional[str] = None):
    """Decorador específico para operaciones de venta"""
    return audit_operation(
        action_type=AuditActionType.SALE,
        description=description,
        table_name="point_of_sale_transactions",
        severity=AuditSeverity.MEDIUM,
        capture_args=True,
        capture_result=True
    )