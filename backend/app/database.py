from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .config import settings

Base = declarative_base()

def get_db_session_maker(database_url: str):
    # Configuración optimizada del engine con pooling
    engine = create_engine(
        database_url,
        # Configuración del pool de conexiones
        poolclass=QueuePool,
        pool_size=10,          # Número de conexiones permanentes en el pool
        max_overflow=20,       # Número máximo de conexiones adicionales
        pool_pre_ping=True,    # Verificar conexiones antes de usarlas
        pool_recycle=3600,     # Reciclar conexiones cada hora
        
        # Configuración de echo para desarrollo (cambiar a False en producción)
        echo=False,
        
        # Configuración adicional para PostgreSQL
        connect_args={
            "options": "-c timezone=utc"
        } if "postgresql" in database_url else {}
    )
    
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
