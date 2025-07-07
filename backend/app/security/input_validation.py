"""
Validación de inputs para prevenir inyección SQL y XSS
"""
import re
from typing import Any, Optional
from fastapi import HTTPException, status
import bleach


class InputValidator:
    """Validador de inputs para prevenir inyecciones y ataques"""
    
    # Patrones peligrosos para SQL injection
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
        r"(\b(OR|AND)\s+['\"]?[0-9]+['\"]?\s*=\s*['\"]?[0-9]+['\"]?)",
        r"(['\"];\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT))",
        r"(\b(SLEEP|BENCHMARK|WAITFOR|DELAY)\s*\()",
        r"(\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b)",
        r"(\b(INFORMATION_SCHEMA|MYSQL|PERFORMANCE_SCHEMA|SYS)\b)",
        r"(['\"].*['\"].*['\"])",  # Múltiples quotes
        r"(--\s*$|#\s*$|/\*.*\*/)",  # Comentarios SQL
        r"(\b(XP_|SP_)\w+)",  # Procedimientos almacenados
        r"(\b(CAST|CONVERT|CHAR|ASCII|SUBSTRING|CONCAT)\s*\()",  # Funciones de manipulación
    ]
    
    # Patrones peligrosos para XSS
    XSS_PATTERNS = [
        r"(<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe\b[^>]*>)",
        r"(<object\b[^>]*>)",
        r"(<embed\b[^>]*>)",
        r"(<link\b[^>]*>)",
        r"(<meta\b[^>]*>)",
        r"(<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>)",
    ]
    
    # Caracteres permitidos por tipo de campo
    ALLOWED_CHARS = {
        'alphanumeric': r'^[a-zA-Z0-9\s\-_\.]+$',
        'name': r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\-_\.(),]+$',
        'email': r'^[a-zA-Z0-9\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}$',
        'numeric': r'^[0-9]+(\.[0-9]+)?$',
        'sku': r'^[a-zA-Z0-9\-_]+$',
        'description': r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\-_\.(),;:!?¡¿]+$',
    }
    
    @classmethod
    def validate_sql_injection(cls, text: str) -> bool:
        """Validar si el texto contiene patrones de SQL injection"""
        if not isinstance(text, str):
            return True
            
        text_upper = text.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return False
        return True
    
    @classmethod
    def validate_xss(cls, text: str) -> bool:
        """Validar si el texto contiene patrones de XSS"""
        if not isinstance(text, str):
            return True
            
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        return True
    
    @classmethod
    def validate_format(cls, text: str, field_type: str) -> bool:
        """Validar formato específico del campo"""
        if not isinstance(text, str):
            return False
            
        if field_type not in cls.ALLOWED_CHARS:
            return True  # Si no hay patrón específico, permitir
            
        pattern = cls.ALLOWED_CHARS[field_type]
        return bool(re.match(pattern, text))
    
    @classmethod
    def sanitize_input(cls, text: str, field_type: str = 'description') -> str:
        """Sanitizar input removiendo caracteres peligrosos"""
        if not isinstance(text, str):
            return str(text)
        
        # Usar bleach para sanitizar HTML/XSS
        if field_type == 'description':
            # Permitir algunos tags básicos para descripción
            allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
            allowed_attributes = {}
            clean_text = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)
        else:
            # Para otros campos, remover todos los tags
            clean_text = bleach.clean(text, tags=[], attributes={})
        
        # Normalizar espacios
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    @classmethod
    def validate_input(cls, text: str, field_type: str = 'description', max_length: int = 255) -> str:
        """Validación completa de input"""
        if not isinstance(text, str):
            text = str(text)
        
        # Verificar longitud
        if len(text) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El texto excede la longitud máxima de {max_length} caracteres"
            )
        
        # Validar SQL injection
        if not cls.validate_sql_injection(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El texto contiene patrones no permitidos"
            )
        
        # Validar XSS
        if not cls.validate_xss(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El texto contiene código potencialmente peligroso"
            )
        
        # Validar formato específico
        if not cls.validate_format(text, field_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El formato del campo {field_type} no es válido"
            )
        
        # Sanitizar y devolver
        return cls.sanitize_input(text, field_type)


# Decorador para validar inputs automáticamente
def validate_input_decorator(field_type: str = 'description', max_length: int = 255):
    """Decorador para validar inputs de funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validar argumentos que sean strings
            validated_args = []
            for arg in args:
                if isinstance(arg, str):
                    validated_args.append(InputValidator.validate_input(arg, field_type, max_length))
                else:
                    validated_args.append(arg)
            
            # Validar kwargs que sean strings
            validated_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    validated_kwargs[key] = InputValidator.validate_input(value, field_type, max_length)
                else:
                    validated_kwargs[key] = value
            
            return func(*validated_args, **validated_kwargs)
        return wrapper
    return decorator


# Función helper para validar query parameters
def validate_query_param(param: Optional[str], param_name: str, field_type: str = 'alphanumeric', max_length: int = 100) -> Optional[str]:
    """Validar parámetros de query de forma segura"""
    if param is None:
        return None
    
    try:
        return InputValidator.validate_input(param, field_type, max_length)
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parámetro '{param_name}' inválido: {e.detail}"
        )


# Función helper para validar búsquedas
def validate_search_term(search_term: str, max_length: int = 100) -> str:
    """Validar términos de búsqueda de forma segura"""
    if not search_term or not search_term.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El término de búsqueda no puede estar vacío"
        )
    
    # Normalizar
    search_term = search_term.strip()
    
    # Validar longitud
    if len(search_term) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El término de búsqueda excede la longitud máxima de {max_length} caracteres"
        )
    
    # Validar SQL injection
    if not InputValidator.validate_sql_injection(search_term):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El término de búsqueda contiene patrones no permitidos"
        )
    
    # Escape de caracteres especiales para LIKE
    escaped_term = search_term.replace('%', '\\%').replace('_', '\\_')
    
    return escaped_term