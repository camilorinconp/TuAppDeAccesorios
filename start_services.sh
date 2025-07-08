#!/bin/bash

echo "🚀 Iniciando servicios de TuAppDeAccesorios"

# Limpiar procesos previos
echo "🧹 Limpiando procesos previos..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true

# Esperar un momento
sleep 2

# Iniciar solo PostgreSQL y Redis con Docker
echo "🐳 Iniciando PostgreSQL y Redis..."
docker-compose up -d db redis

# Esperar a que estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

# Verificar estado
echo "📊 Verificando estado de servicios Docker..."
docker-compose ps

# Iniciar backend localmente
echo "🔧 Iniciando backend en puerto 8000..."
cd backend
export DATABASE_URL="postgresql://tuapp_user:TjsgqypkqFJ1xS2024@localhost:5432/tuapp_db"
export REDIS_URL="redis://:UwWHHhZehbZg5h2024@localhost:6379/0"
export SECRET_KEY="plp3gDRyzZWcYZYAMRNYb2TYkVnKM-bT3oi6ZT-UZJI"
export ENVIRONMENT="development"

# Iniciar backend en background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend iniciado con PID: $BACKEND_PID"

cd ..

# Esperar a que el backend esté listo
echo "⏳ Esperando a que el backend esté listo..."
sleep 5

# Probar backend
echo "🔍 Probando backend..."
curl -s http://localhost:8000/health || echo "❌ Backend no responde"

# Iniciar frontend localmente
echo "⚛️ Iniciando frontend en puerto 3001..."
cd frontend

# Configurar variables de entorno para el frontend
export REACT_APP_API_URL="http://localhost:8000"
export PORT=3001
export GENERATE_SOURCEMAP=false
export TSC_COMPILE_ON_ERROR=true

# Iniciar frontend en background
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend iniciado con PID: $FRONTEND_PID"

cd ..

echo "🎉 Servicios iniciados:"
echo "  🔧 Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo "  ⚛️ Frontend: http://localhost:3001 (PID: $FRONTEND_PID)"
echo "  🐳 PostgreSQL: localhost:5432"
echo "  🐳 Redis: localhost:6379"
echo ""
echo "📊 Para ver logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "⚠️ Para detener:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  docker-compose stop"

# Guardar PIDs para fácil acceso
echo "$BACKEND_PID $FRONTEND_PID" > .service_pids