#!/bin/bash

# Script de verificación de seguridad antes del deploy
echo "🔍 VERIFICACIÓN DE SEGURIDAD PARA PRODUCCIÓN"
echo "============================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Función para verificaciones
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "1. VERIFICANDO ARCHIVOS DE CONFIGURACIÓN..."
echo "--------------------------------------------"

# Verificar que existe .env.prod
if [ -f ".env.prod" ]; then
    check_pass "Archivo .env.prod existe"
    
    # Verificar SECRET_KEY
    if grep -q "SECRET_KEY=" .env.prod && ! grep -q "your-secret-key" .env.prod; then
        check_pass "SECRET_KEY configurado (no es valor por defecto)"
    else
        check_fail "SECRET_KEY no configurado o usando valor por defecto"
    fi
    
    # Verificar contraseñas
    if grep -q "POSTGRES_PASSWORD=" .env.prod && ! grep -q "password" .env.prod; then
        check_pass "Contraseña de PostgreSQL configurada"
    else
        check_fail "Contraseña de PostgreSQL no configurada o insegura"
    fi
    
    # Verificar HTTPS
    if grep -q "FORCE_HTTPS=true" .env.prod; then
        check_pass "HTTPS forzado habilitado"
    else
        check_warn "HTTPS no está forzado - verificar configuración SSL"
    fi
    
    # Verificar dominio
    if grep -q "tudominio.com" .env.prod; then
        check_warn "Dominio por defecto detectado - cambiar por dominio real"
    else
        check_pass "Dominio personalizado configurado"
    fi
    
else
    check_fail "Archivo .env.prod no encontrado - ejecutar ./scripts/generate-secrets.sh"
fi

echo ""
echo "2. VERIFICANDO CONFIGURACIÓN DOCKER..."
echo "-------------------------------------"

# Verificar docker-compose.prod.yml
if [ -f "docker-compose.prod.yml" ]; then
    check_pass "docker-compose.prod.yml existe"
    
    # Verificar que no expone puertos de DB
    if ! grep -q "5432:5432" docker-compose.prod.yml; then
        check_pass "Puerto de PostgreSQL no expuesto públicamente"
    else
        check_fail "Puerto de PostgreSQL expuesto públicamente"
    fi
    
    # Verificar health checks
    if grep -q "healthcheck:" docker-compose.prod.yml; then
        check_pass "Health checks configurados"
    else
        check_warn "Health checks no configurados"
    fi
    
else
    check_fail "docker-compose.prod.yml no encontrado"
fi

echo ""
echo "3. VERIFICANDO CERTIFICADOS SSL..."
echo "--------------------------------"

if [ -d "nginx/ssl" ]; then
    if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/private.key" ]; then
        check_pass "Certificados SSL encontrados"
    else
        check_fail "Certificados SSL no encontrados en nginx/ssl/"
    fi
else
    check_fail "Directorio nginx/ssl/ no existe - crear certificados SSL"
fi

echo ""
echo "4. VERIFICANDO CONFIGURACIÓN DE SEGURIDAD..."
echo "-------------------------------------------"

# Verificar middleware de rate limiting
if grep -q "RateLimitMiddleware" backend/app/main.py; then
    check_pass "Rate limiting middleware configurado"
else
    check_fail "Rate limiting middleware no configurado"
fi

# Verificar headers de seguridad
if grep -q "SecurityHeadersMiddleware" backend/app/main.py; then
    check_pass "Security headers middleware configurado"
else
    check_fail "Security headers middleware no configurado"
fi

# Verificar CORS restrictivo
if grep -q "cors_origins_list" backend/app/main.py; then
    check_pass "CORS restrictivo configurado"
else
    check_warn "CORS podría no estar configurado restrictivamente"
fi

echo ""
echo "5. VERIFICANDO DEPENDENCIAS..."
echo "-----------------------------"

# Verificar requirements.txt actualizado
if grep -q "fastapi>=0.104" backend/requirements.txt; then
    check_pass "FastAPI actualizado a versión segura"
else
    check_warn "Verificar versión de FastAPI"
fi

# Verificar python-json-logger
if grep -q "python-json-logger" backend/requirements.txt; then
    check_pass "Logging estructurado configurado"
else
    check_fail "python-json-logger no encontrado"
fi

echo ""
echo "6. VERIFICANDO ARCHIVOS SENSIBLES..."
echo "-----------------------------------"

# Verificar .gitignore
if grep -q ".env.prod" .gitignore 2>/dev/null; then
    check_pass ".env.prod en .gitignore"
else
    check_warn ".env.prod no está en .gitignore - agregar para seguridad"
fi

# Verificar que no hay secrets en el código
if grep -r "password.*=" backend/app/ | grep -v "hashed_password" | grep -v "POSTGRES_PASSWORD" | grep -q .; then
    check_warn "Posibles contraseñas hardcodeadas encontradas en el código"
else
    check_pass "No se encontraron contraseñas hardcodeadas"
fi

echo ""
echo "============================================="
echo "RESUMEN DE VERIFICACIÓN:"
echo "============================================="
echo -e "${GREEN}✓ Verificaciones pasadas: $PASSED${NC}"
echo -e "${YELLOW}⚠ Advertencias: $WARNINGS${NC}"
echo -e "${RED}✗ Verificaciones fallidas: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡EXCELENTE! La aplicación está lista para producción.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Casi listo. Revisar advertencias antes del deploy.${NC}"
    exit 1
else
    echo -e "${RED}❌ NO ESTÁ LISTO. Resolver problemas críticos antes del deploy.${NC}"
    echo ""
    echo "PRÓXIMOS PASOS:"
    echo "1. Resolver todos los ítems marcados con ✗"
    echo "2. Generar certificados SSL si es necesario"
    echo "3. Ejecutar ./scripts/generate-secrets.sh > .env.prod"
    echo "4. Revisar y personalizar dominios en .env.prod"
    echo "5. Volver a ejecutar este script"
    exit 2
fi