from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from .config import settings
import os

Base = declarative_base()

def get_db_session_maker(database_url: str):
    """Configuración optimizada del engine con pooling para diferentes entornos"""
    
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    is_sqlite = "sqlite" in database_url
    is_postgresql = "postgresql" in database_url
    
    # Configuración específica por tipo de base de datos
    if is_sqlite:
        # SQLite: configuración para desarrollo
        engine_config = {
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20
            },
            "echo": False
        }
    elif is_postgresql:
        # PostgreSQL: configuración optimizada para producción
        pool_size = 20 if is_production else 10
        max_overflow = 30 if is_production else 20
        
        engine_config = {
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_pre_ping": True,
            "pool_recycle": 7200 if is_production else 3600,  # 2h prod, 1h dev
            "pool_timeout": 30,
            "echo": False,
            "connect_args": {
                "options": "-c timezone=utc",
                "connect_timeout": 10,
                "application_name": "TuAppDeAccesorios"
            }
        }
    else:
        # Fallback para otros tipos de BD
        engine_config = {
            "poolclass": QueuePool,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "echo": False
        }
    
    engine = create_engine(database_url, **engine_config)
    
    SessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine,
        # Configuración adicional para mejor rendimiento
        expire_on_commit=False
    )
    
    return SessionLocal, engine

# Crear instancias globales para compatibilidad
SessionLocal, engine = get_db_session_maker(settings.database_url)

# Función de dependencia para FastAPI
def get_db():
    """Dependencia para obtener sesión de base de datos"""
    from .logging_config import get_logger
    
    logger = get_logger(__name__)
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
