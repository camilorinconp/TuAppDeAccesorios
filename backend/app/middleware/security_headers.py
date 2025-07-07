"""
Middleware de headers de seguridad para protección avanzada
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from typing import Dict, Any
import secrets
import re

from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que añade headers de seguridad avanzados"""
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        self.nonce_cache = {}  # Cache de nonces para CSP
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generar nonce único para CSP
        nonce = self._generate_nonce()
        request.state.csp_nonce = nonce
        
        # Procesar request
        response = await call_next(request)
        
        # Agregar headers de seguridad
        self._add_security_headers(response, nonce, request)
        
        # Log de headers de seguridad (solo en debug)
        if settings.environment.lower() == "development":
            logger.debug(f"Security headers applied to {request.url.path}")
        
        return response
    
    def _generate_nonce(self) -> str:
        """Generar nonce criptográficamente seguro para CSP"""
        return secrets.token_urlsafe(16)
    
    def _add_security_headers(self, response: Response, nonce: str, request: Request):
        """Agregar todos los headers de seguridad"""
        
        # Strict Transport Security (HSTS)
        if settings.force_https or settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy (CSP) - Muy restrictivo
        csp_policy = self._build_csp_policy(nonce, request)
        response.headers["Content-Security-Policy"] = csp_policy
        
        # X-Frame-Options - Prevenir clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options - Prevenir MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection (legacy pero útil)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy - Controlar información de referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (Feature Policy)
        permissions_policy = self._build_permissions_policy()
        response.headers["Permissions-Policy"] = permissions_policy
        
        # Cross-Origin-Embedder-Policy
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # Cross-Origin-Opener-Policy
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Cross-Origin-Resource-Policy
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Server header - Ocultar información del servidor
        response.headers["Server"] = "TuApp/1.0"
        
        # X-Powered-By - Remover si existe
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        # Cache Control para endpoints sensibles
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Headers específicos para APIs
        if request.url.path.startswith("/api/") or request.url.path.startswith("/docs"):
            response.headers["X-API-Version"] = "1.0"
            response.headers["X-Rate-Limit-Policy"] = "enforced"
    
    def _build_csp_policy(self, nonce: str, request: Request) -> str:
        """Construir política CSP muy restrictiva"""
        
        # Base policy muy restrictiva
        base_policy = {
            "default-src": ["'none'"],
            "script-src": [f"'nonce-{nonce}'", "'strict-dynamic'"],
            "style-src": [f"'nonce-{nonce}'", "'unsafe-inline'"],  # unsafe-inline solo para fallback
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "connect-src": ["'self'"],
            "media-src": ["'self'"],
            "object-src": ["'none'"],
            "child-src": ["'none'"],
            "frame-src": ["'none'"],
            "worker-src": ["'none'"],
            "manifest-src": ["'self'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": []
        }
        
        # Ajustes para desarrollo
        if settings.environment.lower() == "development":
            # Permitir localhost para desarrollo
            base_policy["connect-src"].extend([
                "http://localhost:*",
                "ws://localhost:*",
                "wss://localhost:*"
            ])
            base_policy["script-src"].append("'unsafe-eval'")  # Solo para desarrollo
        
        # Ajustes para documentación (Swagger/OpenAPI)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            base_policy["script-src"].extend(["'unsafe-inline'", "'unsafe-eval'"])
            base_policy["style-src"].append("'unsafe-inline'")
            base_policy["img-src"].append("data:")
        
        # Construir string de política
        policy_parts = []
        for directive, sources in base_policy.items():
            if sources:
                policy_parts.append(f"{directive} {' '.join(sources)}")
            else:
                policy_parts.append(directive)
        
        return "; ".join(policy_parts)
    
    def _build_permissions_policy(self) -> str:
        """Construir Permissions Policy restrictiva"""
        permissions = {
            "camera": "self",
            "microphone": "self", 
            "geolocation": "self",
            "payment": "self",
            "usb": "none",
            "bluetooth": "none",
            "accelerometer": "none",
            "gyroscope": "none",
            "magnetometer": "none",
            "ambient-light-sensor": "none",
            "autoplay": "none",
            "encrypted-media": "self",
            "fullscreen": "self",
            "picture-in-picture": "none",
            "display-capture": "none",
            "web-share": "self"
        }
        
        policy_parts = []
        for feature, allowlist in permissions.items():
            if allowlist == "none":
                policy_parts.append(f"{feature}=()")
            elif allowlist == "self":
                policy_parts.append(f"{feature}=(self)")
            else:
                policy_parts.append(f"{feature}=({allowlist})")
        
        return ", ".join(policy_parts)
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Determinar si un endpoint es sensible y requiere headers especiales"""
        sensitive_patterns = [
            r'/token',
            r'/login',
            r'/logout', 
            r'/refresh',
            r'/password',
            r'/admin',
            r'/users',
            r'/auth',
            r'/api/users',
            r'/api/auth'
        ]
        
        return any(re.search(pattern, path, re.IGNORECASE) for pattern in sensitive_patterns)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware para redireccionar HTTP a HTTPS en producción"""
    
    async def dispatch(self, request: Request, call_next):
        # Solo redireccionar en producción
        if settings.force_https and settings.is_production:
            if request.url.scheme != "https":
                # Construir URL HTTPS
                https_url = request.url.replace(scheme="https")
                
                # Log del redirect por seguridad
                logger.warning(
                    f"HTTP to HTTPS redirect",
                    original_url=str(request.url),
                    redirect_url=str(https_url),
                    client_ip=request.client.host
                )
                
                return StarletteResponse(
                    status_code=301,  # Permanent redirect
                    headers={"Location": str(https_url)}
                )
        
        return await call_next(request)


class SecurityValidationMiddleware(BaseHTTPMiddleware):
    """Middleware para validaciones adicionales de seguridad"""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'<iframe[^>]*>',
            r'data:text/html'
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Validar tamaño de request
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                f"Request size too large",
                content_length=content_length,
                max_allowed=self.max_request_size,
                client_ip=request.client.host
            )
            return StarletteResponse(
                status_code=413,  # Payload too large
                content="Request size too large"
            )
        
        # Validar User-Agent
        user_agent = request.headers.get("user-agent", "")
        if self._is_suspicious_user_agent(user_agent):
            logger.warning(
                f"Suspicious user agent detected",
                user_agent=user_agent,
                client_ip=request.client.host,
                path=request.url.path
            )
            # No bloquear pero registrar
        
        # Validar URL por patrones sospechosos
        if self._contains_suspicious_patterns(str(request.url)):
            logger.warning(
                f"Suspicious URL pattern detected",
                url=str(request.url),
                client_ip=request.client.host
            )
            return StarletteResponse(
                status_code=400,
                content="Invalid request"
            )
        
        return await call_next(request)
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Detectar User-Agents sospechosos"""
        suspicious_agents = [
            "sqlmap",
            "nikto", 
            "nmap",
            "masscan",
            "gobuster",
            "dirb",
            "curl/7.0",  # Versión muy antigua
            "python-requests/0",  # Sin versión
            "bot",
            "crawler",
            "scanner"
        ]
        
        user_agent_lower = user_agent.lower()
        return any(suspicious in user_agent_lower for suspicious in suspicious_agents)
    
    def _contains_suspicious_patterns(self, url: str) -> bool:
        """Detectar patrones sospechosos en URL"""
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in self.suspicious_patterns)


# Función helper para agregar header personalizado
def add_custom_security_header(response: Response, name: str, value: str):
    """Agregar header de seguridad personalizado"""
    response.headers[name] = value