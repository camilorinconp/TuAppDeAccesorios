#!/bin/bash
# guia_acceso_prestamos.sh - Guía paso a paso para acceder a la gestión de préstamos

echo "🏪 GUÍA COMPLETA: ACCESO A LA GESTIÓN DE PRÉSTAMOS"
echo "================================================="
echo ""

# Verificar servicios
echo "🔍 PASO 1: Verificación de Servicios"
echo "===================================="
echo ""

if curl -s "http://localhost:8000/health" > /dev/null; then
    echo "✅ Backend funcionando en http://localhost:8000"
else
    echo "❌ Backend NO disponible"
    echo "💡 Para iniciar backend: python -m uvicorn backend.app.main:app --reload --port 8000"
    exit 1
fi

if curl -s -o /dev/null "http://localhost:3001" 2>/dev/null; then
    echo "✅ Frontend funcionando en http://localhost:3001"
else
    echo "❌ Frontend NO disponible"
    echo "💡 Para iniciar frontend: cd frontend && npm start"
    exit 1
fi
echo ""

# Verificar datos de prueba
echo "📊 PASO 2: Verificación de Datos de Prueba"
echo "=========================================="
echo ""

ADMIN_TOKEN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)

if [[ "$ADMIN_TOKEN" == "null" || "$ADMIN_TOKEN" == "" ]]; then
    echo "❌ Error: No se pudo obtener token de admin"
    exit 1
fi

