from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, schemas, auth, models
from ..dependencies import get_db
from ..config import settings
from ..metrics import business_metrics
from ..logging_config import get_logger
from ..services.audit_service import AuditService
from ..models.audit import AuditActionType, AuditSeverity

router = APIRouter()
logger = get_logger(__name__)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    # Intentar encontrar usuario
    user = None
    failure_reason = None
    
    try:
        user = crud.get_user_by_username(db, username=form_data.username)
        if not user:
            failure_reason = "Usuario no encontrado"
        elif not auth.security.verify_password(form_data.password, user.hashed_password):
            failure_reason = "Contraseña incorrecta"
    except Exception as e:
        failure_reason = f"Error en verificación: {str(e)}"
    
    # Registrar intento de login
    session_id = AuditService.generate_session_id()
    AuditService.log_login_attempt(
        db=db,
        username=form_data.username,
        success=user is not None and failure_reason is None,
        user_id=user.id if user else None,
        session_id=session_id,
        failure_reason=failure_reason,
        request=request
    )
    
    # Si falló el login, lanzar excepción
    if failure_reason:
        # Registrar alerta de seguridad para múltiples intentos
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}
    )
    
    # Configurar cookies seguras
    auth.set_auth_cookies(response, access_token, refresh_token)
    
    # Registrar evento de auditoría para login exitoso
    AuditService.log_event(
        db=db,
        action_type=AuditActionType.LOGIN,
        description=f"Login exitoso para usuario: {user.username}",
        user_id=user.id,
        username=user.username,
        user_role=user.role.value,
        session_id=session_id,
        severity=AuditSeverity.LOW,
        request=request
    )
    
    # Registrar métricas de login
    business_metrics.record_user_login(user_id=user.id, user_type="user")
    
    # Log de auditoría
    logger.business(
        "user_login",
        user_id=user.id,
        username=user.username,
        login_type="user",
        session_id=session_id
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/distributor-token", response_model=schemas.Token)
def login_for_distributor_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    distributor = crud.get_distributor_by_access_code(db, access_code=form_data.password)
    if not distributor or distributor.name != form_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect distributor name or access code",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": distributor.name, "distributor_id": distributor.id, "role": "distributor"}, 
        expires_delta=access_token_expires
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": distributor.name, "distributor_id": distributor.id, "role": "distributor"}
    )
    
    # Configurar cookies seguras
    auth.set_auth_cookies(response, access_token, refresh_token)
    
    # Registrar métricas de login
    business_metrics.record_user_login(user_id=distributor.id, user_type="distributor")
    
    # Log de auditoría
    logger.business(
        "distributor_login",
        distributor_id=distributor.id,
        distributor_name=distributor.name,
        login_type="distributor"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Endpoint para refrescar el access token usando el refresh token"""
    return await auth.refresh_access_token(request, response, db)

@router.post("/logout")
async def logout(response: Response):
    """Endpoint para cerrar sesión y limpiar cookies"""
    auth.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}

@router.get("/verify")
async def verify_auth(
    request: Request,
    db: Session = Depends(get_db)
):
    """Endpoint para verificar si el usuario está autenticado"""
    try:
        user = await auth.get_current_user(request, db)
        return {"authenticated": True, "user": user.username, "role": user.role.value}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
