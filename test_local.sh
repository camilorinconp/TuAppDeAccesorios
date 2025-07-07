#!/bin/bash

echo "🧪 SCRIPT DE PRUEBAS LOCALES - TuAppDeAccesorios"
echo "=================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para mostrar resultados
show_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# 1. Verificar que los servicios estén corriendo
echo "1. 🔍 VERIFICANDO ESTADO DE SERVICIOS"
echo "------------------------------------"
docker-compose ps
echo ""

# 2. Health Checks
echo "2. 🏥 HEALTH CHECKS"
echo "------------------"

# Backend Health
BACKEND_HEALTH=$(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null)
if [ "$BACKEND_HEALTH" = "healthy" ]; then
    show_result 0 "Backend API está saludable"
else
    show_result 1 "Backend API no responde correctamente"
fi

# Frontend
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)
if [ "$FRONTEND_STATUS" = "200" ]; then
    show_result 0 "Frontend está accesible"
else
    show_result 1 "Frontend no está accesible"
fi

echo ""

# 3. Pruebas de Base de Datos
echo "3. 🗄️  PRUEBAS DE BASE DE DATOS"
echo "------------------------------"

# Verificar que PostgreSQL esté accesible
docker-compose exec -T db pg_isready -U tuappuser -d tuappdb > /dev/null 2>&1
show_result $? "PostgreSQL está respondiendo"

# Contar tablas
TABLE_COUNT=$(docker-compose exec -T db psql -U tuappuser -d tuappdb -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d '[:space:]')
echo "📊 Tablas en la base de datos: $TABLE_COUNT"

# Contar usuarios
USER_COUNT=$(docker-compose exec -T db psql -U tuappuser -d tuappdb -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d '[:space:]')
echo "👥 Usuarios registrados: $USER_COUNT"

echo ""

# 4. Pruebas de Autenticación
echo "4. 🔐 PRUEBAS DE AUTENTICACIÓN"
echo "-----------------------------"

# Intentar login
echo "Probando login con admin/admin123..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r .access_token 2>/dev/null)

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    show_result 0 "Login exitoso - Token generado"
    echo "🎫 Token: ${TOKEN:0:50}..."
    
    # Probar endpoint autenticado
    USER_DATA=$(curl -s -X GET "http://localhost:8000/users/" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$USER_DATA" | jq . > /dev/null 2>&1; then
        show_result 0 "Acceso autenticado a endpoints protegidos"
        echo "👤 Usuario actual: $(echo "$USER_DATA" | jq -r '.[0].username')"
    else
        show_result 1 "Error en acceso autenticado"
    fi
else
    show_result 1 "Error en login"
    echo "⚠️  Respuesta: $TOKEN_RESPONSE"
fi

echo ""

# 5. Pruebas de API - Productos
echo "5. 📦 PRUEBAS DE API - PRODUCTOS"
echo "-------------------------------"

# Contar productos
PRODUCT_COUNT=$(curl -s http://localhost:8000/products/ | jq -r .total 2>/dev/null)
echo "📊 Productos en la base de datos: $PRODUCT_COUNT"

# Listar productos
echo ""
echo "📋 Lista de productos:"
curl -s http://localhost:8000/products/ | jq -r '.products[] | "- \(.sku): \(.name) - $\(.selling_price) (Stock: \(.stock_quantity))"' 2>/dev/null

echo ""

# 6. Pruebas de Redis
echo "6. 🔄 PRUEBAS DE REDIS (CACHE)"
echo "-----------------------------"

# Verificar que Redis esté funcionando
docker-compose exec -T redis redis-cli ping > /dev/null 2>&1
show_result $? "Redis está respondiendo"

# Verificar estadísticas de cache
CACHE_STATS=$(curl -s http://localhost:8000/health | jq .metrics_summary.cache 2>/dev/null)
if [ -n "$CACHE_STATS" ]; then
    echo "📊 Estadísticas de cache:"
    echo "$CACHE_STATS" | jq .
fi

echo ""

# 7. URLs de Acceso
echo "7. 🌐 URLS DE ACCESO AL SISTEMA"
echo "------------------------------"
echo "Frontend:              http://localhost:3001"
echo "API Documentation:     http://localhost:8000/docs"
echo "API Health Check:      http://localhost:8000/health"
echo "API Products:          http://localhost:8000/products/"
echo ""

# 8. Comandos Útiles
echo "8. 🛠️  COMANDOS ÚTILES PARA DESARROLLO"
echo "------------------------------------"
echo "Ver logs del backend:   docker-compose logs backend -f"
echo "Ver logs del frontend:  docker-compose logs frontend -f"
echo "Acceder a PostgreSQL:   docker-compose exec db psql -U tuappuser -d tuappdb"
echo "Acceder a Redis:        docker-compose exec redis redis-cli"
echo "Reiniciar servicios:    docker-compose restart"
echo ""

echo "🎉 PRUEBAS COMPLETADAS"
echo "====================="
echo ""
echo "Para más pruebas manuales, puedes:"
echo "1. Abrir http://localhost:3001 en tu navegador"
echo "2. Usar http://localhost:8000/docs para probar la API interactivamente"
echo "3. Ejecutar este script nuevamente con: ./test_local.sh"