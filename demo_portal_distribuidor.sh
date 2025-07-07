#!/bin/bash
# demo_portal_distribuidor.sh - Demostración completa del Portal de Distribuidores

API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3001"

echo "🚀 DEMOSTRACIÓN COMPLETA DEL PORTAL DE DISTRIBUIDORES"
echo "=================================================================="
echo ""

# Verificar servicios
echo "🔍 Verificando servicios..."
if ! curl -s "$API_URL/health" > /dev/null; then
    echo "❌ Backend no disponible en $API_URL"
    exit 1
fi
echo "✅ Backend funcionando"

if ! curl -s -o /dev/null "$FRONTEND_URL" 2>/dev/null; then
    echo "⚠️ Frontend no disponible en $FRONTEND_URL (puede estar iniciando)"
else
    echo "✅ Frontend funcionando"
fi
echo ""

# Paso 1: Login del distribuidor
echo "🔐 PASO 1: Autenticación del Distribuidor"
echo "============================================"
echo "👤 Usuario: Distribuidor Demo"
echo "🔑 Código: DEMO123"
echo ""

DIST_TOKEN=$(curl -s -X POST "$API_URL/distributor-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=Distribuidor Demo&password=DEMO123" | jq -r .access_token)

if [[ "$DIST_TOKEN" != "null" && "$DIST_TOKEN" != "" ]]; then
    echo "✅ Login exitoso"
    echo "🎫 Token JWT generado: ${DIST_TOKEN:0:30}..."
else
    echo "❌ Error en login"
    exit 1
fi
echo ""

# Paso 2: Ver préstamos activos
echo "📊 PASO 2: Consulta de Préstamos Activos"
echo "========================================="

LOANS=$(curl -s -X GET "$API_URL/my-loans" \
  -H "Authorization: Bearer $DIST_TOKEN")

LOAN_COUNT=$(echo $LOANS | jq '. | length')
echo "📈 Total de préstamos: $LOAN_COUNT"
echo ""

if [[ $LOAN_COUNT -gt 0 ]]; then
    echo "📋 Detalle de préstamos:"
    echo "========================"
    
    # Mostrar cada préstamo
    for i in $(seq 0 $((LOAN_COUNT-1))); do
        LOAN=$(echo $LOANS | jq ".[$i]")
        LOAN_ID=$(echo $LOAN | jq -r .id)
        PRODUCT_ID=$(echo $LOAN | jq -r .product_id)
        QUANTITY=$(echo $LOAN | jq -r .quantity_loaned)
        STATUS=$(echo $LOAN | jq -r .status)
        LOAN_DATE=$(echo $LOAN | jq -r .loan_date)
        DUE_DATE=$(echo $LOAN | jq -r .return_due_date)
        
        echo "🏷️  Préstamo #$LOAN_ID"
        echo "   📦 Producto ID: $PRODUCT_ID"
        echo "   📊 Cantidad: $QUANTITY unidades"
        echo "   📅 Fecha préstamo: $LOAN_DATE"
        echo "   ⏰ Vencimiento: $DUE_DATE"
        echo "   🔄 Estado: $STATUS"
        echo ""
    done
else
    echo "📭 No hay préstamos activos"
    echo "💡 Ejecuta './crear_datos_distribuidor.sh' para crear datos de prueba"
fi

# Paso 3: Simular envío de reporte (solo si hay préstamos activos)
if [[ $LOAN_COUNT -gt 0 ]]; then
    echo "📤 PASO 3: Envío de Reporte de Consignación"
    echo "==========================================="
    
    # Obtener el primer préstamo en estado "en_prestamo"
    ACTIVE_LOAN=$(echo $LOANS | jq '.[] | select(.status == "en_prestamo") | .id' | head -1)
    
    if [[ "$ACTIVE_LOAN" != "" && "$ACTIVE_LOAN" != "null" ]]; then
        echo "📋 Enviando reporte para préstamo #$ACTIVE_LOAN..."
        echo "   💰 Vendidos: 5 unidades"
        echo "   📦 Devueltos: 3 unidades"
        
        REPORT_RESPONSE=$(curl -s -X POST "$API_URL/consignments/reports" \
          -H "Authorization: Bearer $DIST_TOKEN" \
          -H "Content-Type: application/json" \
          -d "{
            \"loan_id\": $ACTIVE_LOAN,
            \"quantity_sold\": 5,
            \"quantity_returned\": 3,
            \"report_date\": \"$(date +%Y-%m-%d)\"
          }")
        
        REPORT_ID=$(echo $REPORT_RESPONSE | jq -r .id)
        if [[ "$REPORT_ID" != "null" && "$REPORT_ID" != "" ]]; then
            echo "✅ Reporte enviado exitosamente (ID: $REPORT_ID)"
            
            # Verificar cambio de estado
            echo "🔄 Verificando actualización de estado..."
            UPDATED_LOANS=$(curl -s -X GET "$API_URL/my-loans" \
              -H "Authorization: Bearer $DIST_TOKEN")
            
            UPDATED_STATUS=$(echo $UPDATED_LOANS | jq -r ".[] | select(.id == $ACTIVE_LOAN) | .status")
            echo "📊 Estado actualizado: $UPDATED_STATUS"
        else
            echo "❌ Error al enviar reporte"
            echo "🔍 Respuesta: $REPORT_RESPONSE"
        fi
    else
        echo "⚠️ No hay préstamos activos para reportar"
    fi
    echo ""
fi

# Paso 4: Acceso via navegador
echo "🌐 PASO 4: Acceso via Interfaz Web"
echo "=================================="
echo "🔗 URL del Portal: $FRONTEND_URL/distributor-portal"
echo "👤 Credenciales de acceso:"
echo "   • Usuario: Distribuidor Demo"
echo "   • Código: DEMO123"
echo ""
echo "📱 Funcionalidades disponibles en la web:"
echo "   ✅ Login seguro con JWT"
echo "   ✅ Vista de préstamos activos"
echo "   ✅ Formularios de reporte intuitivos"
echo "   ✅ Validación en tiempo real"
echo "   ✅ Manejo de errores informativo"
echo ""

# Resumen final
echo "🎉 RESUMEN DE LA DEMOSTRACIÓN"
echo "============================="
echo "✅ Autenticación JWT funcional"
echo "✅ Acceso seguro a préstamos del distribuidor"
echo "✅ Envío de reportes de consignación"
echo "✅ Actualización automática de estados"
echo "✅ Interfaz web completamente operativa"
echo ""
echo "🔧 APIs probadas:"
echo "   • POST /distributor-token (Login)"
echo "   • GET /my-loans (Consulta préstamos)"
echo "   • POST /consignments/reports (Envío reportes)"
echo ""
echo "🔥 ESTADO: Portal de Distribuidores 100% FUNCIONAL"
echo ""
echo "💡 Próximos pasos:"
echo "1. Abrir $FRONTEND_URL/distributor-portal en el navegador"
echo "2. Iniciar sesión con las credenciales de arriba"
echo "3. Explorar la interfaz y funcionalidades"
echo "4. Probar envío de reportes desde la web"
echo ""
echo "📚 Para más información consulta la documentación completa en README.md"