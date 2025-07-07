#!/bin/bash

# Script para generar secrets seguros para producción
# Usar: ./scripts/generate-secrets.sh > .env.prod

echo "# ============================================================================"
echo "# CONFIGURACIÓN SEGURA PARA PRODUCCIÓN - GENERADA AUTOMÁTICAMENTE"
echo "# FECHA: $(date)"
echo "# ============================================================================"
echo ""

echo "# SEGURIDAD - SECRETOS ÚNICOS GENERADOS"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/')"
echo "REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '=+/')"
echo ""

echo "# BASE DE DATOS"
echo "POSTGRES_USER=tuapp_prod_user"
echo "POSTGRES_DB=tuapp_production"
echo "DATABASE_URL=postgresql://tuapp_prod_user:\${POSTGRES_PASSWORD}@db:5432/tuapp_production"
echo ""

echo "# REDIS"
echo "REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0"
echo "REDIS_CACHE_ENABLED=true"
echo "REDIS_CACHE_DEFAULT_TTL=300"
echo ""

echo "# AUTENTICACIÓN JWT"
echo "ALGORITHM=HS256"
echo "ACCESS_TOKEN_EXPIRE_MINUTES=15"
echo "REFRESH_TOKEN_EXPIRE_DAYS=7"
echo ""

echo "# CONFIGURACIÓN DE PRODUCCIÓN"
echo "ENVIRONMENT=production"
echo "LOG_LEVEL=INFO"
echo "LOG_FILE=/app/logs/app.log"
echo "PROJECT_NAME=TuAppDeAccesorios"
echo ""

echo "# SEGURIDAD Y CORS (AJUSTAR SEGÚN DOMINIO)"
echo "ALLOWED_HOSTS=tudominio.com,www.tudominio.com,api.tudominio.com"
echo "CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com"
echo "FORCE_HTTPS=true"
echo "SECURE_COOKIES=true"
echo ""

echo "# RATE LIMITING"
echo "RATE_LIMIT_ENABLED=true"
echo "RATE_LIMIT_REQUESTS=100"
echo "RATE_LIMIT_WINDOW=3600"
echo ""

echo "# FRONTEND"
echo "REACT_APP_API_URL=https://api.tudominio.com"
echo "REACT_APP_ENVIRONMENT=production"
echo "GENERATE_SOURCEMAP=false"
echo ""

echo "# ============================================================================"
echo "# IMPORTANTE: "
echo "# 1. Cambiar 'tudominio.com' por tu dominio real"
echo "# 2. Guardar este archivo como .env.prod"
echo "# 3. Nunca commitear este archivo con valores reales"
echo "# 4. Configurar certificados SSL antes del deploy"
echo "# ============================================================================"