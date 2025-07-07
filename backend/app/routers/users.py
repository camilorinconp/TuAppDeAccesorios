from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user
from ..logging_config import get_secure_logger
from ..security.endpoint_security import secure_endpoint, admin_required, validate_json_input
from ..security.input_validation import InputValidator

router = APIRouter()
logger = get_secure_logger(__name__)

@router.post("/users/", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
@secure_endpoint(max_requests_per_hour=20, require_admin=True, log_access=True)
@validate_json_input(max_size=10240)  # 10KB
@admin_required
def create_user(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    """Crear nuevo usuario con validación completa de seguridad"""
    
    # Validar y sanitizar inputs
    try:
        # Validar username
        if user.username:
            user.username = InputValidator.validate_input(user.username, 'alphanumeric', max_length=50)
        
        # Validar email
        if user.email:
            user.email = InputValidator.validate_input(user.email, 'email', max_length=255)
        
        # Validar full_name
        if user.full_name:
            user.full_name = InputValidator.validate_input(user.full_name, 'name', max_length=255)
        
        # Validaciones de negocio adicionales
        if len(user.username) < 3:
            raise HTTPException(status_code=400, detail="Username debe tener al menos 3 caracteres")
        
        if len(user.password) < 8:
            raise HTTPException(status_code=400, detail="Password debe tener al menos 8 caracteres")
            
    except HTTPException as e:
        logger.warning(
            f"Invalid user data provided",
            client_ip=request.client.host,
            username=user.username,
            error_detail=e.detail
        )
        raise e
    
    # Verificar si el usuario ya existe
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        logger.warning(
            f"Attempt to create duplicate user",
            client_ip=request.client.host,
            username=user.username
        )
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Verificar si el email ya existe
    existing_email = crud.get_user_by_email(db, email=user.email)
    if existing_email:
        logger.warning(
            f"Attempt to create user with duplicate email",
            client_ip=request.client.host,
            email=user.email
        )
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Crear usuario
    new_user = crud.create_user(db=db, user=user)
    
    # Log de auditoría
    logger.info(
        f"User created successfully",
        user_id=new_user.id,
        username=new_user.username,
        client_ip=request.client.host
    )
    
    return new_user

@router.get("/users/", response_model=List[schemas.User], dependencies=[Depends(get_current_admin_user)])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user