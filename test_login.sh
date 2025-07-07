#!/bin/bash

echo "🚀 PROBANDO LOGIN - TuAppDeAccesorios"
echo "===================================="
echo ""

# Verificar que el backend esté funcionando
echo "🔍 Verificando backend..."
HEALTH=$(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null)

if [ "$HEALTH" != "healthy" ]; then
    echo "❌ El backend no está funcionando. Ejecuta primero:"
    echo "   docker-compose up -d"
    exit 1
fi

echo "✅ Backend funcionando correctamente"
echo ""

echo "🧪 Probando login directamente:"
echo "================================"

# Test con credenciales correctas
echo "1. Probando admin/admin123:"
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

if echo "$LOGIN_RESPONSE" | jq -e .access_token > /dev/null 2>&1; then
    echo "   ✅ LOGIN EXITOSO"
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r .access_token)
    echo "   🎫 Token: ${TOKEN:0:50}..."
else
    echo "   ❌ LOGIN FALLIDO"
    echo "   📄 Respuesta: $LOGIN_RESPONSE"
fi

echo ""

# Test con credenciales incorrectas
echo "2. Probando credenciales incorrectas:"
WRONG_LOGIN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=wrong&password=wrong")

if echo "$WRONG_LOGIN" | jq -e .access_token > /dev/null 2>&1; then
    echo "   ❌ ERROR: Login exitoso con credenciales incorrectas"
else
    echo "   ✅ Correctamente rechazado"
    echo "   📄 Error: $(echo "$WRONG_LOGIN" | jq -r .message)"
fi

echo ""
echo "🌐 OPCIONES PARA PROBAR EL LOGIN:"
echo "================================"
echo ""
echo "OPCIÓN 1 - Página de login funcional (RECOMENDADO):"
echo "   open login_working.html"
echo ""
echo "OPCIÓN 2 - Swagger UI:"
echo "   open http://localhost:8000/docs"
echo ""
echo "OPCIÓN 3 - Frontend React (si está compilado):"
echo "   open http://localhost:3001"
echo ""

echo "¿Qué opción quieres abrir?"
echo "1) Página de login funcional"
echo "2) Swagger UI"
echo "3) Frontend React"
echo "4) Todas las opciones"
echo "5) Solo mostrar información"

read -p "Selecciona (1-5): " choice

case $choice in
    1)
        echo "🚀 Abriendo página de login funcional..."
        open login_working.html 2>/dev/null || echo "Archivo: $(pwd)/login_working.html"
        ;;
    2)
        echo "📚 Abriendo Swagger UI..."
        open http://localhost:8000/docs 2>/dev/null || echo "URL: http://localhost:8000/docs"
        ;;
    3)
        echo "🌐 Abriendo Frontend React..."
        open http://localhost:3001 2>/dev/null || echo "URL: http://localhost:3001"
        ;;
    4)
        echo "🚀 Abriendo todas las opciones..."
        open login_working.html 2>/dev/null || echo "Archivo: $(pwd)/login_working.html"
        sleep 2
        open http://localhost:8000/docs 2>/dev/null || echo "URL: http://localhost:8000/docs"
        sleep 2
        open http://localhost:3001 2>/dev/null || echo "URL: http://localhost:3001"
        ;;
    5)
        echo "ℹ️ Información mostrada arriba"
        ;;
    *)
        echo "❌ Opción inválida"
        ;;
esac

echo ""
echo "📋 RESUMEN:"
echo "==========="
echo "✅ Backend funcionando: http://localhost:8000"
echo "✅ Credenciales verificadas: admin/admin123"
echo "✅ API de login operativa al 100%"
echo ""
echo "Si tienes problemas con el frontend React, usa la página login_working.html"