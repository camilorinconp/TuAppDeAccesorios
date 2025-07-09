"""
Excepciones personalizadas para la aplicación
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(Exception):
    """Excepción base de la aplicación"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Error de validación de datos"""
    pass


class NotFoundError(AppException):
    """Recurso no encontrado"""
    pass


class DuplicateError(AppException):
    """Recurso duplicado"""
    pass


class InsufficientStockError(AppException):
    """Stock insuficiente para la operación"""
    pass


class BusinessLogicError(AppException):
    """Error de lógica de negocio"""
    pass


class AuthenticationError(AppException):
    """Error de autenticación"""
    pass


class AuthorizationError(AppException):
    """Error de autorización"""
    pass


class ConsignmentError(BusinessLogicError):
    """Error específico de operaciones de consignación"""
    pass


# Conversión de excepciones a HTTPException
def convert_to_http_exception(exc: AppException) -> HTTPException:
    """Convierte excepciones de la aplicación a HTTPException de FastAPI"""
    
    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": exc.message,
                "type": "validation_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": exc.message,
                "type": "not_found_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, DuplicateError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": exc.message,
                "type": "duplicate_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, InsufficientStockError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "type": "insufficient_stock_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, BusinessLogicError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "type": "business_logic_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": exc.message,
                "type": "authentication_error",
                "details": exc.details
            }
        )
    
    elif isinstance(exc, AuthorizationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": exc.message,
                "type": "authorization_error",
                "details": exc.details
            }
        )
    
    else:
        # Error genérico
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error interno del servidor",
                "type": "internal_server_error",
                "details": {}
            }
        )


# Modelos de respuesta de error
class ErrorResponse:
    def __init__(self, message: str, error_type: str, details: Dict[str, Any] = None):
        self.message = message
        self.type = error_type
        self.details = details or {}
    
    def to_dict(self):
        return {
            "message": self.message,
            "type": self.type,
            "details": self.details
        }