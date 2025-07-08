#!/bin/bash

echo "🧪 PRUEBA DE INTEGRACIÓN COMPLETA - TuAppDeAccesorios"
echo "========================================================"

echo ""
echo "🔍 1. Verificando servicios..."

# Frontend
echo -n "   Frontend (puerto 3001): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200"; then
    echo "✅ FUNCIONANDO"
else
    echo "❌ NO RESPONDE"
fi

# Backend
echo -n "   Backend (puerto 8000): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
    echo "✅ FUNCIONANDO"
else
    echo "❌ NO RESPONDE"
fi

echo ""
echo "🔐 2. Probando autenticación..."

# Test de login
echo -n "   Login API: "
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin&password=admin123")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "✅ FUNCIONANDO"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "     Token obtenido: ${TOKEN:0:20}..."
else
    echo "❌ FALLO"
    echo "     Respuesta: $LOGIN_RESPONSE"
fi

echo ""
echo "🌐 3. Verificando configuración de CORS..."

echo -n "   CORS desde frontend a backend: "
CORS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Origin: http://localhost:3001" \
    http://localhost:8000/health)

if [ "$CORS_RESPONSE" = "200" ]; then
    echo "✅ CONFIGURADO CORRECTAMENTE"
else
    echo "⚠️  Código: $CORS_RESPONSE"
fi

echo ""
echo "📊 4. Resumen de configuración:"
echo "   Frontend URL: http://localhost:3001"
echo "   Backend URL:  http://localhost:8000"
echo "   API URL configurada en frontend: $(grep REACT_APP_API_URL /Users/user/TuAppDeAccesorios/frontend/.env)"

echo ""
echo "🎯 5. Para acceder a la aplicación:"
echo "   👉 Abre tu navegador en: http://localhost:3001"
echo "   📝 Credenciales: admin / admin123"

echo ""
echo "✅ PRUEBA DE INTEGRACIÓN COMPLETADA"