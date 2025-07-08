from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import products, distributors, users, auth_router, pos, consignments, reports, cache_admin, metrics, audit, search, performance, backup
# from .routers import celery_jobs  # Comentado temporalmente - falta dependencia celery
from .config import settings
from . import models # Importar todos los modelos para que SQLAlchemy los descubra
from .database import get_db_session_maker
# from .middleware import (
#     ErrorHandlingMiddleware, 
#     PerformanceMiddleware, 
#     ResponseCacheMiddleware,
#     LoggingMiddleware
# )
# from .middleware.security_headers import SecurityHeadersMiddleware, HTTPSRedirectMiddleware, SecurityValidationMiddleware
# from .middleware.audit_middleware import AuditMiddleware, AuthAuditMiddleware
# from .rate_limiter import RateLimitMiddleware
from .logging_config import setup_logging
from .metrics import metrics_registry
import os

# Configurar logging al inicio
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    environment=os.getenv("ENVIRONMENT", "development"),
    log_file=os.getenv("LOG_FILE", None),
    enable_console=True
)

app = FastAPI(
    title=settings.project_name,
    description="API para gestionar el inventario y las ventas de una tienda de accesorios para celulares.",
    version="0.1.0",
)

# Configurar CORS de manera restrictiva
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Request-ID"
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Agregar middleware personalizado (orden importante)
# app.add_middleware(HTTPSRedirectMiddleware)  # Primero: redireccionar a HTTPS
# app.add_middleware(SecurityValidationMiddleware)  # Segundo: validaciones de seguridad
# app.add_middleware(SecurityHeadersMiddleware)  # Tercero: headers de seguridad
# app.add_middleware(RateLimitMiddleware)  # Rate limiting antes de otros middlewares
# app.add_middleware(AuditMiddleware)  # Auditoría general
# app.add_middleware(AuthAuditMiddleware)  # Auditoría específica de autenticación
# app.add_middleware(LoggingMiddleware)
# app.add_middleware(PerformanceMiddleware)
# app.add_middleware(ErrorHandlingMiddleware)

# Agregar middleware de caché si está habilitado
# if settings.redis_cache_enabled:
#     app.add_middleware(ResponseCacheMiddleware, cache_ttl=settings.redis_cache_default_ttl)

# Configuración de la base de datos para la aplicación principal
SessionLocal, engine = get_db_session_maker(settings.database_url)

# Sobrescribir la dependencia get_db para la aplicación principal
def get_db():
    from .logging_config import get_logger
    from .metrics import measure_db_query
    
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

app.include_router(products.router)
app.include_router(distributors.router)
app.include_router(users.router)
app.include_router(auth_router.router)
app.include_router(pos.router)
app.include_router(consignments.router)
app.include_router(reports.router)
app.include_router(cache_admin.router)
app.include_router(metrics.router)
app.include_router(audit.router)
app.include_router(backup.router)
app.include_router(search.router)
app.include_router(performance.router)
# app.include_router(celery_jobs.router)  # Comentado temporalmente - falta dependencia celery

# Endpoint para métricas
@app.get("/metrics")
def get_metrics():
    """Endpoint para obtener métricas de la aplicación"""
    return metrics_registry.get_all_metrics()

@app.get("/health")
def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "metrics_summary": metrics_registry.get_summary()
    }

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a TuAppDeAccesorios!"}

from .security.audit_logger import audit_logger

@app.on_event("startup")
async def startup_event():
    """Evento que se ejecuta al iniciar la aplicación"""
    from .logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info(
        "Application starting",
        app_name=settings.project_name,
        environment=os.getenv("ENVIRONMENT", "development"),
        redis_enabled=settings.redis_cache_enabled,
        database_url=settings.database_url.split("@")[-1] if "@" in settings.database_url else "[hidden]"
    )
    audit_logger.start_periodic_flush()

@app.on_event("shutdown")
async def shutdown_event():
    """Evento que se ejecuta al cerrar la aplicación"""
    from .logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info(
        "Application shutting down",
        final_metrics=metrics_registry.get_summary()
    )