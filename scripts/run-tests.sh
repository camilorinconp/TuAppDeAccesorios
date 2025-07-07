#!/bin/bash

# Script para ejecutar todos los tests
# Uso: ./scripts/run-tests.sh [tipo]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

TEST_TYPE=${1:-all}

log_info "Ejecutando tests para TuAppDeAccesorios"
log_info "Tipo de test: ${TEST_TYPE}"

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    log_error "Debe ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Función para ejecutar tests del backend
run_backend_tests() {
    log_step "Ejecutando tests del backend..."
    
    cd backend
    
    # Instalar dependencias si es necesario
    if [ ! -d "venv" ]; then
        log_info "Creando entorno virtual para tests..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio httpx
    else
        source venv/bin/activate
    fi
    
    # Ejecutar tests con coverage
    log_info "Ejecutando tests unitarios..."
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
    
    # Guardar resultado
    backend_exit_code=$?
    
    cd ..
    
    return $backend_exit_code
}

# Función para ejecutar tests del frontend
run_frontend_tests() {
    log_step "Ejecutando tests del frontend..."
    
    cd frontend
    
    # Verificar que node_modules existe
    if [ ! -d "node_modules" ]; then
        log_info "Instalando dependencias del frontend..."
        npm install
    fi
    
    # Ejecutar tests con coverage
    log_info "Ejecutando tests unitarios del frontend..."
    npm test -- --coverage --watchAll=false
    
    # Guardar resultado
    frontend_exit_code=$?
    
    cd ..
    
    return $frontend_exit_code
}

# Función para ejecutar tests de integración
run_integration_tests() {
    log_step "Ejecutando tests de integración..."
    
    # Iniciar servicios para tests de integración
    log_info "Iniciando servicios para tests de integración..."
    docker-compose -f docker-compose.test.yml up -d db redis
    
    # Esperar a que los servicios estén listos
    sleep 10
    
    cd backend
    source venv/bin/activate
    
    # Ejecutar tests de integración específicos
    log_info "Ejecutando tests de integración..."
    pytest tests/test_api_integration.py -v -k "integration"
    
    integration_exit_code=$?
    
    cd ..
    
    # Limpiar servicios
    docker-compose -f docker-compose.test.yml down
    
    return $integration_exit_code
}

# Función para ejecutar tests de carga
run_load_tests() {
    log_step "Ejecutando tests de carga..."
    
    # Verificar que locust está instalado
    if ! command -v locust &> /dev/null; then
        log_warn "Locust no está instalado. Instalando..."
        pip install locust
    fi
    
    # Iniciar aplicación en modo test
    log_info "Iniciando aplicación para tests de carga..."
    docker-compose up -d
    
    # Esperar a que la aplicación esté lista
    sleep 30
    
    # Ejecutar tests de carga
    log_info "Ejecutando tests de carga (30 segundos)..."
    locust -f tests/load_tests.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=30s --headless
    
    load_exit_code=$?
    
    # Detener aplicación
    docker-compose down
    
    return $load_exit_code
}

# Función para ejecutar tests end-to-end
run_e2e_tests() {
    log_step "Ejecutando tests end-to-end..."
    
    cd frontend
    
    # Verificar que Cypress está instalado
    if [ ! -d "node_modules/cypress" ]; then
        log_info "Instalando Cypress..."
        npm install --save-dev cypress @testing-library/cypress
    fi
    
    # Iniciar aplicación completa
    log_info "Iniciando aplicación completa para E2E..."
    cd ..
    docker-compose up -d
    
    # Esperar a que la aplicación esté lista
    sleep 60
    
    cd frontend
    
    # Ejecutar tests E2E
    log_info "Ejecutando tests end-to-end..."
    npx cypress run
    
    e2e_exit_code=$?
    
    cd ..
    
    # Detener aplicación
    docker-compose down
    
    return $e2e_exit_code
}

