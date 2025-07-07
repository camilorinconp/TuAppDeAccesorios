"""
Configuración de logging estructurado para la aplicación
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from pathlib import Path
from .security.log_sanitizer import SanitizedLogFilter, get_sanitized_logger

class StructuredFormatter(jsonlogger.JsonFormatter):
    """Formateador JSON personalizado para logging estructurado"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Agregar campos adicionales
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Agregar información del proceso
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread
        
        # Información de la aplicación
        log_record['application'] = 'tuapp-backend'
        log_record['environment'] = getattr(record, 'environment', 'development')

class RequestContextFilter(logging.Filter):
    """Filtro para agregar contexto de request a los logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Agregar información del request si está disponible
        # Esto se configurará en el middleware
        if not hasattr(record, 'request_id'):
            record.request_id = None
        if not hasattr(record, 'user_id'):
            record.user_id = None
        if not hasattr(record, 'endpoint'):
            record.endpoint = None
        if not hasattr(record, 'method'):
            record.method = None
        if not hasattr(record, 'client_ip'):
            record.client_ip = None
        if not hasattr(record, 'user_agent'):
            record.user_agent = None
        
        return True

def setup_logging(
    level: str = "INFO",
    environment: str = "development",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """
    Configura el sistema de logging de la aplicación
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Entorno de la aplicación
        log_file: Archivo de log (opcional)
        enable_console: Si habilitar logging en consola
    """
    
    # Configurar formato para logs estructurados
    json_format = "%(timestamp)s %(level)s %(logger)s %(module)s %(funcName)s %(lineno)d %(process)d %(thread)d %(application)s %(environment)s %(request_id)s %(user_id)s %(endpoint)s %(method)s %(client_ip)s %(user_agent)s %(message)s"
    
    # Crear formateadores
    json_formatter = StructuredFormatter(json_format)
    
    # Formato simple para consola en desarrollo
    console_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )
    console_formatter = logging.Formatter(console_format)
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Agregar filtro de contexto
    context_filter = RequestContextFilter()
    
    # Handler para consola
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if environment == "development":
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(json_formatter)
        console_handler.addFilter(context_filter)
        root_logger.addHandler(console_handler)
    
    # Handler para archivo
    if log_file:
        # Crear directorio si no existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)
    
    # Configurar loggers específicos
    configure_specific_loggers(level, environment)
    
    # Log de inicio
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging system initialized",
        extra={
            'level': level,
            'environment': environment,
            'log_file': log_file,
            'console_enabled': enable_console
        }
    )

def configure_specific_loggers(level: str, environment: str) -> None:
    """Configura loggers específicos para diferentes componentes"""
    
    # SQLAlchemy - solo errores en producción
    sqlalchemy_level = "WARNING" if environment == "production" else "INFO"
    logging.getLogger("sqlalchemy.engine").setLevel(getattr(logging, sqlalchemy_level))
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Redis - solo errores
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # HTTP clients
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # FastAPI/Uvicorn
    if environment == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Logger de la aplicación
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, level.upper()))

class AppLogger:
    """Clase utilitaria para logging de la aplicación"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"app.{name}")
    
    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        extra = kwargs.copy()
        if error:
            extra.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_details': getattr(error, 'details', None)
            })
        self.logger.error(message, extra=extra)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        extra = kwargs.copy()
        if error:
            extra.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_details': getattr(error, 'details', None)
            })
        self.logger.critical(message, extra=extra)
    
    def audit(self, action: str, user_id: Optional[int] = None, **kwargs) -> None:
        """Log de auditoría para acciones importantes"""
        extra = kwargs.copy()
        extra.update({
            'audit_action': action,
            'audit_user_id': user_id,
            'audit_timestamp': datetime.utcnow().isoformat()
        })
        self.logger.info(f"AUDIT: {action}", extra=extra)
    
    def performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log de métricas de performance"""
        extra = kwargs.copy()
        extra.update({
            'performance_operation': operation,
            'performance_duration_ms': duration * 1000,
            'performance_timestamp': datetime.utcnow().isoformat()
        })
        self.logger.info(f"PERFORMANCE: {operation} took {duration:.3f}s", extra=extra)

def get_logger(name: str) -> "AppLogger":
    """Factory para crear loggers de la aplicación"""
    return AppLogger(name)

def get_secure_logger(name: str, extra: Optional[Dict[str, Any]] = None):
    """Factory para crear loggers con sanitización automática de datos sensibles"""
    return get_sanitized_logger(f"app.{name}", extra)

# Decorador para logging automático de funciones
def log_function_call(logger: Optional[AppLogger] = None, level: str = "DEBUG"):
    """
    Decorador para logging automático de llamadas a funciones
    
    Args:
        logger: Logger a usar (si es None, se crea uno automáticamente)
        level: Nivel de logging
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Log de entrada
            getattr(logger, level.lower())(
                f"Calling {func_name}",
                extra={
                    'function_call': func_name,
                    'function_args_count': len(args),
                    'function_kwargs_count': len(kwargs)
                }
            )
            
            start_time = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                
                # Log de éxito
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.performance(func_name, duration)
                
                return result
                
            except Exception as e:
                # Log de error
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"Error in {func_name}",
                    error=e,
                    extra={
                        'function_call': func_name,
                        'function_duration': duration
                    }
                )
                raise
        
        return wrapper
    return decorator