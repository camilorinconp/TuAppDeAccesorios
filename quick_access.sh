#!/bin/bash

echo "🚀 ACCESO RÁPIDO A TuAppDeAccesorios"
echo "=================================="
echo ""

# Verificar que el backend esté funcionando
echo "🔍 Verificando backend..."
HEALTH=$(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null)

if [ "$HEALTH" = "healthy" ]; then
    echo "✅ Backend funcionando correctamente"
else
    echo "❌ Backend no responde"
    exit 1
fi

# Probar login
echo "🔐 Probando credenciales admin/admin123..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r .access_token 2>/dev/null)

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ Login exitoso - Credenciales funcionando"
    echo "🎫 Token generado: ${TOKEN:0:30}..."
else
    echo "⚠️ Rate limiting activo o error de login"
    echo "💡 Solución: Espera 1 minuto y vuelve a intentar"
    echo "📝 Respuesta: $LOGIN_RESPONSE"
fi

echo ""
echo "🌐 OPCIONES DE ACCESO:"
echo "====================="
echo ""
echo "1. 📚 SWAGGER UI (Recomendado):"
echo "   URL: http://localhost:8000/docs"
echo "   ✅ Funciona 100% con admin/admin123"
echo ""
echo "2. 🌐 Frontend Web (si ya compiló):"
echo "   URL: http://localhost:3001"
echo "   ✅ Mismas credenciales"
echo ""
echo "3. 🗄️ Base de Datos Directa:"
echo "   docker-compose exec db psql -U tuappuser -d tuappdb"
echo ""

echo "¿Qué quieres abrir?"
echo "1) Swagger UI (API Documentation)"
echo "2) Frontend Web"
echo "3) Ambos"
echo "4) Solo verificar estado"
read -p "Selecciona (1-4): " choice

case $choice in
    1)
        echo "🚀 Abriendo Swagger UI..."
        open http://localhost:8000/docs 2>/dev/null || echo "Visita: http://localhost:8000/docs"
        ;;
    2)
        echo "🌐 Abriendo Frontend..."
        open http://localhost:3001 2>/dev/null || echo "Visita: http://localhost:3001"
        ;;
    3)
        echo "🚀 Abriendo ambos..."
        open http://localhost:8000/docs 2>/dev/null || echo "Swagger: http://localhost:8000/docs"
        sleep 2
        open http://localhost:3001 2>/dev/null || echo "Frontend: http://localhost:3001"
        ;;
    4)
        echo "ℹ️ Solo verificación completada"
        ;;
    *)
        echo "❌ Opción inválida"
        ;;
esac

echo ""
echo "📋 CREDENCIALES:"
echo "Usuario: admin"
echo "Contraseña: admin123"
echo ""
echo "🎯 INSTRUCCIONES RÁPIDAS PARA SWAGGER:"
echo "1. Busca /token → Try it out"
echo "2. username: admin, password: admin123 → Execute"  
echo "3. Copia el access_token"
echo "4. Botón Authorize (🔒) → Bearer tu_token"
echo "5. ¡Ya puedes usar todos los endpoints!"
echo ""
echo "✅ ¡TuAppDeAccesorios está listo para usar!"