# Verificar distribuidores
DISTRIBUTORS=$(curl -s -X GET "http://localhost:8000/distributors/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '. | length')

echo "👥 Distribuidores disponibles: $DISTRIBUTORS"
if [[ $DISTRIBUTORS -eq 0 ]]; then
    echo "⚠️  No hay distribuidores. Ejecuta './crear_datos_distribuidor.sh' para crear datos"
fi

# Verificar productos
PRODUCTS=$(curl -s -X GET "http://localhost:8000/products/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.products | length')

echo "📦 Productos disponibles: $PRODUCTS"
if [[ $PRODUCTS -eq 0 ]]; then
    echo "⚠️  No hay productos. Crea algunos desde http://localhost:3001/inventory"
fi

# Verificar préstamos existentes
LOANS=$(curl -s -X GET "http://localhost:8000/consignments/loans" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '. | length')

echo "🏪 Préstamos existentes: $LOANS"
echo ""

# Instrucciones de acceso
echo "🌐 PASO 3: Acceso a la Interfaz Web"
echo "=================================="
echo ""
echo "1️⃣ Abrir navegador en: http://localhost:3001"
echo ""
echo "2️⃣ Iniciar sesión con credenciales de administrador:"
echo "   👤 Usuario: admin"
echo "   🔑 Contraseña: admin123"
echo ""
echo "3️⃣ En el Dashboard, hacer clic en:"
echo "   🏪 'Gestión de Préstamos'"
echo ""
echo "4️⃣ O acceder directamente a:"
echo "   🔗 http://localhost:3001/consignments"
echo ""

# Funcionalidades disponibles
echo "⚙️  PASO 4: Funcionalidades Disponibles"
echo "======================================"
echo ""
echo "📝 CREAR PRÉSTAMOS:"
echo "   • Botón verde '+ Crear Préstamo'"
echo "   • Seleccionar distribuidor de la lista"
echo "   • Seleccionar producto (muestra stock disponible)"
echo "   • Ingresar cantidad (validación en tiempo real)"
echo "   • Fechas de préstamo y vencimiento"
echo "   • Vista previa del impacto en el stock"
echo ""
echo "📊 VER PRÉSTAMOS:"
echo "   • Lista completa con todos los detalles"
echo "   • Estados visuales (En Préstamo, Devuelto, Vencido)"
echo "   • Información de distribuidor y producto"
echo "   • Alertas de vencimiento"
echo "   • Días restantes hasta vencimiento"
echo ""
echo "📈 ESTADÍSTICAS:"
echo "   • Total de préstamos"
echo "   • Préstamos activos"
echo "   • Próximos a vencer (7 días)"
echo "   • Préstamos vencidos"
echo ""

# Casos de uso prácticos
echo "🎯 PASO 5: Casos de Uso Prácticos"
echo "================================="
echo ""
echo "💡 ESCENARIO 1: Crear primer préstamo"
echo "   1. Clic en '+ Crear Préstamo'"
echo "   2. Seleccionar 'Distribuidor Demo'"
echo "   3. Elegir un producto con stock > 0"
echo "   4. Ingresar cantidad menor al stock"
echo "   5. Observar cálculo automático del stock resultante"
echo "   6. Clic en 'Crear Préstamo'"
echo ""
echo "💡 ESCENARIO 2: Validar stock insuficiente"
echo "   1. Intentar crear préstamo con cantidad > stock"
echo "   2. Observar validación automática"
echo "   3. Sistema previene el préstamo excesivo"
echo ""
echo "💡 ESCENARIO 3: Monitorear préstamos"
echo "   1. Ver lista de préstamos activos"
echo "   2. Identificar préstamos próximos a vencer"
echo "   3. Seguimiento de distribuidores"
echo ""

# Verificación de coherencia
echo "🔍 PASO 6: Verificación de Coherencia"
echo "===================================="
echo ""

if [[ $PRODUCTS -gt 0 ]]; then
    PRODUCT_ID=$(curl -s -X GET "http://localhost:8000/products/" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.products[0].id')
    
    PRODUCT_NAME=$(curl -s -X GET "http://localhost:8000/products/" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.products[0].name')
    
    CURRENT_STOCK=$(curl -s -X GET "http://localhost:8000/products/$PRODUCT_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.stock_quantity')
    
    ACTIVE_LOANS=$(curl -s -X GET "http://localhost:8000/consignments/loans" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | \
      jq "[.[] | select(.product_id == $PRODUCT_ID and .status == \"en_prestamo\")] | map(.quantity_loaned) | add // 0")
    
    echo "🔢 Ejemplo de coherencia con '$PRODUCT_NAME':"
    echo "   📦 Stock actual en tienda: $CURRENT_STOCK"
    echo "   🏪 En préstamos activos: $ACTIVE_LOANS"
    echo "   📊 Total contabilizado: $((CURRENT_STOCK + ACTIVE_LOANS))"
    echo ""
fi

# URLs importantes
echo "🔗 PASO 7: Enlaces Importantes"
echo "=============================="
echo ""
echo "🌐 Interfaz Principal:"
echo "   Dashboard: http://localhost:3001/dashboard"
echo "   Gestión de Préstamos: http://localhost:3001/consignments"
echo "   Inventario: http://localhost:3001/inventory"
echo ""
echo "👤 Portal de Distribuidores:"
echo "   URL: http://localhost:3001/distributor-portal"
echo "   Usuario: Distribuidor Demo"
echo "   Código: DEMO123"
echo ""
echo "📚 API Documentation:"
echo "   Swagger UI: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""

# Solución de problemas comunes
echo "🛠️  PASO 8: Solución de Problemas Comunes"
echo "======================================="
echo ""
echo "❓ Si no aparecen distribuidores o productos:"
echo "   ./crear_datos_distribuidor.sh"
echo ""
echo "❓ Si hay errores de autenticación:"
echo "   Verificar credenciales: admin / admin123"
echo ""
echo "❓ Si no cargan los préstamos:"
echo "   Verificar que el backend esté en puerto 8000"
echo "   curl http://localhost:8000/health"
echo ""
echo "❓ Si aparecen errores 'Failed to fetch':"
echo "   Verificar CORS entre frontend (3001) y backend (8000)"
echo ""

echo "🎉 GUÍA COMPLETADA"
echo "=================="
echo ""
echo "✨ Todo está listo para usar la gestión de préstamos"
echo "🔗 Accede ahora: http://localhost:3001/consignments"
echo ""
echo "📖 Para más información consulta:"
echo "   README.md - Sección 'Gestión de Préstamos con Coherencia de Inventario'"
echo "   ./demo_gestion_prestamos.sh - Demostración completa"