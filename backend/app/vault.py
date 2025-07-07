"""
Sistema de gestión de secretos con HashiCorp Vault
Proporciona acceso seguro a credenciales y configuraciones sensibles
"""
import os
import hvac
import logging
from typing import Dict, Optional, Any
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VaultManager:
    """Gestor de secretos con HashiCorp Vault"""
    
    def __init__(self):
        self.client = None
        self.vault_url = os.getenv('VAULT_URL', 'http://localhost:8200')
        self.vault_token = os.getenv('VAULT_TOKEN')
        self.vault_role_id = os.getenv('VAULT_ROLE_ID')
        self.vault_secret_id = os.getenv('VAULT_SECRET_ID')
        self.mount_point = os.getenv('VAULT_MOUNT_POINT', 'secret')
        self.secret_path = os.getenv('VAULT_SECRET_PATH', 'tuapp/config')
        self._cache = {}
        self._cache_ttl = {}
        self._connected = False
        
    def _connect(self) -> bool:
        """Conectar a Vault con autenticación AppRole o Token"""
        try:
            if not self.client:
                self.client = hvac.Client(url=self.vault_url)
            
            # Verificar si Vault está sellado
            if self.client.sys.is_sealed():
                logger.error("Vault está sellado y no puede ser usado")
                return False
            
            # Autenticación con AppRole (recomendado para producción)
            if self.vault_role_id and self.vault_secret_id:
                try:
                    result = self.client.auth.approle.login(
                        role_id=self.vault_role_id,
                        secret_id=self.vault_secret_id
                    )
                    self.client.token = result['auth']['client_token']
                    logger.info("Autenticado en Vault con AppRole")
                    self._connected = True
                    return True
                except Exception as e:
                    logger.error(f"Error en autenticación AppRole: {e}")
            
            # Fallback a token directo (desarrollo)
            if self.vault_token:
                self.client.token = self.vault_token
                if self.client.is_authenticated():
                    logger.info("Autenticado en Vault con token directo")
                    self._connected = True
                    return True
            
            logger.error("No se pudo autenticar en Vault")
            return False
            
        except Exception as e:
            logger.error(f"Error conectando a Vault: {e}")
            return False
    
    def _is_cache_valid(self, key: str) -> bool:
        """Verificar si el cache para una clave sigue siendo válido"""
        if key not in self._cache_ttl:
            return False
        return datetime.now() < self._cache_ttl[key]
    
    @lru_cache(maxsize=32)
    def get_secret(self, secret_name: str, default: Optional[str] = None, cache_ttl: int = 300) -> Optional[str]:
        """
        Obtener un secreto de Vault con cache
        
        Args:
            secret_name: Nombre del secreto
            default: Valor por defecto si no se encuentra
            cache_ttl: Tiempo de vida del cache en segundos
        """
        cache_key = f"{self.secret_path}/{secret_name}"
        
        # Verificar cache
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        
        # Fallback a variable de entorno si Vault no está disponible
        env_value = os.getenv(secret_name.upper())
        if env_value and not self._connected:
            logger.warning(f"Usando variable de entorno para {secret_name} (Vault no disponible)")
            return env_value
        
        # Conectar a Vault si es necesario
        if not self._connected and not self._connect():
            logger.warning(f"Vault no disponible, usando valor por defecto para {secret_name}")
            return default
        
        try:
            # Leer secreto de Vault
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.secret_path,
                mount_point=self.mount_point
            )
            
            secrets_data = response['data']['data']
            value = secrets_data.get(secret_name, default)
            
            # Guardar en cache
            self._cache[cache_key] = value
            self._cache_ttl[cache_key] = datetime.now() + timedelta(seconds=cache_ttl)
            
            return value
            
        except Exception as e:
            logger.error(f"Error obteniendo secreto {secret_name} de Vault: {e}")
            # Fallback a variable de entorno
            env_value = os.getenv(secret_name.upper())
            if env_value:
                logger.warning(f"Usando variable de entorno para {secret_name}")
                return env_value
            return default
    
    def get_all_secrets(self) -> Dict[str, Any]:
        """Obtener todos los secretos del path configurado"""
        if not self._connected and not self._connect():
            logger.warning("Vault no disponible, retornando diccionario vacío")
            return {}
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.secret_path,
                mount_point=self.mount_point
            )
            return response['data']['data']
        except Exception as e:
            logger.error(f"Error obteniendo todos los secretos: {e}")
            return {}
    
    def set_secret(self, secret_name: str, value: str) -> bool:
        """
        Guardar un secreto en Vault
        
        Args:
            secret_name: Nombre del secreto
            value: Valor del secreto
        """
        if not self._connected and not self._connect():
            return False
        
        try:
            # Obtener secretos existentes
            current_secrets = self.get_all_secrets()
            
            # Agregar/actualizar el nuevo secreto
            current_secrets[secret_name] = value
            
            # Guardar todos los secretos
            self.client.secrets.kv.v2.create_or_update_secret(
                path=self.secret_path,
                secret=current_secrets,
                mount_point=self.mount_point
            )
            
            # Limpiar cache
            cache_key = f"{self.secret_path}/{secret_name}"
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            
            logger.info(f"Secreto {secret_name} guardado en Vault")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando secreto {secret_name}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Verificar el estado de salud de Vault"""
        try:
            if not self.client:
                self._connect()
            
            if not self.client:
                return {"status": "error", "message": "No se pudo conectar a Vault"}
            
            health = self.client.sys.read_health_status()
            return {
                "status": "healthy" if not health.get('sealed', True) else "sealed",
                "version": health.get('version', 'unknown'),
                "cluster_name": health.get('cluster_name', 'unknown'),
                "authenticated": self.client.is_authenticated() if self._connected else False
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Instancia global del gestor de secretos
vault_manager = VaultManager()


def get_vault_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Función helper para obtener secretos de Vault
    
    Args:
        secret_name: Nombre del secreto
        default: Valor por defecto
    """
    return vault_manager.get_secret(secret_name, default)


def init_vault_secrets() -> Dict[str, str]:
    """
    Inicializar secretos básicos en Vault para la aplicación
    Retorna un diccionario con los secretos generados
    """
    import secrets
    import string
    
    basic_secrets = {}
    
    # Generar SECRET_KEY si no existe
    secret_key = vault_manager.get_secret('SECRET_KEY')
    if not secret_key:
        secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
        vault_manager.set_secret('SECRET_KEY', secret_key)
        basic_secrets['SECRET_KEY'] = secret_key
    
    # Generar contraseña de PostgreSQL si no existe
    postgres_password = vault_manager.get_secret('POSTGRES_PASSWORD')
    if not postgres_password:
        postgres_password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(32))
        vault_manager.set_secret('POSTGRES_PASSWORD', postgres_password)
        basic_secrets['POSTGRES_PASSWORD'] = postgres_password
    
    # Generar contraseña de Redis si no existe
    redis_password = vault_manager.get_secret('REDIS_PASSWORD')
    if not redis_password:
        redis_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
        vault_manager.set_secret('REDIS_PASSWORD', redis_password)
        basic_secrets['REDIS_PASSWORD'] = redis_password
    
    return basic_secrets