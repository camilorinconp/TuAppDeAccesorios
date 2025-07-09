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
        r"(['\"];?\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT))",
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
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?[1-9]\d{1,14}$',
        'name': r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-\'\.]+$'
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
    def validate_and_sanitize(cls, text: str, field_type: str = 'general', max_length: int = 255) -> str:
        """Validar y sanitizar input completo"""
        if not text:
            return ""
            
        # Validar longitud
        if len(text) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El texto excede la longitud máxima de {max_length} caracteres"
            )
        
        # Validar SQL injection
        if not cls.validate_sql_injection(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El texto contiene patrones de SQL injection no permitidos"
            )
        
        # Validar XSS
        if not cls.validate_xss(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El texto contiene patrones de XSS no permitidos"
            )
        
        # Sanitizar y retornar
        return cls.sanitize_input(text, field_type)


def validate_search_term(search_term: str, max_length: int = 100) -> str:
    """Validar término de búsqueda"""
    if not search_term:
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
    
    return search_term


def validate_email(email: str) -> str:
    """Validar formato de email"""
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email no puede estar vacío"
        )
    
    # Normalizar
    email = email.strip().lower()
    
    # Validar formato
    if not InputValidator.validate_format(email, 'email'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de email inválido"
        )
    
    return email


def validate_phone(phone: str) -> str:
    """Validar formato de teléfono"""
    if not phone:
        return ""
    
    # Limpiar teléfono
    phone = re.sub(r'[^\d+]', '', phone.strip())
    
    # Validar formato
    if not InputValidator.validate_format(phone, 'phone'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de teléfono inválido"
        )
    
    return phone