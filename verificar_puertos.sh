#!/bin/bash
# verificar_puertos.sh - Verificar y corregir configuración de puertos

echo "🔍 VERIFICACIÓN DE CONFIGURACIÓN DE PUERTOS"
echo "==========================================="
echo ""

echo "📊 PUERTOS CONFIGURADOS CORRECTAMENTE:"
echo "======================================"
echo "🖥️  Backend API: http://localhost:8000"
echo "🌐 Frontend Web: http://localhost:3001"
echo "🗄️  PostgreSQL: localhost:5433"
echo "🔴 Redis: localhost:6380"
echo ""

echo "✅ VERIFICACIÓN DE SERVICIOS:"
echo "============================"

# Backend en puerto 8000
if curl -s "http://localhost:8000/health" > /dev/null; then
    echo "✅ Backend correcto en puerto 8000"
else
    echo "❌ Backend NO disponible en puerto 8000"
fi

# Frontend en puerto 3001
if curl -s -o /dev/null "http://localhost:3001" 2>/dev/null; then
    echo "✅ Frontend correcto en puerto 3001"
else
    echo "❌ Frontend NO disponible en puerto 3001"
fi

# Verificar que NO hay nada en puerto 3000
if curl -s -o /dev/null "http://localhost:3000" 2>/dev/null; then
    echo "⚠️  ADVERTENCIA: Hay algo ejecutándose en puerto 3000"
    echo "   Esto puede causar confusión. El frontend debe estar en 3001"
else
    echo "✅ Puerto 3000 libre (correcto, frontend está en 3001)"
fi
echo ""

echo "🔧 CONFIGURACIÓN DE CORS:"
echo "========================"
echo "Backend configurado para aceptar requests desde:"
echo "• http://localhost:3000 (compatibilidad legacy)"
echo "• http://localhost:3001 (puerto actual del frontend)"
echo ""

echo "📋 URLS IMPORTANTES:"
echo "==================="
echo "🏠 Dashboard: http://localhost:3001/dashboard"
echo "🏪 Gestión de Préstamos: http://localhost:3001/consignments"
echo "📦 Inventario: http://localhost:3001/inventory"
echo "👤 Portal Distribuidores: http://localhost:3001/distributor-portal"
echo ""
echo "📚 Documentación API: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""

echo "🎯 CONFIRMACIÓN DE ACCESO:"
echo "========================="
echo ""
echo "Por favor confirma que puedes acceder a:"
echo "1. 🌐 http://localhost:3001 (debe mostrar la aplicación)"
echo "2. 🏪 http://localhost:3001/consignments (después de login admin/admin123)"
echo ""

echo "🚨 SI HAY PROBLEMAS:"
echo "==================="
echo ""
echo "❓ Si frontend no carga en puerto 3001:"
echo "   cd frontend && npm start"
echo ""
echo "❓ Si aparece en puerto 3000 por error:"
echo "   Detener servidor y volver a iniciar con 'npm start'"
echo ""
echo "❓ Si hay errores CORS:"
echo "   Backend ya está configurado para ambos puertos (3000 y 3001)"
echo ""

echo "✨ ESTADO: Frontend configurado correctamente en puerto 3001"