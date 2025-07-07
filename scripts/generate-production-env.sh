#!/bin/bash

# ============================================
# SCRIPT DE GENERACIÓN DE VARIABLES DE ENTORNO DE PRODUCCIÓN
# TuAppDeAccesorios
# ============================================

set -e

echo "🔧 Generando configuración de producción para TuAppDeAccesorios..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para generar contraseñas seguras
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Función para generar claves secretas
generate_secret_key() {
    openssl rand -hex 32
}

# Verificar si ya existe .env.production
if [[ -f ".env.production" ]]; then
    echo -e "${YELLOW}⚠️  Ya existe un archivo .env.production${NC}"
    read -p "¿Deseas sobreescribirlo? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}ℹ️  Operación cancelada${NC}"
        exit 0
    fi
fi

# Solicitar información del usuario
echo -e "${BLUE}📝 Configuración de Producción${NC}"
echo "Por favor, proporciona la siguiente información:"
echo

# Dominio
read -p "🌐 Dominio principal (ej: tudominio.com): " DOMAIN_NAME
if [[ -z "$DOMAIN_NAME" ]]; then
    echo -e "${RED}❌ El dominio es requerido${NC}"
    exit 1
fi

# Email para alertas
read -p "📧 Email para alertas: " ALERT_EMAIL
if [[ -z "$ALERT_EMAIL" ]]; then
    echo -e "${RED}❌ El email es requerido${NC}"
    exit 1
fi

# Configuración de base de datos
read -p "🗄️  Usuario de base de datos [tuapp_prod_user]: " DB_USER
DB_USER=${DB_USER:-tuapp_prod_user}

read -p "🗄️  Nombre de base de datos [tuapp_production]: " DB_NAME
DB_NAME=${DB_NAME:-tuapp_production}

# Generar contraseñas automáticamente
echo -e "${YELLOW}🔐 Generando contraseñas seguras...${NC}"
DB_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)
SECRET_KEY=$(generate_secret_key)
GRAFANA_PASSWORD=$(generate_password)

# Crear archivo .env.production
cat > .env.production << EOF
# ============================================
# CONFIGURACIÓN DE PRODUCCIÓN - TuAppDeAccesorios
# ============================================
# Generado automáticamente el $(date)
# IMPORTANTE: Mantener este archivo seguro y no subirlo a Git

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=${DB_NAME}
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}

# ============================================
# CONFIGURACIÓN DE AUTENTICACIÓN
# ============================================
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================
# CONFIGURACIÓN DE REDIS
# ============================================
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_CACHE_ENABLED=true
REDIS_CACHE_DEFAULT_TTL=300

# ============================================
# CONFIGURACIÓN DE APLICACIÓN
# ============================================
ENVIRONMENT=production
PROJECT_NAME=TuAppDeAccesorios
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# ============================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================
CORS_ORIGINS=["https://${DOMAIN_NAME}", "https://www.${DOMAIN_NAME}"]
ALLOWED_HOSTS=["${DOMAIN_NAME}", "www.${DOMAIN_NAME}"]

# ============================================
# CONFIGURACIÓN DE FRONTEND
# ============================================
REACT_APP_API_URL=https://${DOMAIN_NAME}
REACT_APP_ENVIRONMENT=production
GENERATE_SOURCEMAP=false

# ============================================
# CONFIGURACIÓN DE SSL/TLS
# ============================================
SSL_CERT_PATH=/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem
DOMAIN_NAME=${DOMAIN_NAME}

# ============================================
# CONFIGURACIÓN DE MONITOREO
# ============================================
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
ALERT_EMAIL=${ALERT_EMAIL}

# ============================================
# CONFIGURACIÓN DE BACKUPS
# ============================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30

# ============================================
# CONFIGURACIÓN DE RATE LIMITING
# ============================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=10

# ============================================
# CONFIGURACIÓN DE PERFORMANCE
# ============================================
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=30
GUNICORN_KEEPALIVE=2
MAX_UPLOAD_SIZE=10485760
EOF

# Crear archivo de credenciales para referencia
cat > .production-credentials.txt << EOF
# ============================================
# CREDENCIALES DE PRODUCCIÓN - TuAppDeAccesorios
# ============================================
# Generado el $(date)
# IMPORTANTE: Guardar estas credenciales en un lugar seguro

Dominio: ${DOMAIN_NAME}
Email de alertas: ${ALERT_EMAIL}

Base de Datos:
  Usuario: ${DB_USER}
  Contraseña: ${DB_PASSWORD}
  Base de datos: ${DB_NAME}

Redis:
  Contraseña: ${REDIS_PASSWORD}

JWT:
  Clave secreta: ${SECRET_KEY}

Grafana:
  Usuario: admin
  Contraseña: ${GRAFANA_PASSWORD}

URLs importantes:
  - Frontend: https://${DOMAIN_NAME}
  - API: https://${DOMAIN_NAME}/api
  - Grafana: https://${DOMAIN_NAME}:3000
  - Prometheus: https://${DOMAIN_NAME}:9090
EOF

# Establecer permisos restrictivos
chmod 600 .env.production
chmod 600 .production-credentials.txt

echo -e "${GREEN}✅ Configuración de producción generada exitosamente!${NC}"
echo
echo -e "${YELLOW}📋 Archivos creados:${NC}"
echo "  - .env.production (variables de entorno)"
echo "  - .production-credentials.txt (credenciales de referencia)"
echo
echo -e "${YELLOW}🔐 Información importante:${NC}"
echo "  - Las contraseñas han sido generadas automáticamente"
echo "  - Guarda el archivo .production-credentials.txt en un lugar seguro"
echo "  - NUNCA subas estos archivos a Git"
echo "  - Configura tu dominio DNS para apuntar a tu servidor"
echo
echo -e "${BLUE}🚀 Próximos pasos:${NC}"
echo "  1. Configura tu servidor con Docker y Docker Compose"
echo "  2. Copia el archivo .env.production a tu servidor"
echo "  3. Ejecuta el script de SSL: ./scripts/setup-ssl.sh"
echo "  4. Inicia los servicios: docker-compose -f docker-compose.prod.yml up -d"
echo
echo -e "${GREEN}🎉 ¡Listo para producción!${NC}"