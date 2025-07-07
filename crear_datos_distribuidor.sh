#!/bin/bash
# crear_datos_distribuidor.sh - Script para crear datos de prueba del portal de distribuidores

# Variables
API_URL="http://localhost:8000"
echo "🚀 Iniciando creación de datos de prueba para el Portal de Distribuidores"
echo "📡 API URL: $API_URL"
echo ""

# Función para verificar si el backend está disponible
check_backend() {
    echo "🔍 Verificando disponibilidad del backend..."
    if curl -s "$API_URL/health" > /dev/null; then
        echo "✅ Backend disponible"
        return 0
    else
        echo "❌ Backend no disponible. Asegúrate de que esté ejecutándose en $API_URL"
        echo "💡 Ejecuta: python -m uvicorn backend.app.main:app --reload --port 8000"
        exit 1
    fi
}

# Verificar backend
check_backend

echo ""
echo "🔐 Paso 1: Obteniendo token de administrador..."
ADMIN_TOKEN=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)

if [[ "$ADMIN_TOKEN" == "null" || "$ADMIN_TOKEN" == "" ]]; then
    echo "❌ Error: No se pudo obtener token de admin"
    echo "💡 Verifica que el usuario admin existe con contraseña admin123"
    exit 1
fi

echo "✅ Token obtenido: ${ADMIN_TOKEN:0:20}..."
echo ""

echo "👤 Paso 2: Creando distribuidor de prueba..."
DISTRIBUTOR_RESPONSE=$(curl -s -X POST "$API_URL/distributors/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Distribuidor Demo",
    "access_code": "DEMO123",
    "contact_info": "demo@distribuidor.com"
  }')

echo "📋 Respuesta del distribuidor:"
echo $DISTRIBUTOR_RESPONSE | jq .
echo ""

echo "📦 Paso 3: Creando productos para préstamo..."
PRODUCTS=(
    '{"sku": "FUNDA001", "name": "Funda iPhone 15 Pro", "cost_price": 15000, "selling_price": 25000, "stock_quantity": 100}'
    '{"sku": "PROTECTOR001", "name": "Protector de Pantalla Samsung S24", "cost_price": 8000, "selling_price": 15000, "stock_quantity": 200}'
    '{"sku": "CABLE001", "name": "Cable USB-C Premium", "cost_price": 12000, "selling_price": 20000, "stock_quantity": 150}'
)

PRODUCT_IDS=()
for i in "${!PRODUCTS[@]}"; do
    echo "📱 Creando producto $((i+1))/3..."
    PRODUCT_RESPONSE=$(curl -s -X POST "$API_URL/products/" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d "${PRODUCTS[$i]}")
    
    PRODUCT_ID=$(echo $PRODUCT_RESPONSE | jq -r .id)
    PRODUCT_IDS+=($PRODUCT_ID)
    echo "✅ Producto creado con ID: $PRODUCT_ID"
done
echo ""

echo "🏪 Paso 4: Creando préstamos de consignación..."
for i in "${!PRODUCT_IDS[@]}"; do
    product_id=${PRODUCT_IDS[$i]}
    quantity_loaned=$((15 + i * 5))
    
    echo "📋 Creando préstamo para producto ID $product_id (cantidad: $quantity_loaned)..."
    LOAN_RESPONSE=$(curl -s -X POST "$API_URL/consignments/loans" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"distributor_id\": 1,
            \"product_id\": $product_id,
            \"quantity_loaned\": $quantity_loaned,
            \"loan_date\": \"$(date +%Y-%m-%d)\",
            \"return_due_date\": \"$(date -d '+30 days' +%Y-%m-%d)\",
            \"status\": \"en_prestamo\"
        }")
    
    LOAN_ID=$(echo $LOAN_RESPONSE | jq -r .id)
    echo "✅ Préstamo creado con ID: $LOAN_ID"
done
echo ""

echo "🧪 Paso 5: Verificando funcionamiento del portal..."
echo "🔐 Probando login del distribuidor..."
DIST_TOKEN=$(curl -s -X POST "$API_URL/distributor-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=Distribuidor Demo&password=DEMO123" | jq -r .access_token)

if [[ "$DIST_TOKEN" != "null" && "$DIST_TOKEN" != "" ]]; then
    echo "✅ Login del distribuidor exitoso"
    
    echo "📊 Probando acceso a préstamos..."
    LOANS=$(curl -s -X GET "$API_URL/my-loans" \
        -H "Authorization: Bearer $DIST_TOKEN")
    
    LOAN_COUNT=$(echo $LOANS | jq '. | length')
    echo "📈 Préstamos encontrados: $LOAN_COUNT"
    
    if [[ $LOAN_COUNT -gt 0 ]]; then
        echo "✅ Acceso a préstamos exitoso"
        echo ""
        echo "📋 Resumen de préstamos:"
        echo $LOANS | jq -r '.[] | "🏷️  \(.product.name) - Cantidad: \(.quantity_loaned) - Estado: \(.status)"'
    else
        echo "⚠️ No se encontraron préstamos"
    fi
else
    echo "❌ Error en login del distribuidor"
fi

echo ""
echo "🎉 ¡Datos de prueba creados exitosamente!"
echo ""
echo "📱 Información de acceso al Portal de Distribuidores:"
echo "🌐 URL Frontend: http://localhost:3001/distributor-portal"
echo "🔐 Usuario: Distribuidor Demo"
echo "🔑 Código: DEMO123"
echo ""
echo "📊 Endpoints de API disponibles:"
echo "• POST /distributor-token - Login"
echo "• GET /my-loans - Ver préstamos"
echo "• POST /consignments/reports - Enviar reportes"
echo ""
echo "💡 Próximos pasos:"
echo "1. Abrir http://localhost:3001/distributor-portal"
echo "2. Iniciar sesión con las credenciales de arriba"
echo "3. Ver los préstamos creados automáticamente"
echo "4. Probar enviar reportes de ventas/devoluciones"
echo ""
echo "🔧 Para reiniciar los datos, ejecuta este script nuevamente"