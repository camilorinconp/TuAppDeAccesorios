from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone # Importar timezone
from typing import Optional
import uuid
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .config import settings
from .utils import security
from .security.token_blacklist import token_blacklist, check_token_blacklist

# NO IMPORTAR get_db AQUI PARA EVITAR IMPORTACIONES CIRCULARES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Configuración para cookies seguras
COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Agregar JTI (JWT ID) único para tracking y revocación
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire, 
        "type": "access",
        "jti": jti,
        "iat": datetime.now(timezone.utc).timestamp()
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    # Agregar JTI único para refresh token también
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire, 
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(timezone.utc).timestamp()
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Configura las cookies de autenticación de forma segura"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,  # Basado en configuración de entorno
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        domain=None,  # No especificar dominio para mayor seguridad
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,  # Basado en configuración de entorno
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        domain=None,  # No especificar dominio para mayor seguridad
        path="/",
    )

def clear_auth_cookies(response: Response):
    """Limpia las cookies de autenticación"""
    response.delete_cookie(key=COOKIE_NAME)
    response.delete_cookie(key=REFRESH_COOKIE_NAME)

def get_token_from_request(request: Request) -> Optional[str]:
    """Extrae el token desde cookies o header Authorization"""
    # Primero intenta obtener desde cookies
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    
    # Si no está en cookies, intenta desde header Authorization
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    
    return None

def _decode_token(token: str, token_type: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verificar que el token no sea None o vacío
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != token_type:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

@check_token_blacklist
async def get_current_user(request: Request, db: Session):
    """Obtiene el usuario actual desde el token JWT con verificación de blacklist
    Nota: db debe ser inyectado como dependencia en el router
    """
    payload = _decode_token(get_token_from_request(request), "access")
    username: str = payload.get("sub")
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = schemas.TokenData(username=username)
    user = crud.get_user_by_username(db, username=token_data.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@check_token_blacklist
async def get_current_distributor(request: Request, db: Session):
    """Obtiene el distribuidor actual desde el token JWT"""
    payload = _decode_token(get_token_from_request(request), "access")
    distributor_name: str = payload.get("sub")
    distributor_id: int = payload.get("distributor_id")
    role: str = payload.get("role")
    
    if distributor_name is None or distributor_id is None or role != "distributor":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate distributor credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    distributor = crud.get_distributor(db, distributor_id=distributor_id)
    
    if distributor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate distributor credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return distributor

async def refresh_access_token(request: Request, response: Response, db: Session):
    """Refresca el access token usando el refresh token"""
    refresh_token = get_token_from_request(request)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    payload = _decode_token(refresh_token, "refresh")
    username: str = payload.get("sub")
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Crear nuevos tokens
    new_access_token = create_access_token(data={"sub": user.username})
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Configurar nuevas cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)
    
    return {"access_token": new_access_token, "token_type": "bearer"}