# Función para generar reporte consolidado
generate_report() {
    log_step "Generando reporte consolidado..."
    
    # Crear directorio de reportes
    mkdir -p test-reports
    
    # Crear reporte HTML consolidado
    cat > test-reports/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Reporte de Tests - TuAppDeAccesorios</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .pass { color: green; }
        .fail { color: red; }
        .warn { color: orange; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Reporte de Tests - TuAppDeAccesorios</h1>
        <p>Fecha: $(date)</p>
    </div>
    
    <div class="section">
        <h2>Resumen de Ejecución</h2>
        <table>
            <tr><th>Tipo de Test</th><th>Estado</th><th>Cobertura</th></tr>
            <tr><td>Backend Unit Tests</td><td id="backend-status">-</td><td id="backend-coverage">-</td></tr>
            <tr><td>Frontend Unit Tests</td><td id="frontend-status">-</td><td id="frontend-coverage">-</td></tr>
            <tr><td>Integration Tests</td><td id="integration-status">-</td><td>-</td></tr>
            <tr><td>Load Tests</td><td id="load-status">-</td><td>-</td></tr>
            <tr><td>E2E Tests</td><td id="e2e-status">-</td><td>-</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Enlaces a Reportes Detallados</h2>
        <ul>
            <li><a href="../backend/htmlcov/index.html">Cobertura Backend</a></li>
            <li><a href="../frontend/coverage/lcov-report/index.html">Cobertura Frontend</a></li>
            <li><a href="cypress-report.html">Reporte Cypress</a></li>
        </ul>
    </div>
</body>
</html>
EOF

    log_info "Reporte generado en test-reports/index.html"
}

# Función para mostrar estadísticas finales
show_summary() {
    log_step "Resumen de ejecución de tests"
    
    echo "======================================================"
    echo "                RESUMEN DE TESTS"
    echo "======================================================"
    
    if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "backend" ]; then
        if [ ${backend_exit_code:-1} -eq 0 ]; then
            echo -e "Backend Unit Tests:     ${GREEN}✓ PASS${NC}"
        else
            echo -e "Backend Unit Tests:     ${RED}✗ FAIL${NC}"
        fi
    fi
    
    if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "frontend" ]; then
        if [ ${frontend_exit_code:-1} -eq 0 ]; then
            echo -e "Frontend Unit Tests:    ${GREEN}✓ PASS${NC}"
        else
            echo -e "Frontend Unit Tests:    ${RED}✗ FAIL${NC}"
        fi
    fi
    
    if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "integration" ]; then
        if [ ${integration_exit_code:-1} -eq 0 ]; then
            echo -e "Integration Tests:      ${GREEN}✓ PASS${NC}"
        else
            echo -e "Integration Tests:      ${RED}✗ FAIL${NC}"
        fi
    fi
    
    if [ "$TEST_TYPE" = "load" ]; then
        if [ ${load_exit_code:-1} -eq 0 ]; then
            echo -e "Load Tests:             ${GREEN}✓ PASS${NC}"
        else
            echo -e "Load Tests:             ${RED}✗ FAIL${NC}"
        fi
    fi
    
    if [ "$TEST_TYPE" = "e2e" ]; then
        if [ ${e2e_exit_code:-1} -eq 0 ]; then
            echo -e "E2E Tests:              ${GREEN}✓ PASS${NC}"
        else
            echo -e "E2E Tests:              ${RED}✗ FAIL${NC}"
        fi
    fi
    
    echo "======================================================"
    
    # Calcular resultado general
    total_failed=0
    if [ ${backend_exit_code:-0} -ne 0 ]; then ((total_failed++)); fi
    if [ ${frontend_exit_code:-0} -ne 0 ]; then ((total_failed++)); fi
    if [ ${integration_exit_code:-0} -ne 0 ]; then ((total_failed++)); fi
    if [ ${load_exit_code:-0} -ne 0 ]; then ((total_failed++)); fi
    if [ ${e2e_exit_code:-0} -ne 0 ]; then ((total_failed++)); fi
    
    if [ $total_failed -eq 0 ]; then
        echo -e "${GREEN}🎉 TODOS LOS TESTS PASARON${NC}"
        echo
        echo "El proyecto está listo para deploy a producción"
        return 0
    else
        echo -e "${RED}❌ $total_failed TIPO(S) DE TEST FALLARON${NC}"
        echo
        echo "Revisa los errores antes de hacer deploy"
        return 1
    fi
}

# Ejecutar tests según el tipo especificado
case $TEST_TYPE in
    "backend")
        run_backend_tests
        ;;
    "frontend")
        run_frontend_tests
        ;;
    "integration")
        run_integration_tests
        ;;
    "load")
        run_load_tests
        ;;
    "e2e")
        run_e2e_tests
        ;;
    "all")
        run_backend_tests
        run_frontend_tests
        run_integration_tests
        ;;
    *)
        log_error "Tipo de test inválido: $TEST_TYPE"
        echo "Tipos válidos: all, backend, frontend, integration, load, e2e"
        exit 1
        ;;
esac

# Generar reporte y mostrar resumen
generate_report
show_summary

# Salir con código de error si algún test falló
exit $?