"""
Endpoints adicionales de seguridad para autenticación
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from ..database import get_db
from ..auth import get_current_user, get_token_from_request
from ..security.token_blacklist import token_blacklist
from ..logging_config import get_secure_logger
from .. import models, schemas

router = APIRouter(prefix="/auth", tags=["Authentication Security"])
logger = get_secure_logger(__name__)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Logout seguro con revocación de token"""
    try:
        token = get_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No token provided"
            )
        
        # Obtener usuario actual para el token
        try:
            current_user = await get_current_user(request, db)
            user_id = current_user.id
        except HTTPException:
            # Si no puede obtener usuario, usar ID genérico
            user_id = -1
        
        # Agregar token a blacklist
        success = token_blacklist.add_token(token, user_id, "logout")
        
        if success:
            # Limpiar cookies
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            
            logger.info(f"User logged out securely", user_id=user_id)
            
            return {"message": "Logged out successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error during logout"
            )
            
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )


@router.post("/revoke-all-sessions")
async def revoke_all_sessions(
    request: Request,
    db: Session = Depends(get_db)
):
    """Revocar todas las sesiones activas del usuario"""
    current_user = await get_current_user(request, db)
    
    try:
        revoked_count = token_blacklist.revoke_all_user_tokens(
            current_user.id, 
            "user_requested"
        )
        
        logger.info(
            f"User revoked all sessions",
            user_id=current_user.id,
            revoked_count=revoked_count
        )
        
        return {
            "message": f"Revoked {revoked_count} active sessions",
            "revoked_sessions": revoked_count
        }
        
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error revoking sessions"
        )


@router.get("/active-sessions")
async def get_active_sessions(
    request: Request,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Obtener sesiones activas del usuario"""
    current_user = await get_current_user(request, db)
    
    try:
        sessions = token_blacklist.get_user_sessions(current_user.id)
        
        # Sanitizar información sensible
        safe_sessions = []
        for session in sessions:
            safe_session = {
                "session_id": session.get("jti", "unknown"),
                "created_at": session.get("created_at"),
                "last_activity": session.get("last_activity"),
                "device_info": {
                    "user_agent": session.get("device_info", {}).get("user_agent", "Unknown"),
                    "ip_address": session.get("device_info", {}).get("ip_address", "Unknown")
                }
            }
            safe_sessions.append(safe_session)
        
        return safe_sessions
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sessions"
        )


@router.post("/revoke-session")
async def revoke_specific_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Revocar una sesión específica por ID"""
    current_user = await get_current_user(request, db)
    
    try:
        # Obtener sesiones del usuario
        sessions = token_blacklist.get_user_sessions(current_user.id)
        
        # Buscar la sesión específica
        target_session = None
        for session in sessions:
            if session.get("jti") == session_id:
                target_session = session
                break
        
        if not target_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Revocar el token específico
        token = target_session.get("token")
        if token:
            success = token_blacklist.add_token(
                token, 
                current_user.id, 
                "user_revoked_session"
            )
            
            if success:
                logger.info(
                    f"User revoked specific session",
                    user_id=current_user.id,
                    session_id=session_id
                )
                
                return {"message": "Session revoked successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error revoking session"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking specific session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error revoking session"
        )


@router.get("/security-info")
async def get_security_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """Información de seguridad del usuario actual"""
    current_user = await get_current_user(request, db)
    
    try:
        # Estadísticas de seguridad
        sessions = token_blacklist.get_user_sessions(current_user.id)
        blacklist_stats = token_blacklist.get_blacklist_stats()
        
        security_info = {
            "user_id": current_user.id,
            "active_sessions": len(sessions),
            "account_created": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None,
            "last_login": sessions[0].get("created_at") if sessions else None,
            "security_features": {
                "token_blacklist_enabled": True,
                "session_tracking_enabled": True,
                "secure_cookies": True,
                "jwt_with_jti": True
            },
            "system_stats": {
                "total_blacklisted_tokens": blacklist_stats.get("blacklisted_tokens", 0),
                "total_active_sessions": blacklist_stats.get("active_user_sessions", 0)
            }
        }
        
        return security_info
        
    except Exception as e:
        logger.error(f"Error getting security info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving security information"
        )


@router.post("/emergency-lockout")
async def emergency_lockout(
    request: Request,
    db: Session = Depends(get_db)
):
    """Bloqueo de emergencia - revocar todas las sesiones inmediatamente"""
    current_user = await get_current_user(request, db)
    
    try:
        # Revocar todas las sesiones
        revoked_count = token_blacklist.revoke_all_user_tokens(
            current_user.id, 
            "emergency_lockout"
        )
        
        # Log de seguridad crítico
        logger.critical(
            f"EMERGENCY LOCKOUT ACTIVATED",
            user_id=current_user.id,
            revoked_sessions=revoked_count,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "Unknown")
        )
        
        return {
            "message": "Emergency lockout activated - all sessions revoked",
            "revoked_sessions": revoked_count,
            "status": "locked_out"
        }
        
    except Exception as e:
        logger.error(f"Error during emergency lockout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during emergency lockout"
        )