#!/bin/bash

# Script para validar configuración de Docker y Docker Compose
echo "🔍 VALIDANDO CONFIGURACIÓN DOCKER"
echo "================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Funciones de verificación
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

echo "1. VERIFICANDO DOCKERFILES..."
echo "----------------------------"

# Verificar Dockerfile del backend
if [ -f "backend/Dockerfile" ]; then
    check_pass "backend/Dockerfile existe"
    
    # Verificar usuario no-root
    if grep -q "USER appuser" backend/Dockerfile; then
        check_pass "Backend Dockerfile usa usuario no-root"
    else
        check_fail "Backend Dockerfile no configura usuario no-root"
    fi
    
    # Verificar multi-stage build
    if grep -q "FROM.*AS" backend/Dockerfile; then
        check_pass "Backend Dockerfile usa multi-stage build"
    else
        check_warn "Backend Dockerfile no usa multi-stage build"
    fi
    
    # Verificar healthcheck
    if grep -q "HEALTHCHECK" backend/Dockerfile; then
        check_pass "Backend Dockerfile tiene healthcheck"
    else
        check_fail "Backend Dockerfile no tiene healthcheck"
    fi
else
    check_fail "backend/Dockerfile no encontrado"
fi

# Verificar Dockerfile.prod del backend
if [ -f "backend/Dockerfile.prod" ]; then
    check_pass "backend/Dockerfile.prod existe"
    
    if grep -q "FROM.*builder" backend/Dockerfile.prod; then
        check_pass "Backend Dockerfile.prod usa build optimizado"
    else
        check_warn "Backend Dockerfile.prod podría no estar optimizado"
    fi
else
    check_fail "backend/Dockerfile.prod no encontrado"
fi

# Verificar Dockerfile del frontend
if [ -f "frontend/Dockerfile" ]; then
    check_pass "frontend/Dockerfile existe"
    
    if grep -q "USER reactjs" frontend/Dockerfile; then
        check_pass "Frontend Dockerfile usa usuario no-root"
    else
        check_fail "Frontend Dockerfile no configura usuario no-root"
    fi
else
    check_fail "frontend/Dockerfile no encontrado"
fi

# Verificar Dockerfile.prod del frontend
if [ -f "frontend/Dockerfile.prod" ]; then
    check_pass "frontend/Dockerfile.prod existe"
    
    # Verificar que use nginx
    if grep -q "FROM nginx" frontend/Dockerfile.prod; then
        check_pass "Frontend Dockerfile.prod usa nginx"
    else
        check_fail "Frontend Dockerfile.prod no usa nginx"
    fi
    
    # Verificar configuración de seguridad
    if grep -q "X-Content-Type-Options" frontend/Dockerfile.prod; then
        check_pass "Frontend Dockerfile.prod configura headers de seguridad"
    else
        check_warn "Frontend Dockerfile.prod no configura headers de seguridad"
    fi
else
    check_fail "frontend/Dockerfile.prod no encontrado"
fi

echo ""
echo "2. VERIFICANDO DOCKER-COMPOSE..."
echo "-------------------------------"

# Verificar docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    check_pass "docker-compose.yml existe"
    
    # Verificar servicios esenciales
    if docker-compose config | grep -q "services:"; then
        check_pass "docker-compose.yml tiene configuración válida"
        
        # Verificar servicios individuales
        if docker-compose config | grep -q "db:"; then
            check_pass "Servicio de base de datos configurado"
        else
            check_fail "Servicio de base de datos no encontrado"
        fi
        
        if docker-compose config | grep -q "redis:"; then
            check_pass "Servicio Redis configurado"
        else
            check_fail "Servicio Redis no encontrado"
        fi
        
        if docker-compose config | grep -q "backend:"; then
            check_pass "Servicio backend configurado"
        else
            check_fail "Servicio backend no encontrado"
        fi
        
        if docker-compose config | grep -q "frontend:"; then
            check_pass "Servicio frontend configurado"
        else
            check_fail "Servicio frontend no encontrado"
        fi
    else
        check_fail "docker-compose.yml tiene configuración inválida"
    fi
    
    # Verificar health checks
    if grep -q "healthcheck:" docker-compose.yml; then
        check_pass "Health checks configurados"
    else
        check_warn "Health checks no configurados"
    fi
    
    # Verificar volúmenes
    if grep -q "volumes:" docker-compose.yml; then
        check_pass "Volúmenes configurados"
    else
        check_fail "Volúmenes no configurados"
    fi
    
    # Verificar si expone puerto de DB (desarrollo)
    if grep -q "5432:5432" docker-compose.yml; then
        check_warn "Puerto de PostgreSQL expuesto (OK para desarrollo)"
    fi
    
else
    check_fail "docker-compose.yml no encontrado"
fi

