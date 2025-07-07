#!/bin/bash

echo "🚀 INICIANDO INTERFAZ SIMPLE DE TuAppDeAccesorios"
echo "=============================================="
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

# Verificar si Python está disponible
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python no encontrado. Instala Python o abre el archivo directamente:"
    echo "   open simple_login.html"
    exit 1
fi

echo "🌐 Iniciando servidor web simple..."
echo "📁 Sirviendo desde: $(pwd)"
echo ""
echo "🎯 URLs de acceso:"
echo "   Interfaz Simple:    http://localhost:8080"
echo "   Swagger UI:         http://localhost:8000/docs"
echo "   Frontend React:     http://localhost:3001"
echo ""
echo "📋 Credenciales:"
echo "   Usuario: admin"
echo "   Contraseña: admin123"
echo ""
echo "💡 Presiona Ctrl+C para detener el servidor"
echo ""

# Abrir automáticamente en el navegador (si está disponible)
if command -v open &> /dev/null; then
    sleep 2 && open http://localhost:8080 &
elif command -v xdg-open &> /dev/null; then
    sleep 2 && xdg-open http://localhost:8080 &
fi

# Iniciar servidor HTTP simple de Python
$PYTHON_CMD -m http.server 8080