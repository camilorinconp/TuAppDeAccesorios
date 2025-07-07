"""
Sistema de blacklist para tokens JWT revocados
Previene el uso de tokens robados o comprometidos
"""
import redis
import json
import logging
from typing import Optional, Set, Dict, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
from ..config import settings
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class TokenBlacklist:
    """Gestor de blacklist de tokens JWT usando Redis"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.prefix = "blacklist:"
        self.user_sessions_prefix = "user_sessions:"
        
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(settings.redis_url)
                self.redis_client.ping()
                logger.info("Token blacklist connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis for token blacklist: {e}")
                self.redis_client = None
    
    def add_token(self, token: str, user_id: int, reason: str = "logout") -> bool:
        """Agregar token a la blacklist"""
        if not self.redis_client:
            logger.warning("Redis not available for token blacklist")
            return False
        
        try:
            # Decodificar token para obtener información
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                exp_timestamp = payload.get('exp', 0)
                jti = payload.get('jti')  # JWT ID único
                
                if not jti:
                    logger.error("Token missing JTI (JWT ID)")
                    return False
                    
            except JWTError as e:
                logger.error(f"Invalid token for blacklist: {e}")
                return False
            
            # Calcular TTL basado en expiración del token
            current_time = datetime.utcnow().timestamp()
            ttl = max(0, int(exp_timestamp - current_time))
            
            if ttl <= 0:
                logger.info("Token already expired, not adding to blacklist")
                return True
            
            # Datos del token revocado
            token_data = {
                'user_id': user_id,
                'revoked_at': datetime.utcnow().isoformat(),
                'reason': reason,
                'jti': jti
            }
            
            # Agregar a blacklist con TTL
            blacklist_key = f"{self.prefix}{jti}"
            self.redis_client.setex(
                blacklist_key,
                ttl,
                json.dumps(token_data)
            )
            
            # Registrar en auditoría
            logger.info(
                f"Token blacklisted",
                user_id=user_id,
                reason=reason,
                jti=jti,
                ttl=ttl
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding token to blacklist: {e}")
            return False
    
    def is_blacklisted(self, token: str) -> bool:
        """Verificar si un token está en la blacklist"""
        if not self.redis_client:
            return False
        
        try:
            # Decodificar token para obtener JTI
            try:
                payload = jwt.decode(
                    token, 
                    settings.secret_key, 
                    algorithms=[settings.algorithm],
                    options={"verify_exp": False}  # No verificar expiración aquí
                )
                jti = payload.get('jti')
                
                if not jti:
                    logger.warning("Token missing JTI during blacklist check")
                    return False
                    
            except JWTError as e:
                logger.error(f"Invalid token during blacklist check: {e}")
                return True  # Token inválido = considerarlo blacklisted
            
            # Verificar en blacklist
            blacklist_key = f"{self.prefix}{jti}"
            return self.redis_client.exists(blacklist_key) > 0
            
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: int, reason: str = "security_incident") -> int:
        """Revocar todos los tokens activos de un usuario"""
        if not self.redis_client:
            return 0
        
        try:
            # Buscar todas las sesiones del usuario
            sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_tokens = self.redis_client.smembers(sessions_key)
            
            revoked_count = 0
            for token_data in session_tokens:
                try:
                    token_info = json.loads(token_data)
                    token = token_info.get('token')
                    if token and self.add_token(token, user_id, reason):
                        revoked_count += 1
                except json.JSONDecodeError:
                    continue
            
            # Limpiar sesiones del usuario
            self.redis_client.delete(sessions_key)
            
            logger.info(
                f"Revoked all user tokens",
                user_id=user_id,
                revoked_count=revoked_count,
                reason=reason
            )
            
            return revoked_count
            
        except Exception as e:
            logger.error(f"Error revoking all user tokens: {e}")
            return 0
    
    def track_user_session(self, token: str, user_id: int, device_info: Dict[str, Any]) -> bool:
        """Rastrear sesión activa de usuario"""
        if not self.redis_client:
            return False
        
        try:
            # Decodificar token para obtener información
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                exp_timestamp = payload.get('exp', 0)
                jti = payload.get('jti')
                
            except JWTError as e:
                logger.error(f"Invalid token for session tracking: {e}")
                return False
            
            # TTL basado en expiración del token
            current_time = datetime.utcnow().timestamp()
            ttl = max(0, int(exp_timestamp - current_time))
            
            if ttl <= 0:
                return False
            
            # Información de la sesión
            session_data = {
                'jti': jti,
                'token': token,
                'created_at': datetime.utcnow().isoformat(),
                'device_info': device_info,
                'last_activity': datetime.utcnow().isoformat()
            }
            
            # Agregar a sesiones del usuario
            sessions_key = f"{self.user_sessions_prefix}{user_id}"
            self.redis_client.sadd(sessions_key, json.dumps(session_data))
            self.redis_client.expire(sessions_key, ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking user session: {e}")
            return False
    
    def get_user_sessions(self, user_id: int) -> list:
        """Obtener sesiones activas de un usuario"""
        if not self.redis_client:
            return []
        
        try:
            sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_tokens = self.redis_client.smembers(sessions_key)
            
            sessions = []
            for token_data in session_tokens:
                try:
                    session_info = json.loads(token_data)
                    # Verificar si el token no está blacklisted
                    if not self.is_blacklisted(session_info.get('token', '')):
                        sessions.append(session_info)
                except json.JSONDecodeError:
                    continue
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    def cleanup_expired_tokens(self) -> int:
        """Limpiar tokens expirados de la blacklist (mantenimiento)"""
        if not self.redis_client:
            return 0
        
        try:
            # Redis maneja automáticamente la expiración con TTL
            # Esta función es para estadísticas
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)
            
            logger.info(f"Current blacklisted tokens: {len(keys)}")
            return len(keys)
            
        except Exception as e:
            logger.error(f"Error during blacklist cleanup: {e}")
            return 0
    
    def get_blacklist_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la blacklist"""
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            blacklist_pattern = f"{self.prefix}*"
            sessions_pattern = f"{self.user_sessions_prefix}*"
            
            blacklisted_count = len(self.redis_client.keys(blacklist_pattern))
            active_sessions = len(self.redis_client.keys(sessions_pattern))
            
            return {
                "blacklisted_tokens": blacklisted_count,
                "active_user_sessions": active_sessions,
                "redis_connected": True,
                "last_cleanup": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting blacklist stats: {e}")
            return {"error": str(e)}


# Instancia global del gestor de blacklist
token_blacklist = TokenBlacklist()


# Decorador para verificar blacklist automáticamente
def check_token_blacklist(func):
    """Decorador para verificar automáticamente si un token está blacklisted"""
    def wrapper(*args, **kwargs):
        # Buscar token en los argumentos
        token = None
        
        # Buscar en kwargs
        if 'token' in kwargs:
            token = kwargs['token']
        
        # Buscar en args (asumir que el primer string largo es el token)
        if not token:
            for arg in args:
                if isinstance(arg, str) and len(arg) > 50 and '.' in arg:
                    token = arg
                    break
        
        if token and token_blacklist.is_blacklisted(token):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        return func(*args, **kwargs)
    
    return wrapper


# Función helper para logout seguro
def secure_logout(token: str, user_id: int) -> bool:
    """Logout seguro agregando token a blacklist"""
    return token_blacklist.add_token(token, user_id, "logout")


# Función helper para revocar tokens comprometidos
def revoke_compromised_token(token: str, user_id: int) -> bool:
    """Revocar token comprometido"""
    return token_blacklist.add_token(token, user_id, "compromised")