# Verificar docker-compose.prod.yml
if [ -f "docker-compose.prod.yml" ]; then
    check_pass "docker-compose.prod.yml existe"
    
    # Verificar que NO expone puerto de DB
    if ! grep -q "5432:5432" docker-compose.prod.yml; then
        check_pass "Puerto de PostgreSQL no expuesto en producción"
    else
        check_fail "Puerto de PostgreSQL expuesto en producción (PELIGROSO)"
    fi
    
    # Verificar límites de recursos
    if grep -q "deploy:" docker-compose.prod.yml && grep -q "resources:" docker-compose.prod.yml; then
        check_pass "Límites de recursos configurados"
    else
        check_warn "Límites de recursos no configurados"
    fi
    
    # Verificar servicio de backup
    if grep -q "backup:" docker-compose.prod.yml; then
        check_pass "Servicio de backup configurado"
    else
        check_fail "Servicio de backup no configurado"
    fi
    
else
    check_fail "docker-compose.prod.yml no encontrado"
fi

echo ""
echo "3. VERIFICANDO CONFIGURACIÓN DE BASE DE DATOS..."
echo "-----------------------------------------------"

# Verificar configuración de PostgreSQL
if [ -f "database/postgresql.conf" ]; then
    check_pass "Configuración personalizada de PostgreSQL"
    
    if grep -q "shared_buffers" database/postgresql.conf; then
        check_pass "Optimización de memoria configurada"
    else
        check_warn "Optimización de memoria no configurada"
    fi
    
    if grep -q "log_min_duration_statement" database/postgresql.conf; then
        check_pass "Logging de queries lentas configurado"
    else
        check_warn "Logging de queries lentas no configurado"
    fi
else
    check_warn "Configuración personalizada de PostgreSQL no encontrada"
fi

# Verificar script de inicialización
if [ -f "database/init-user-db.sh" ]; then
    check_pass "Script de inicialización de DB encontrado"
    
    if [ -x "database/init-user-db.sh" ]; then
        check_pass "Script de inicialización es ejecutable"
    else
        check_fail "Script de inicialización no es ejecutable"
    fi
else
    check_warn "Script de inicialización de DB no encontrado"
fi

echo ""
echo "4. VERIFICANDO REDES Y CONECTIVIDAD..."
echo "------------------------------------"

# Verificar configuración de redes en docker-compose
if grep -q "networks:" docker-compose.yml 2>/dev/null; then
    check_pass "Redes personalizadas configuradas"
else
    check_warn "Usando red por defecto (puede estar bien)"
fi

# Verificar configuración de depends_on
if grep -q "depends_on:" docker-compose.yml; then
    check_pass "Dependencias entre servicios configuradas"
else
    check_warn "Dependencias entre servicios no especificadas"
fi

echo ""
echo "5. VERIFICANDO CONFIGURACIÓN DE SEGURIDAD..."
echo "-------------------------------------------"

# Verificar variables de entorno
if [ -f ".env.example" ]; then
    check_pass "Archivo .env.example existe"
    
    if grep -q "SECRET_KEY" .env.example; then
        check_pass "Variable SECRET_KEY documentada"
    else
        check_fail "Variable SECRET_KEY no documentada"
    fi
    
    if grep -q "POSTGRES_PASSWORD" .env.example; then
        check_pass "Variable POSTGRES_PASSWORD documentada"
    else
        check_fail "Variable POSTGRES_PASSWORD no documentada"
    fi
else
    check_fail "Archivo .env.example no encontrado"
fi

# Verificar que no hay secretos hardcodeados
if grep -r "password.*=" docker-compose*.yml | grep -v "\${" | grep -q .; then
    check_fail "Posibles contraseñas hardcodeadas en docker-compose"
else
    check_pass "No se encontraron contraseñas hardcodeadas"
fi

echo ""
echo "6. VERIFICANDO VOLÚMENES Y PERSISTENCIA..."
echo "----------------------------------------"

# Verificar configuración de volúmenes en producción
if [ -f "docker-compose.prod.yml" ]; then
    if grep -A 20 "volumes:" docker-compose.prod.yml | grep -q "driver_opts:"; then
        check_pass "Volúmenes de producción configurados con bind mounts"
    else
        check_warn "Volúmenes de producción usan configuración por defecto"
    fi
    
    if grep -q "backup_data:" docker-compose.prod.yml; then
        check_pass "Volumen de backup configurado"
    else
        check_fail "Volumen de backup no configurado"
    fi
fi

echo ""
echo "================================="
echo "RESUMEN DE VALIDACIÓN:"
echo "================================="
echo -e "${GREEN}✓ Verificaciones pasadas: $PASSED${NC}"
echo -e "${YELLOW}⚠ Advertencias: $WARNINGS${NC}"
echo -e "${RED}✗ Verificaciones fallidas: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡EXCELENTE! Configuración Docker lista para producción.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Configuración casi lista. Revisar advertencias.${NC}"
    exit 1
else
    echo -e "${RED}❌ Configuración NO ESTÁ LISTA. Resolver problemas críticos.${NC}"
    echo ""
    echo "PRÓXIMOS PASOS:"
    echo "1. Resolver todos los ítems marcados con ✗"
    echo "2. Revisar las advertencias ⚠"
    echo "3. Ejecutar 'docker-compose config' para validar sintaxis"
    echo "4. Volver a ejecutar este script"
    exit 2
fi