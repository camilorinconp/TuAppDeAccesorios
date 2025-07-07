"""
Sanitizador de logs para prevenir data leakage y exposición de información sensible
"""
import re
import logging
from typing import Any, Dict, List, Optional, Union


class LogSanitizer:
    """Sanitizador de logs para remover información sensible"""
    
    # Patrones de información sensible que no debe aparecer en logs
    SENSITIVE_PATTERNS = {
        'password': [
            r'password["\s]*[:=]["\s]*[^,}\s]+',
            r'pwd["\s]*[:=]["\s]*[^,}\s]+',
            r'passwd["\s]*[:=]["\s]*[^,}\s]+',
            r'secret["\s]*[:=]["\s]*[^,}\s]+',
            r'token["\s]*[:=]["\s]*[^,}\s]+',
            r'key["\s]*[:=]["\s]*[^,}\s]+',
        ],
        'email': [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        'phone': [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\+\d{1,3}[-.]?\d{1,4}[-.]?\d{1,4}[-.]?\d{1,9}\b',
        ],
        'credit_card': [
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            r'\b\d{13,19}\b',
        ],
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{9}\b',
        ],
        'ip_address': [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        ],
        'database_url': [
            r'postgresql://[^:]+:[^@]+@[^/]+/\w+',
            r'mysql://[^:]+:[^@]+@[^/]+/\w+',
            r'redis://[^:]*:[^@]*@[^/]+',
        ],
        'jwt_token': [
            r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
        ],
        'api_key': [
            r'sk-[a-zA-Z0-9]{32,}',
            r'pk-[a-zA-Z0-9]{32,}',
            r'api[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',
        ]
    }
    
    # Campos que siempre deben ser censurados
    SENSITIVE_FIELDS = [
        'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'private_key',
        'access_token', 'refresh_token', 'jwt', 'authorization', 'auth',
        'api_key', 'database_url', 'redis_url', 'connection_string',
        'credit_card', 'ssn', 'social_security_number'
    ]
    
    # Reemplazos para información sensible
    REDACTION_REPLACEMENTS = {
        'password': '[PASSWORD_REDACTED]',
        'email': '[EMAIL_REDACTED]',
        'phone': '[PHONE_REDACTED]',
        'credit_card': '[CARD_REDACTED]',
        'ssn': '[SSN_REDACTED]',
        'ip_address': '[IP_REDACTED]',
        'database_url': '[DB_URL_REDACTED]',
        'jwt_token': '[JWT_REDACTED]',
        'api_key': '[API_KEY_REDACTED]',
        'default': '[SENSITIVE_DATA_REDACTED]'
    }
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitizar texto removiendo información sensible"""
        if not isinstance(text, str):
            return str(text)
        
        sanitized = text
        
        # Aplicar cada patrón de sanitización
        for category, patterns in cls.SENSITIVE_PATTERNS.items():
            replacement = cls.REDACTION_REPLACEMENTS.get(category, cls.REDACTION_REPLACEMENTS['default'])
            for pattern in patterns:
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizar diccionario removiendo campos sensibles"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Verificar si la clave es sensible
            if any(sensitive_field in key_lower for sensitive_field in cls.SENSITIVE_FIELDS):
                sanitized[key] = cls.REDACTION_REPLACEMENTS['default']
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_text(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def sanitize_list(cls, data: List[Any]) -> List[Any]:
        """Sanitizar lista recursivamente"""
        if not isinstance(data, list):
            return data
        
        sanitized = []
        for item in data:
            if isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item))
            elif isinstance(item, str):
                sanitized.append(cls.sanitize_text(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    @classmethod
    def sanitize_log_record(cls, record: logging.LogRecord) -> logging.LogRecord:
        """Sanitizar un LogRecord completo"""
        # Sanitizar el mensaje principal
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = cls.sanitize_text(record.msg)
        
        # Sanitizar argumentos del mensaje
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(cls.sanitize_text(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(cls.sanitize_dict(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        # Sanitizar datos extra/contexto
        for attr_name in dir(record):
            if not attr_name.startswith('_') and attr_name not in ['msg', 'args', 'levelname', 'levelno', 'module', 'funcName', 'lineno', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process']:
                attr_value = getattr(record, attr_name)
                if isinstance(attr_value, str):
                    setattr(record, attr_name, cls.sanitize_text(attr_value))
                elif isinstance(attr_value, dict):
                    setattr(record, attr_name, cls.sanitize_dict(attr_value))
        
        return record


class SanitizedLogFilter(logging.Filter):
    """Filtro de logging que sanitiza automáticamente los logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filtrar y sanitizar el record antes de que sea procesado"""
        try:
            LogSanitizer.sanitize_log_record(record)
            return True
        except Exception as e:
            # En caso de error en la sanitización, permitir el log pero agregar warning
            print(f"Error sanitizing log record: {e}", file=sys.stderr)
            return True


class SanitizedLoggerAdapter(logging.LoggerAdapter):
    """Adapter que automáticamente sanitiza los logs"""
    
    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        """Procesar el mensaje y kwargs antes del logging"""
        # Sanitizar el mensaje
        if isinstance(msg, str):
            msg = LogSanitizer.sanitize_text(msg)
        elif isinstance(msg, dict):
            msg = LogSanitizer.sanitize_dict(msg)
        
        # Sanitizar extra data
        if 'extra' in kwargs and isinstance(kwargs['extra'], dict):
            kwargs['extra'] = LogSanitizer.sanitize_dict(kwargs['extra'])
        
        return msg, kwargs


# Función helper para crear logger sanitizado
def get_sanitized_logger(name: str, extra: Optional[Dict[str, Any]] = None) -> SanitizedLoggerAdapter:
    """Crear un logger que automáticamente sanitiza los logs"""
    logger = logging.getLogger(name)
    
    # Agregar filtro de sanitización si no existe
    if not any(isinstance(f, SanitizedLogFilter) for f in logger.filters):
        logger.addFilter(SanitizedLogFilter())
    
    return SanitizedLoggerAdapter(logger, extra or {})


# Función para sanitizar datos antes de logging manual
def sanitize_for_logging(data: Union[str, Dict[str, Any], List[Any]]) -> Union[str, Dict[str, Any], List[Any]]:
    """Función utility para sanitizar datos antes de hacer log manual"""
    if isinstance(data, str):
        return LogSanitizer.sanitize_text(data)
    elif isinstance(data, dict):
        return LogSanitizer.sanitize_dict(data)
    elif isinstance(data, list):
        return LogSanitizer.sanitize_list(data)
    else:
        return data


# Contexto de logging seguro
class SafeLogContext:
    """Context manager para logging seguro con datos sensibles"""
    
    def __init__(self, logger: logging.Logger, level: int = logging.INFO):
        self.logger = logger
        self.level = level
        self.original_filters = []
    
    def __enter__(self):
        # Guardar filtros originales
        self.original_filters = self.logger.filters.copy()
        
        # Agregar filtro de sanitización
        sanitize_filter = SanitizedLogFilter()
        self.logger.addFilter(sanitize_filter)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restaurar filtros originales
        self.logger.filters = self.original_filters
    
    def log(self, message: str, **kwargs):
        """Log con sanitización automática"""
        self.logger.log(self.level, message, **kwargs)