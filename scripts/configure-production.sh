#!/bin/bash

# Script para configurar variables de entorno productivas
# Uso: ./scripts/configure-production.sh <dominio>

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Verificar argumentos
if [ $# -ne 1 ]; then
    log_error "Uso: $0 <dominio>"
    log_error "Ejemplo: $0 tuapp.com"
    exit 1
fi

DOMAIN=$1

log_info "Configurando variables de entorno para producción"
log_info "Dominio: ${DOMAIN}"

# Verificar si el script generate-secrets.sh existe
if [ ! -f "scripts/generate-secrets.sh" ]; then
    log_error "El script generate-secrets.sh no existe"
    exit 1
fi

log_step "1. Generando secrets seguros..."

# Generar archivo .env.prod
./scripts/generate-secrets.sh > .env.prod

# Personalizar dominio en el archivo
log_step "2. Personalizando configuración con dominio ${DOMAIN}..."

# Usar sed para reemplazar el dominio en el archivo
sed -i.bak "s/tudominio.com/${DOMAIN}/g" .env.prod

# Personalizar configuraciones adicionales
log_step "3. Configurando parámetros adicionales..."

# Agregar configuraciones específicas de producción
cat >> .env.prod << EOF

# ============================================================================
# CONFIGURACIONES ADICIONALES DE PRODUCCIÓN
# ============================================================================

# BACKUP
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=tuapp-backups-${DOMAIN//./}

# MONITOREO
MONITORING_ENABLED=true
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# LOGGING AVANZADO
LOG_FORMAT=json
LOG_AUDIT_ENABLED=true
LOG_PERFORMANCE_ENABLED=true
LOG_RETENTION_DAYS=90

# PERFORMANCE
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=30
GUNICORN_KEEPALIVE=2
NGINX_WORKER_CONNECTIONS=1024

# SEGURIDAD ADICIONAL
SECURITY_HEADERS_ENABLED=true
CSRF_PROTECTION_ENABLED=true
XSS_PROTECTION_ENABLED=true
CONTENT_TYPE_NOSNIFF_ENABLED=true

# CACHE AVANZADO
CACHE_MIDDLEWARE_ENABLED=true
CACHE_STATIC_FILES_ENABLED=true
CACHE_API_RESPONSES_ENABLED=true
CACHE_DATABASE_QUERIES_ENABLED=true

# EMAIL (configurar según proveedor)
EMAIL_ENABLED=false
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=noreply@${DOMAIN}
EMAIL_PASSWORD=changeme
EMAIL_USE_TLS=true

# NOTIFICACIONES
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERTS_EMAIL=admin@${DOMAIN}

# ============================================================================
# CONFIGURACIÓN COMPLETADA
# ============================================================================
EOF

log_step "4. Validando configuración..."

# Verificar que el archivo se creó correctamente
if [ ! -f ".env.prod" ]; then
    log_error "Error al crear el archivo .env.prod"
    exit 1
fi

# Verificar que los secrets se generaron
if ! grep -q "SECRET_KEY=" .env.prod; then
    log_error "Error: SECRET_KEY no generado"
    exit 1
fi

if ! grep -q "POSTGRES_PASSWORD=" .env.prod; then
    log_error "Error: POSTGRES_PASSWORD no generado"
    exit 1
fi

if ! grep -q "REDIS_PASSWORD=" .env.prod; then
    log_error "Error: REDIS_PASSWORD no generado"
    exit 1
fi

log_step "5. Configurando permisos de seguridad..."

# Configurar permisos seguros para el archivo
chmod 600 .env.prod

# Crear backup del archivo original
cp .env.prod .env.prod.backup

log_step "6. Creando archivo de ejemplo para desarrollo..."

# Crear archivo de ejemplo sin secrets reales
cat > .env.example << EOF
# ============================================================================
# ARCHIVO DE EJEMPLO - CONFIGURACIÓN PARA DESARROLLO
# ============================================================================

# SEGURIDAD - GENERAR NUEVOS VALORES PARA PRODUCCIÓN
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=your-postgres-password
REDIS_PASSWORD=your-redis-password

# BASE DE DATOS
POSTGRES_USER=tuapp_user
POSTGRES_DB=tuapp_development
DATABASE_URL=postgresql://tuapp_user:password@db:5432/tuapp_development

# REDIS
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_ENABLED=true
REDIS_CACHE_DEFAULT_TTL=300

# AUTENTICACIÓN JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CONFIGURACIÓN DE DESARROLLO
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FILE=/app/logs/app.log
PROJECT_NAME=TuAppDeAccesorios

# SEGURIDAD Y CORS
ALLOWED_HOSTS=localhost,127.0.0.1,frontend
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
FORCE_HTTPS=false
SECURE_COOKIES=false

# RATE LIMITING
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# FRONTEND
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
GENERATE_SOURCEMAP=true

# ============================================================================
# PARA PRODUCCIÓN:
# 1. Ejecutar: ./scripts/configure-production.sh tudominio.com
# 2. Verificar configuración SSL
# 3. Ajustar variables según necesidades
# ============================================================================
EOF

log_step "7. Creando script de validación..."

# Crear script para validar configuración
cat > scripts/validate-env.sh << 'EOF'
#!/bin/bash

# Script para validar configuración de entorno
# Uso: ./scripts/validate-env.sh [archivo_env]

ENV_FILE=${1:-.env.prod}

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Archivo $ENV_FILE no encontrado"
    exit 1
fi

echo "Validando configuración en $ENV_FILE..."

# Validar que los secrets no estén vacíos
check_secret() {
    local key=$1
    local value=$(grep "^${key}=" "$ENV_FILE" | cut -d'=' -f2)
    
    if [ -z "$value" ] || [ "$value" = "changeme" ] || [ "$value" = "your-secret-key-here" ]; then
        echo "ERROR: $key no está configurado correctamente"
        return 1
    fi
    
    echo "OK: $key configurado"
    return 0
}

# Validar secrets críticos
check_secret "SECRET_KEY"
check_secret "POSTGRES_PASSWORD"
check_secret "REDIS_PASSWORD"

# Validar configuración de dominio
DOMAIN=$(grep "^ALLOWED_HOSTS=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$DOMAIN" == *"tudominio.com"* ]]; then
    echo "WARNING: Dominio por defecto detectado. Actualizar ALLOWED_HOSTS"
fi

# Validar configuración de CORS
CORS=$(grep "^CORS_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$CORS" == *"tudominio.com"* ]]; then
    echo "WARNING: CORS por defecto detectado. Actualizar CORS_ORIGINS"
