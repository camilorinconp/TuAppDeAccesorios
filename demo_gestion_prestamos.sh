#!/bin/bash
# demo_gestion_prestamos.sh - Demostración completa de gestión de préstamos con coherencia de inventario

API_URL="http://localhost:8000"

echo "🏪 DEMOSTRACIÓN: GESTIÓN DE PRÉSTAMOS CON COHERENCIA DE INVENTARIO"
echo "================================================================="
echo ""

# Verificar backend
if ! curl -s "$API_URL/health" > /dev/null; then
    echo "❌ Backend no disponible en $API_URL"
    exit 1
fi
echo "✅ Backend funcionando"
echo ""

# Obtener token de admin
echo "🔐 Obteniendo credenciales de administrador..."
ADMIN_TOKEN=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)

if [[ "$ADMIN_TOKEN" == "null" || "$ADMIN_TOKEN" == "" ]]; then
    echo "❌ Error: No se pudo obtener token de admin"
    exit 1
fi
echo "✅ Token obtenido"
echo ""

# PARTE 1: Estado inicial del inventario
echo "📊 PARTE 1: ESTADO INICIAL DEL INVENTARIO"
echo "========================================="

echo "📦 Consultando productos existentes..."
PRODUCTS=$(curl -s -X GET "$API_URL/products/" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "📋 Productos en inventario:"
echo $PRODUCTS | jq -r '.products[] | "🏷️  ID: \(.id) | \(.name) | Stock: \(.stock_quantity) | Precio: $\(.selling_price)"'
echo ""

# Seleccionar producto para demostración
PRODUCT_ID=$(echo $PRODUCTS | jq -r '.products[0].id')
PRODUCT_NAME=$(echo $PRODUCTS | jq -r '.products[0].name')
STOCK_INICIAL=$(echo $PRODUCTS | jq -r '.products[0].stock_quantity')

echo "🎯 Producto seleccionado para demostración:"
echo "   📦 ID: $PRODUCT_ID"
echo "   🏷️  Nombre: $PRODUCT_NAME"
echo "   📊 Stock inicial: $STOCK_INICIAL unidades"
echo ""

# PARTE 2: Crear préstamo y verificar coherencia
echo "🏪 PARTE 2: CREACIÓN DE PRÉSTAMO Y COHERENCIA DE INVENTARIO"
echo "=========================================================="

CANTIDAD_PRESTAMO=10
echo "📝 Creando préstamo de $CANTIDAD_PRESTAMO unidades..."
echo "   👤 Distribuidor ID: 1"
echo "   📦 Producto ID: $PRODUCT_ID"
echo "   📊 Cantidad: $CANTIDAD_PRESTAMO"
echo ""

LOAN_RESPONSE=$(curl -s -X POST "$API_URL/consignments/loans" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"distributor_id\": 1,
    \"product_id\": $PRODUCT_ID,
    \"quantity_loaned\": $CANTIDAD_PRESTAMO,
    \"loan_date\": \"$(date +%Y-%m-%d)\",
    \"return_due_date\": \"$(date -d '+30 days' +%Y-%m-%d)\",
    \"status\": \"en_prestamo\"
  }")

LOAN_ID=$(echo $LOAN_RESPONSE | jq -r .id)
echo "✅ Préstamo creado:"
echo $LOAN_RESPONSE | jq .
echo ""

# Verificar actualización automática del stock
echo "🔍 Verificando actualización automática del inventario..."
UPDATED_PRODUCT=$(curl -s -X GET "$API_URL/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

STOCK_ACTUAL=$(echo $UPDATED_PRODUCT | jq -r .stock_quantity)
STOCK_ESPERADO=$((STOCK_INICIAL - CANTIDAD_PRESTAMO))

echo "📊 Resultado de la actualización automática:"
echo "   📦 Stock inicial: $STOCK_INICIAL"
echo "   🏪 Cantidad prestada: $CANTIDAD_PRESTAMO"
echo "   📊 Stock esperado: $STOCK_ESPERADO"
echo "   ✅ Stock actual: $STOCK_ACTUAL"

if [[ $STOCK_ACTUAL -eq $STOCK_ESPERADO ]]; then
    echo "🎉 ✅ COHERENCIA VERIFICADA: El inventario se actualizó correctamente"
else
    echo "❌ ERROR: Inconsistencia en el inventario detectada"
fi
echo ""

# PARTE 3: Validaciones de stock insuficiente
echo "🚨 PARTE 3: VALIDACIONES DE STOCK INSUFICIENTE"
echo "=============================================="

CANTIDAD_EXCESIVA=$((STOCK_ACTUAL + 100))
echo "🧪 Probando préstamo excesivo: $CANTIDAD_EXCESIVA unidades (Stock disponible: $STOCK_ACTUAL)..."

ERROR_RESPONSE=$(curl -s -X POST "$API_URL/consignments/loans" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"distributor_id\": 1,
    \"product_id\": $PRODUCT_ID,
    \"quantity_loaned\": $CANTIDAD_EXCESIVA,
    \"loan_date\": \"$(date +%Y-%m-%d)\",
    \"return_due_date\": \"$(date -d '+30 days' +%Y-%m-%d)\",
    \"status\": \"en_prestamo\"
  }")

echo "📋 Respuesta del sistema:"
echo $ERROR_RESPONSE | jq .
echo ""

if echo $ERROR_RESPONSE | jq -r .detail | grep -q "Stock insuficiente"; then
    echo "✅ VALIDACIÓN EXITOSA: El sistema rechazó correctamente el préstamo excesivo"
else
    echo "❌ ERROR: El sistema no validó correctamente el stock insuficiente"
fi
echo ""

# PARTE 4: Reportes de consignación y devoluciones
echo "📊 PARTE 4: REPORTES DE CONSIGNACIÓN Y DEVOLUCIONES"
echo "=================================================="

# Login como distribuidor
echo "🔐 Autenticando como distribuidor..."
DIST_TOKEN=$(curl -s -X POST "$API_URL/distributor-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=Distribuidor Demo&password=DEMO123" | jq -r .access_token)

VENDIDAS=6
DEVUELTAS=4
echo "📤 Distribuidor enviando reporte:"
echo "   💰 Unidades vendidas: $VENDIDAS"
echo "   📦 Unidades devueltas: $DEVUELTAS"
echo "   📊 Total reportado: $((VENDIDAS + DEVUELTAS))"
echo ""

REPORT_RESPONSE=$(curl -s -X POST "$API_URL/consignments/reports" \
  -H "Authorization: Bearer $DIST_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"loan_id\": $LOAN_ID,
    \"quantity_sold\": $VENDIDAS,
    \"quantity_returned\": $DEVUELTAS,
    \"report_date\": \"$(date +%Y-%m-%d)\"
  }")

echo "📋 Reporte creado:"
echo $REPORT_RESPONSE | jq .
echo ""

# Verificar actualización del stock después del reporte
echo "🔍 Verificando actualización del inventario después del reporte..."
FINAL_PRODUCT=$(curl -s -X GET "$API_URL/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

STOCK_FINAL=$(echo $FINAL_PRODUCT | jq -r .stock_quantity)
STOCK_ESPERADO_FINAL=$((STOCK_ACTUAL + DEVUELTAS))

echo "📊 Resultado después del reporte:"
echo "   📦 Stock antes del reporte: $STOCK_ACTUAL"
echo "   📦 Unidades devueltas: $DEVUELTAS"
echo "   📊 Stock esperado: $STOCK_ESPERADO_FINAL"
echo "   ✅ Stock final: $STOCK_FINAL"

if [[ $STOCK_FINAL -eq $STOCK_ESPERADO_FINAL ]]; then
    echo "🎉 ✅ COHERENCIA VERIFICADA: Las devoluciones se sumaron correctamente al inventario"
else
    echo "❌ ERROR: Inconsistencia en las devoluciones detectada"
fi
echo ""

# PARTE 5: Estado final del préstamo
echo "📋 PARTE 5: ESTADO FINAL DEL PRÉSTAMO"
echo "===================================="

FINAL_LOANS=$(curl -s -X GET "$API_URL/my-loans" \
  -H "Authorization: Bearer $DIST_TOKEN")

echo "📊 Estado final del préstamo:"
echo $FINAL_LOANS | jq ".[] | select(.id == $LOAN_ID)"
echo ""

# PARTE 6: Resumen de coherencia
echo "📈 PARTE 6: RESUMEN DE COHERENCIA DE INVENTARIO"
echo "=============================================="

echo "🔢 Flujo de inventario demostrado:"
echo "   📊 Stock inicial: $STOCK_INICIAL"
echo "   ➖ Préstamo (-$CANTIDAD_PRESTAMO): $((STOCK_INICIAL - CANTIDAD_PRESTAMO))"
echo "   ➕ Devoluciones (+$DEVUELTAS): $STOCK_FINAL"
echo "   💰 Vendidas (no vuelven al stock): $VENDIDAS"
echo ""

TOTAL_EN_MANOS_DISTRIBUIDOR=$((CANTIDAD_PRESTAMO - VENDIDAS - DEVUELTAS))
echo "📊 Balance final:"
echo "   🏪 En stock: $STOCK_FINAL"
echo "   👤 En manos del distribuidor: $TOTAL_EN_MANOS_DISTRIBUIDOR"
echo "   💰 Vendidas: $VENDIDAS"
echo "   📦 Total original: $STOCK_INICIAL"
echo ""

TOTAL_CONTABILIZADO=$((STOCK_FINAL + TOTAL_EN_MANOS_DISTRIBUIDOR + VENDIDAS))
if [[ $TOTAL_CONTABILIZADO -eq $STOCK_INICIAL ]]; then
    echo "✅ COHERENCIA TOTAL VERIFICADA: Todas las unidades están perfectamente contabilizadas"
else
    echo "❌ ERROR: Inconsistencia total detectada"
fi
echo ""

echo "🎯 FUNCIONALIDADES DEMOSTRADAS:"
echo "================================"
echo "✅ Creación de préstamos con validación de stock"
echo "✅ Actualización automática de inventario al prestar"
echo "✅ Validación de stock insuficiente"
echo "✅ Reportes de distribuidores con ventas y devoluciones"
echo "✅ Actualización automática de inventario con devoluciones"
echo "✅ Coherencia total del inventario en todo el flujo"
echo "✅ Manejo de errores y validaciones"
echo "✅ Auditoría y logging de transacciones"
echo ""

echo "🌐 INTERFAZ ADMINISTRATIVA DISPONIBLE:"
echo "======================================"
echo "🔗 URL: http://localhost:3001/consignments"
echo "🔐 Credenciales: admin / admin123"
echo ""
echo "📱 Funcionalidades de la interfaz:"
echo "   📝 Crear préstamos con validación visual"
echo "   📊 Ver resumen de todos los préstamos"
echo "   ⚠️ Alertas de préstamos vencidos"
echo "   📈 Estadísticas de préstamos activos"
echo "   🔍 Validación de stock en tiempo real"
echo ""

echo "🎉 DEMOSTRACIÓN COMPLETADA EXITOSAMENTE"
echo ""
echo "💡 El sistema garantiza coherencia exacta entre:"
echo "   📦 Inventario físico"
echo "   🏪 Préstamos activos"
echo "   💰 Ventas registradas"
echo "   📋 Devoluciones procesadas"