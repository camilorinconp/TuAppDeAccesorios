#!/bin/bash

echo "🔗 PRUEBAS ESPECÍFICAS DE API - TuAppDeAccesorios"
echo "================================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para mostrar requests
show_request() {
    echo -e "${BLUE}📤 $1${NC}"
}

# Función para mostrar respuestas
show_response() {
    echo -e "${GREEN}📥 Respuesta:${NC}"
    echo "$1" | jq . 2>/dev/null || echo "$1"
    echo ""
}

# Obtener token
echo "🔐 Obteniendo token de acceso..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r .access_token 2>/dev/null)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Error obteniendo token${NC}"
    echo "Respuesta: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Token obtenido exitosamente${NC}"
echo ""

# === PRUEBAS DE PRODUCTOS ===
echo "📦 PRUEBAS DE PRODUCTOS"
echo "======================"

# 1. Listar productos
show_request "GET /products/ - Listar todos los productos"
PRODUCTS_RESPONSE=$(curl -s -X GET "http://localhost:8000/products/")
show_response "$PRODUCTS_RESPONSE"

# 2. Crear producto nuevo
show_request "POST /products/ - Crear producto nuevo"
NEW_PRODUCT=$(curl -s -X POST "http://localhost:8000/products/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "CABLE001",
    "name": "Cable USB-C a Lightning",
    "description": "Cable de carga rápida 1 metro",
    "cost_price": 5.00,
    "selling_price": 12.00,
    "stock_quantity": 25
  }')
show_response "$NEW_PRODUCT"

# 3. Obtener producto por ID
if echo "$NEW_PRODUCT" | jq .id > /dev/null 2>&1; then
    PRODUCT_ID=$(echo "$NEW_PRODUCT" | jq -r .id)
    show_request "GET /products/$PRODUCT_ID - Obtener producto específico"
    PRODUCT_DETAIL=$(curl -s -X GET "http://localhost:8000/products/$PRODUCT_ID")
    show_response "$PRODUCT_DETAIL"
fi

# === PRUEBAS DE USUARIOS ===
echo "👥 PRUEBAS DE USUARIOS"
echo "===================="

# 1. Listar usuarios
show_request "GET /users/ - Listar usuarios (requiere autenticación)"
USERS_RESPONSE=$(curl -s -X GET "http://localhost:8000/users/" \
  -H "Authorization: Bearer $TOKEN")
show_response "$USERS_RESPONSE"

# 2. Crear usuario nuevo
show_request "POST /users/ - Crear usuario nuevo"
NEW_USER=$(curl -s -X POST "http://localhost:8000/users/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123",
    "role": "sales_staff"
  }')
show_response "$NEW_USER"

# === PRUEBAS DE MÉTRICAS ===
echo "📊 PRUEBAS DE MÉTRICAS"
echo "===================="

show_request "GET /admin/metrics/summary - Resumen de métricas del sistema"
METRICS_RESPONSE=$(curl -s -X GET "http://localhost:8000/admin/metrics/summary" \
  -H "Authorization: Bearer $TOKEN")
show_response "$METRICS_RESPONSE"

# === PRUEBAS DE HEALTH CHECK ===
echo "🏥 PRUEBAS DE SALUD DEL SISTEMA"
echo "=============================="

show_request "GET /health - Estado de salud del sistema"
HEALTH_RESPONSE=$(curl -s -X GET "http://localhost:8000/health")
show_response "$HEALTH_RESPONSE"

show_request "GET /admin/metrics/system/health - Health check detallado"
DETAILED_HEALTH=$(curl -s -X GET "http://localhost:8000/admin/metrics/system/health")
show_response "$DETAILED_HEALTH"

# === PRUEBAS DE ERRORES ===
echo "❌ PRUEBAS DE MANEJO DE ERRORES"
echo "==============================="

show_request "GET /products/999999 - Producto inexistente"
ERROR_RESPONSE=$(curl -s -X GET "http://localhost:8000/products/999999")
show_response "$ERROR_RESPONSE"

show_request "POST /products/ - Sin autenticación"
NO_AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/products/" \
  -H "Content-Type: application/json" \
  -d '{"sku": "TEST", "name": "Test"}')
show_response "$NO_AUTH_RESPONSE"

echo ""
echo "🎉 PRUEBAS DE API COMPLETADAS"
echo "============================"
echo ""
echo "💡 Consejos para más pruebas:"
echo "1. Visita http://localhost:8000/docs para interfaz interactiva"
echo "2. Usa Postman o curl para pruebas personalizadas"
echo "3. Revisa los logs con: docker-compose logs backend -f"