fi

# Validar configuración de producción
ENV=$(grep "^ENVIRONMENT=" "$ENV_FILE" | cut -d'=' -f2)
if [ "$ENV" != "production" ]; then
    echo "WARNING: ENVIRONMENT no está configurado para producción"
fi

echo "Validación completada"
EOF

chmod +x scripts/validate-env.sh

log_step "8. Ejecutando validación..."

# Ejecutar validación
./scripts/validate-env.sh .env.prod

log_info "Configuración de producción completada exitosamente"

# Mostrar información importante
echo
echo "=================== CONFIGURACIÓN COMPLETADA ==================="
echo
log_info "Archivos creados:"
echo "  - .env.prod (configuración de producción)"
echo "  - .env.prod.backup (backup de seguridad)"
echo "  - .env.example (archivo de ejemplo)"
echo "  - scripts/validate-env.sh (script de validación)"
echo
log_info "Configuración aplicada:"
echo "  - Dominio: ${DOMAIN}"
echo "  - Secrets seguros generados"
echo "  - Configuración de producción optimizada"
echo "  - Permisos de seguridad configurados"
echo
log_warn "IMPORTANTE - SIGUIENTES PASOS:"
echo "  1. Verificar configuración: ./scripts/validate-env.sh"
echo "  2. Ejecutar security check: ./scripts/security-check.sh"
echo "  3. Configurar certificados SSL: ./scripts/ssl-setup.sh ${DOMAIN}"
echo "  4. Desplegar con: docker-compose -f docker-compose.prod.yml up -d"
echo
log_warn "SEGURIDAD:"
echo "  - NUNCA commitear el archivo .env.prod"
echo "  - Mantener backups seguros de la configuración"
echo "  - Rotar secrets periódicamente"
echo "  - Configurar alertas de seguridad"
echo
echo "=============================================================="