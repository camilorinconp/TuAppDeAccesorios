from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import logging

# Importar gestión de secretos
try:
    from .vault import get_vault_secret
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    def get_vault_secret(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(name, default)

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Base de datos
    database_url: str
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    
    # Seguridad JWT - usar Vault si está disponible
    secret_key: str = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Aplicación
    project_name: str = "TuAppDeAccesorios"
    environment: str = "development"  # development, staging, production
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_cache_enabled: bool = True
    redis_cache_default_ttl: int = 300  # 5 minutos por defecto
    
    # Vault
    vault_enabled: bool = False
    
    # CORS y seguridad - configuración dinámica basada en entorno
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"  # Producción: usar CORS_ORIGINS env var
    
    # Configuración específica para Render
    force_https: bool = False
    secure_cookies: bool = False
    
    # Rate limiting - configurado para desarrollo y producción
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hora en segundos
    
    
    # Configuración de auditoría
    audit_enabled: bool = True
    audit_retention_days: int = 365
    audit_log_sensitive_data: bool = False
    audit_async_logging: bool = True
    
    # Configuración de backups
    backup_enabled: bool = True
    backup_local_dir: str = "./backups"
    backup_retention_days: int = 30
    backup_encryption_key: str = "default-key-change-in-production"
    backup_s3_bucket: Optional[str] = None
    backup_schedule: str = "0 2 * * *"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def cookie_secure(self) -> bool:
        return self.secure_cookies or self.is_production or self.force_https
    
    @property
    def cookie_samesite(self) -> str:
        return "strict" if self.is_production else "lax"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.allowed_hosts.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Configuración dinámica de CORS origins con validaciones de seguridad"""
        
        # En producción, priorizar la variable de entorno CORS_ORIGINS
        if self.is_production:
            cors_env = os.getenv("CORS_ORIGINS")
            if cors_env:
                logger.info(f"Using CORS_ORIGINS from environment: {cors_env}")
                self.cors_origins = cors_env
            else:
                # Si no está definida, intentar usar la URL de Render como fallback
                render_url = os.getenv("RENDER_EXTERNAL_URL")
                if render_url:
                    logger.info(f"CORS_ORIGINS not set, using RENDER_EXTERNAL_URL as fallback: {render_url}")
                    self.cors_origins = render_url
                else:
                    logger.error("CORS_ORIGINS environment variable is not set in production.")
                    self.cors_origins = ""

        try:
            # Parsear origins - puede ser string JSON o separado por comas
            if self.cors_origins.startswith('[') and self.cors_origins.endswith(']'):
                import json
                origins = json.loads(self.cors_origins)
            else:
                origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error parsing CORS origins: {e}. Using fallback.")
            origins = ["http://localhost:3000", "http://localhost:3001"]

        # Validaciones de seguridad para producción
        if self.is_production:
            secure_origins = []
            render_url = os.getenv("RENDER_EXTERNAL_URL")
            
            for origin in origins:
                if not origin:
                    continue
                
                # Permitir HTTPS y la URL de Render
                if origin.startswith('https://') or (render_url and origin == render_url):
                    if all(c.isalnum() or c in ':/.-_' for c in origin):
                        secure_origins.append(origin)
                    else:
                        logger.warning(f"CORS origin contains unsafe characters: {origin}")
                else:
                    logger.warning(f"Insecure CORS origin removed in production: {origin}")
            
            if not secure_origins:
                logger.error("No valid HTTPS CORS origins found for production. Frontend requests will be blocked. Please set the CORS_ORIGINS environment variable.")
            
            return secure_origins
        
        # En desarrollo, ser más permisivo
        return origins or ["http://localhost:3000", "http://localhost:3001"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Priorizar REDIS_URL de Render si existe
        if redis_url_env := os.getenv("REDIS_URL"):
            self.redis_url = redis_url_env
            logger.info(f"Using Redis URL from environment: {self.redis_url}")

        # Obtener secretos sensibles desde Vault si está habilitado y disponible
        if self.vault_enabled and VAULT_AVAILABLE:
            logger.info("Vault is enabled, loading secrets from Vault")
            
            # SECRET_KEY desde Vault
            vault_secret_key = get_vault_secret('SECRET_KEY')
            if vault_secret_key:
                self.secret_key = vault_secret_key
            elif not self.secret_key:
                logger.warning("SECRET_KEY not found in Vault or environment variables")
            
            # Actualizar URL de base de datos con contraseña desde Vault
            vault_postgres_password = get_vault_secret('POSTGRES_PASSWORD')
            if vault_postgres_password and 'postgresql://' in self.database_url:
                db_parts = self.database_url.split('@')
                if len(db_parts) == 2:
                    user_pass = db_parts[0].split('://')[-1]
                    if ':' in user_pass:
                        user = user_pass.split(':')[0]
                        self.database_url = f"postgresql://{user}:{vault_postgres_password}@{db_parts[1]}"
            
            # Redis con contraseña desde Vault
            vault_redis_password = get_vault_secret('REDIS_PASSWORD')
            if vault_redis_password and not ':' in self.redis_url.split('://')[-1].split('@')[0]:
                redis_parts = self.redis_url.split('://')
                if len(redis_parts) == 2:
                    protocol = redis_parts[0]
                    host_port = redis_parts[1]
                    self.redis_url = f"{protocol}://:{vault_redis_password}@{host_port}"
        elif self.vault_enabled and not VAULT_AVAILABLE:
            logger.error("Vault is enabled in settings, but the vault module is not available.")
        else:
            logger.info("Vault is not enabled, using environment variables for secrets.")

    class Config:
        env_file = ".env"

settings = Settings()

# Inicializar el gestor de caché con la configuración
if settings.redis_cache_enabled:
    from .cache import cache_manager
    cache_manager.redis_url = settings.redis_url