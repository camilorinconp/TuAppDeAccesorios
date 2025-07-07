#!/bin/bash

# ============================================
# SCRIPT DE VALIDACIÓN DE CONFIGURACIÓN DE PRODUCCIÓN
# TuAppDeAccesorios
# ============================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🔍 Validando Configuración de Producción"
echo "========================================"

# Contadores
ERRORS=0
WARNINGS=0
PASSED=0

# Función para validar configuración
validate_config() {
    local config_name="$1"
    local config_value="$2"
    local validation_type="$3"
    local is_required="$4"
    
    case $validation_type in
        "not_empty")
            if [[ -z "$config_value" ]]; then
                if [[ "$is_required" == "true" ]]; then
                    log_error "$config_name está vacío"
                    ((ERRORS++))
                else
                    log_warning "$config_name está vacío (opcional)"
                    ((WARNINGS++))
                fi
            else
                log_success "$config_name configurado"
                ((PASSED++))
            fi
            ;;
        "https_url")
            if [[ -z "$config_value" ]]; then
                log_error "$config_name está vacío"
                ((ERRORS++))
            elif [[ "$config_value" =~ ^https:// ]]; then
                log_success "$config_name usa HTTPS"
                ((PASSED++))
            else
                log_error "$config_name debe usar HTTPS en producción"
                ((ERRORS++))
            fi
            ;;
        "secure_password")
            if [[ -z "$config_value" ]]; then
                log_error "$config_name está vacío"
                ((ERRORS++))
            elif [[ ${#config_value} -lt 20 ]]; then
                log_warning "$config_name es muy corto (mínimo 20 caracteres)"
                ((WARNINGS++))
            elif [[ "$config_value" == *"password"* ]] || [[ "$config_value" == *"123"* ]]; then
                log_error "$config_name parece ser una contraseña por defecto"
                ((ERRORS++))
            else
                log_success "$config_name parece seguro"
                ((PASSED++))
            fi
            ;;
        "domain")
            if [[ -z "$config_value" ]]; then
                log_error "$config_name está vacío"
                ((ERRORS++))
            elif [[ "$config_value" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                log_success "$config_name tiene formato válido"
                ((PASSED++))
            else
                log_error "$config_name tiene formato inválido"
                ((ERRORS++))
            fi
            ;;
        "cors_origins")
            if [[ -z "$config_value" ]]; then
                log_error "$config_name está vacío"
                ((ERRORS++))
            elif [[ "$config_value" =~ http://localhost ]]; then
                log_warning "$config_name contiene localhost (no recomendado en producción)"
                ((WARNINGS++))
            elif [[ "$config_value" =~ https:// ]]; then
                log_success "$config_name usa HTTPS"
                ((PASSED++))
            else
                log_error "$config_name debe usar HTTPS"
                ((ERRORS++))
            fi
            ;;
        "environment")
            if [[ "$config_value" == "production" ]]; then
                log_success "$config_name configurado para producción"
                ((PASSED++))
            else
                log_error "$config_name debe ser 'production'"
                ((ERRORS++))
            fi
            ;;
    esac
}

# Cargar variables de entorno
if [[ -f ".env.production" ]]; then
    source .env.production
    log_info "Variables de entorno cargadas desde .env.production"
else
    log_error "No se encontró archivo .env.production"
    exit 1
fi

echo
echo "🔐 Validando Configuración de Seguridad"
echo "======================================="

# Validar configuraciones críticas
validate_config "SECRET_KEY" "$SECRET_KEY" "secure_password" "true"
validate_config "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD" "secure_password" "true"
validate_config "REDIS_PASSWORD" "$REDIS_PASSWORD" "secure_password" "true"
validate_config "ENVIRONMENT" "$ENVIRONMENT" "environment" "true"

echo
echo "🌐 Validando Configuración de Red"
echo "================================="

validate_config "DOMAIN_NAME" "$DOMAIN_NAME" "domain" "true"
validate_config "REACT_APP_API_URL" "$REACT_APP_API_URL" "https_url" "true"
validate_config "CORS_ORIGINS" "$CORS_ORIGINS" "cors_origins" "true"

echo
echo "📧 Validando Configuración de Notificaciones"
echo "============================================"

validate_config "ALERT_EMAIL" "$ALERT_EMAIL" "not_empty" "true"
validate_config "SMTP_HOST" "$SMTP_HOST" "not_empty" "false"
validate_config "SMTP_USER" "$SMTP_USER" "not_empty" "false"

echo
echo "💾 Validando Configuración de Backups"
echo "===================================="

validate_config "BACKUP_ENABLED" "$BACKUP_ENABLED" "not_empty" "false"
validate_config "BACKUP_S3_BUCKET" "$BACKUP_S3_BUCKET" "not_empty" "false"
validate_config "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID" "not_empty" "false"

echo
echo "🔧 Validando Configuración del Sistema"
echo "====================================="

# Verificar que Grafana tenga contraseña segura
validate_config "GRAFANA_ADMIN_PASSWORD" "$GRAFANA_ADMIN_PASSWORD" "secure_password" "true"

# Verificar que GENERATE_SOURCEMAP esté deshabilitado
if [[ "$GENERATE_SOURCEMAP" == "false" ]]; then
    log_success "GENERATE_SOURCEMAP deshabilitado para producción"
    ((PASSED++))
else
    log_warning "GENERATE_SOURCEMAP debería estar deshabilitado en producción"
    ((WARNINGS++))
fi

# Verificar configuración de SSL
if [[ -n "$SSL_CERT_PATH" && -n "$SSL_KEY_PATH" ]]; then
    log_success "Rutas de certificados SSL configuradas"
    ((PASSED++))
else
    log_warning "Rutas de certificados SSL no configuradas"
    ((WARNINGS++))
fi

echo
echo "🔍 Validaciones Adicionales de Seguridad"
echo "========================================"

# Verificar que no se usen valores por defecto
if [[ "$SECRET_KEY" == *"CHANGE_THIS"* ]]; then
    log_error "SECRET_KEY contiene valor por defecto"
    ((ERRORS++))
else
    log_success "SECRET_KEY no usa valor por defecto"
    ((PASSED++))
fi

if [[ "$POSTGRES_PASSWORD" == *"CHANGE_THIS"* ]]; then
    log_error "POSTGRES_PASSWORD contiene valor por defecto"
    ((ERRORS++))
else
    log_success "POSTGRES_PASSWORD no usa valor por defecto"
    ((PASSED++))
fi

# Verificar que el dominio no sea de ejemplo
if [[ "$DOMAIN_NAME" == "tudominio.com" || "$DOMAIN_NAME" == "yourdomain.com" ]]; then
    log_error "DOMAIN_NAME usa valor de ejemplo"
    ((ERRORS++))
else
    log_success "DOMAIN_NAME configurado correctamente"
    ((PASSED++))
fi

# Verificar configuración de Rate Limiting
if [[ -n "$RATE_LIMIT_REQUESTS" && "$RATE_LIMIT_REQUESTS" -gt 0 ]]; then
    log_success "Rate limiting configurado"
    ((PASSED++))
else
    log_warning "Rate limiting no configurado"
    ((WARNINGS++))
fi

echo
echo "📋 Resumen de Validación"
echo "======================="
echo -e "✅ Configuraciones correctas: ${GREEN}$PASSED${NC}"
echo -e "⚠️  Advertencias: ${YELLOW}$WARNINGS${NC}"
echo -e "❌ Errores críticos: ${RED}$ERRORS${NC}"

echo
if [[ $ERRORS -eq 0 ]]; then
    if [[ $WARNINGS -eq 0 ]]; then
        log_success "¡Configuración de producción perfecta!"
        echo -e "${GREEN}🚀 El sistema está listo para ser desplegado en producción${NC}"
    else
        log_warning "Configuración lista con advertencias menores"
        echo -e "${YELLOW}🔧 Considera revisar las advertencias antes del despliegue${NC}"
    fi
    exit 0
else
    log_error "Configuración tiene errores críticos"
    echo -e "${RED}🛑 Corrige los errores antes de desplegar en producción${NC}"
    echo
    echo "💡 Sugerencias:"
    echo "  - Ejecuta: ./scripts/generate-production-env.sh"
    echo "  - Revisa el archivo .env.production"
    echo "  - Cambia todos los valores que contengan 'CHANGE_THIS'"
    echo "  - Configura tu dominio real"
    exit 1
fi