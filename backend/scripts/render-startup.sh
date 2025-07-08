#!/bin/bash

# ============================================
# RENDER STARTUP SCRIPT
# Script de inicio para despliegue en Render
# ============================================

set -euo pipefail

echo "🚀 Starting TuAppDeAccesorios on Render..."

# Variables de entorno
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-2}
export TIMEOUT=${TIMEOUT:-120}

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verificar variables de entorno críticas
check_env_vars() {
    log "📋 Checking environment variables..."
    
    local required_vars=(
        "DATABASE_URL"
        "SECRET_KEY"
        "ENVIRONMENT"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log "❌ ERROR: Missing required environment variable: $var"
            exit 1
        fi
    done
    
    log "✅ Required environment variables verified"
}

# Verificar conectividad de base de datos
check_database() {
    log "🗄️ Checking database connectivity..."
    
    # Intentar conectar usando Python
    python -c "
import sys
sys.path.append('/opt/render/project/src/backend')
from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" || {
        log "❌ Database connection failed. Waiting 10 seconds and retrying..."
        sleep 10
        python -c "
import sys
sys.path.append('/opt/render/project/src/backend')
from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful on retry')
except Exception as e:
    print(f'❌ Database connection failed on retry: {e}')
    sys.exit(1)
"
    }
}

# Ejecutar migraciones de base de datos
run_migrations() {
    log "🔄 Running database migrations..."
    
    # Verificar que Alembic esté configurado
    if [ ! -f "alembic.ini" ]; then
        log "❌ ERROR: alembic.ini not found"
        exit 1
    fi
    
    # Ejecutar migraciones
    python -m alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log "✅ Database migrations completed successfully"
    else
        log "❌ Database migrations failed"
        exit 1
    fi
}

# Verificar Redis (opcional)
check_redis() {
    if [ -n "${REDIS_URL:-}" ]; then
        log "🔴 Checking Redis connectivity..."
        
        python -c "
import redis
import os

try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'⚠️ Redis connection failed: {e}')
    print('🔄 Application will continue without Redis cache')
"
    else
        log "⚠️ Redis URL not configured, caching will be disabled"
    fi
}

# Crear directorios necesarios
setup_directories() {
    log "📁 Setting up directories..."
    
    # Crear directorio de logs
    mkdir -p /opt/render/project/src/logs
    
    # Crear directorio de backups si está habilitado
    if [ "${BACKUP_ENABLED:-false}" = "true" ]; then
        mkdir -p /opt/render/project/src/backups
    fi
    
    log "✅ Directories created"
}

# Verificar dependencias críticas
check_dependencies() {
    log "📦 Checking Python dependencies..."
    
    # Verificar que los paquetes críticos estén instalados
    python -c "
import fastapi
import sqlalchemy
import alembic
import uvicorn
print('✅ Critical dependencies verified')
"
}

# Configurar logging para producción
setup_logging() {
    log "📝 Setting up production logging..."
    
    # Configurar nivel de log basado en environment
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    log "✅ Logging configured (Level: $LOG_LEVEL)"
}

# Verificar salud de la aplicación antes de iniciar
health_check() {
    log "🏥 Performing pre-start health check..."
    
    python -c "
import sys
sys.path.append('/opt/render/project/src/backend')

try:
    from app.main import app
    from app.config import settings
    
    print(f'✅ Application loaded successfully')
    print(f'📊 Environment: {settings.environment}')
    print(f'🗄️ Database configured: {bool(settings.database_url)}')
    print(f'🔴 Redis configured: {bool(getattr(settings, \"redis_url\", None))}')
    print(f'🔒 Rate limiting: {settings.rate_limit_enabled}')
    
except Exception as e:
    print(f'❌ Application health check failed: {e}')
    sys.exit(1)
"
}

# Función principal de inicio
start_application() {
    log "🎯 Starting application with Gunicorn..."
    
    # Configuración de Gunicorn optimizada para Render
    exec gunicorn app.main:app \
        --bind "0.0.0.0:$PORT" \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout $TIMEOUT \
        --keep-alive 2 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --preload \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        --worker-tmp-dir /dev/shm
}

# Script principal
main() {
    log "🔥 TuAppDeAccesorios starting on Render..."
    log "🌐 Environment: ${ENVIRONMENT:-unknown}"
    log "🚪 Port: $PORT"
    log "👥 Workers: $WORKERS"
    
    # Ejecutar verificaciones
    check_env_vars
    setup_directories
    setup_logging
    check_dependencies
    check_database
    run_migrations
    check_redis
    health_check
    
    log "✅ All checks passed! Starting application..."
    
    # Iniciar aplicación
    start_application
}

# Manejo de señales para shutdown graceful
cleanup() {
    log "🛑 Shutting down gracefully..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Ejecutar script principal
main "$@"