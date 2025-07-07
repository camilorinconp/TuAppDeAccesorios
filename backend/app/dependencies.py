from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from . import models, auth

# Esta función será sobrescrita en main.py para usar la SessionLocal correcta
def get_db():
    from .database import get_db_session_maker
    from .config import settings
    from .logging_config import get_logger
    from .metrics import measure_db_query
    
    # Crear sesión de base de datos
    SessionLocal, engine = get_db_session_maker(settings.database_url)
    logger = get_logger(__name__)
    db = SessionLocal()
    try:
        with measure_db_query("session_lifecycle"):
            yield db
    except Exception as e:
        logger.error(
            "Database session error",
            error=e,
            operation="session_lifecycle"
        )
        db.rollback()
        raise
    finally:
        db.close()

# Alias para compatibilidad con otros routers
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # Obtener el usuario actual usando el nuevo sistema de autenticación
    return await auth.get_current_user(request, db)

async def get_current_active_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # Obtener el usuario actual usando el nuevo sistema de autenticación
    current_user = await auth.get_current_user(request, db)
    # Aquí podrías añadir lógica para verificar si el usuario está activo, etc.
    return current_user

# Función para obtener distribuidor actual
async def get_current_distributor(
    request: Request,
    db: Session = Depends(get_db)
):
    # Obtener el distribuidor actual usando el sistema de autenticación JWT
    return await auth.get_current_distributor(request, db)

async def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = await get_current_active_user(request, db)
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (admin required)"
        )
    return current_user

async def get_current_sales_staff_user(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = await get_current_active_user(request, db)
    if current_user.role not in [models.UserRole.admin, models.UserRole.sales_staff]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (sales staff or admin required)"
        )
    return current_user