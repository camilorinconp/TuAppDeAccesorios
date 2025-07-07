#!/bin/bash

# Script para probar conectividad de red entre servicios Docker
echo "🌐 TEST DE CONECTIVIDAD DE RED"
echo "=============================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
PROJECT_NAME="tuapp"
NETWORK_NAME="${PROJECT_NAME}_default"

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Funciones de utilidad
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Verificar que los servicios estén corriendo
check_services_running() {
    echo "1. VERIFICANDO SERVICIOS..."
    echo "-------------------------"
    
    local services=("db" "redis" "backend")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            test_pass "Servicio $service está corriendo"
        else
            test_fail "Servicio $service NO está corriendo"
        fi
    done
    
    echo ""
}

# Verificar red Docker
check_docker_network() {
    echo "2. VERIFICANDO RED DOCKER..."
    echo "--------------------------"
    
    # Verificar que la red existe
    if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
        test_pass "Red Docker '$NETWORK_NAME' existe"
        
        # Obtener información de la red
        local network_info=$(docker network inspect "$NETWORK_NAME" --format '{{.Driver}} {{.Scope}}')
        echo "  Tipo: $network_info"
        
        # Verificar contenedores conectados
        local connected_containers=$(docker network inspect "$NETWORK_NAME" --format '{{range $key, $value := .Containers}}{{$value.Name}} {{end}}')
        echo "  Contenedores conectados: $connected_containers"
        
        if [ -n "$connected_containers" ]; then
            test_pass "Contenedores conectados a la red"
        else
            test_warn "No hay contenedores conectados a la red"
        fi
        
    else
        test_fail "Red Docker '$NETWORK_NAME' no existe"
    fi
    
    echo ""
}

# Test de conectividad entre servicios
test_service_connectivity() {
    echo "3. TESTING CONECTIVIDAD ENTRE SERVICIOS..."
    echo "-----------------------------------------"
    
    # Test: Backend -> Database
    echo "Backend -> Database (PostgreSQL):"
    if docker-compose exec -T backend python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host='db',
        port=5432,
        user=os.getenv('POSTGRES_USER', 'tuapp_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'tuapp_password'),
        database=os.getenv('POSTGRES_DB', 'tuapp_db')
    )
    conn.close()
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null | grep -q "SUCCESS"; then
        test_pass "Backend puede conectar a PostgreSQL"
    else
        test_fail "Backend NO puede conectar a PostgreSQL"
    fi
    
    # Test: Backend -> Redis
    echo "Backend -> Redis:"
    if docker-compose exec -T backend python -c "
import redis
import os
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null | grep -q "SUCCESS"; then
        test_pass "Backend puede conectar a Redis"
    else
        test_fail "Backend NO puede conectar a Redis"
    fi
    
    # Test: Database connectivity directo
    echo "Test directo de PostgreSQL:"
    if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-tuapp_user} >/dev/null 2>&1; then
        test_pass "PostgreSQL responde correctamente"
    else
        test_fail "PostgreSQL NO responde"
    fi
    
    # Test: Redis connectivity directo
    echo "Test directo de Redis:"
    if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        test_pass "Redis responde correctamente"
    else
        test_fail "Redis NO responde"
    fi
    
    echo ""
}

# Test de puertos y endpoints
test_ports_and_endpoints() {
    echo "4. TESTING PUERTOS Y ENDPOINTS..."
    echo "--------------------------------"
    
    # Test Backend API
    echo "API Backend (Puerto 8000):"
    local backend_health=$(curl -s -f http://localhost:8000/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        test_pass "API Backend responde en puerto 8000"
        echo "  Respuesta: $backend_health"
    else
        test_fail "API Backend NO responde en puerto 8000"
    fi
    
    # Test Frontend (si está corriendo)
    if docker-compose ps frontend | grep -q "Up"; then
        echo "Frontend (Puerto 3001):"
        if curl -s -f http://localhost:3001 >/dev/null 2>&1; then
            test_pass "Frontend responde en puerto 3001"
        else
            test_fail "Frontend NO responde en puerto 3001"
        fi
    fi
    
    # Test Database (solo en desarrollo)
    if docker-compose ps | grep "5433:5432"; then
        echo "PostgreSQL (Puerto 5433 - Solo desarrollo):"
        if pg_isready -h localhost -p 5433 -U ${POSTGRES_USER:-tuapp_user} >/dev/null 2>&1; then
            test_pass "PostgreSQL accesible desde host (desarrollo)"
        else
            test_warn "PostgreSQL no accesible desde host"
        fi
    fi
    
    # Test Redis (solo en desarrollo)
    if docker-compose ps | grep "6380:6379"; then
        echo "Redis (Puerto 6380 - Solo desarrollo):"
        if redis-cli -h localhost -p 6380 ping >/dev/null 2>&1; then
            test_pass "Redis accesible desde host (desarrollo)"
        else
            test_warn "Redis no accesible desde host"
        fi
    fi
    
    echo ""
}

# Test de latencia entre servicios
test_network_latency() {
    echo "5. TESTING LATENCIA DE RED..."
    echo "---------------------------"
    
    # Latencia Backend -> Database
    echo "Latencia Backend -> Database:"
    local db_latency=$(docker-compose exec -T backend sh -c "time echo '' | nc -w1 db 5432" 2>&1 | grep real | awk '{print $2}')
    if [ -n "$db_latency" ]; then
        echo "  Tiempo de respuesta: $db_latency"
        test_pass "Latencia DB medida correctamente"
    else
        test_warn "No se pudo medir latencia a DB"
    fi
    
    # Latencia Backend -> Redis
    echo "Latencia Backend -> Redis:"
    local redis_latency=$(docker-compose exec -T backend sh -c "time echo '' | nc -w1 redis 6379" 2>&1 | grep real | awk '{print $2}')
    if [ -n "$redis_latency" ]; then
        echo "  Tiempo de respuesta: $redis_latency"
        test_pass "Latencia Redis medida correctamente"
    else
        test_warn "No se pudo medir latencia a Redis"
    fi
    
    echo ""
}

# Test de throughput de red
test_network_throughput() {
    echo "6. TESTING THROUGHPUT DE RED..."
    echo "-----------------------------"
    
    # Test de throughput con transferencia de datos
    echo "Probando throughput Backend -> Database:"
    
    local throughput_test=$(docker-compose exec -T backend python -c "
import time
import psycopg2
import os
try:
    start_time = time.time()
    conn = psycopg2.connect(
        host='db',
        port=5432,
        user=os.getenv('POSTGRES_USER', 'tuapp_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'tuapp_password'),
        database=os.getenv('POSTGRES_DB', 'tuapp_db')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    result = cursor.fetchone()
    end_time = time.time()
    print(f'Query time: {(end_time - start_time)*1000:.2f}ms')
    conn.close()
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null)
    
    if echo "$throughput_test" | grep -q "Query time"; then
        echo "  $throughput_test"
        test_pass "Throughput DB test completado"
    else
        test_warn "No se pudo completar throughput test DB"
    fi
    
    echo ""
}

# Test de seguridad de red
test_network_security() {
    echo "7. TESTING SEGURIDAD DE RED..."
    echo "----------------------------"
    
    # Verificar que los servicios internos no están expuestos en producción
    if [ ! -f "docker-compose.prod.yml" ]; then
        test_warn "docker-compose.prod.yml no encontrado"
    else
        # Verificar que DB no está expuesto
        if ! grep -q "5432:5432" docker-compose.prod.yml; then
            test_pass "PostgreSQL NO expuesto en producción"
        else
            test_fail "PostgreSQL EXPUESTO en producción (PELIGROSO)"
        fi
        
        # Verificar que Redis no está expuesto
        if ! grep -q "6379:6379" docker-compose.prod.yml; then
            test_pass "Redis NO expuesto en producción"
        else
            test_fail "Redis EXPUESTO en producción (PELIGROSO)"
        fi
    fi
    
    # Verificar configuración de red interna
    local internal_ips=$(docker network inspect "$NETWORK_NAME" --format '{{.IPAM.Config}}' 2>/dev/null)
    if [ -n "$internal_ips" ]; then
        echo "  Red interna: $internal_ips"
        test_pass "Red interna configurada"
    else
        test_warn "No se pudo verificar configuración de red interna"
    fi
    
    echo ""
}

# Test de DNS interno
test_internal_dns() {
    echo "8. TESTING DNS INTERNO..."
    echo "-----------------------"
    
    # Test resolución DNS interna
    echo "Resolución DNS Backend -> db:"
    if docker-compose exec -T backend nslookup db >/dev/null 2>&1; then
        test_pass "DNS interno funciona (backend -> db)"
    else
        test_fail "DNS interno NO funciona (backend -> db)"
    fi
    
    echo "Resolución DNS Backend -> redis:"
    if docker-compose exec -T backend nslookup redis >/dev/null 2>&1; then
        test_pass "DNS interno funciona (backend -> redis)"
    else
        test_fail "DNS interno NO funciona (backend -> redis)"
    fi
    
    # Mostrar configuración DNS
    local dns_config=$(docker-compose exec -T backend cat /etc/resolv.conf 2>/dev/null)
    if [ -n "$dns_config" ]; then
        echo "  Configuración DNS:"
        echo "$dns_config" | sed 's/^/    /'
    fi
    
    echo ""
}

# Generar reporte de red
generate_network_report() {
    echo "📋 GENERANDO REPORTE DE RED..."
    echo "============================="
    
    local report_file="/tmp/network-report-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "REPORTE DE RED - $(date)"
        echo "======================="
        echo ""
        
        echo "REDES DOCKER:"
        docker network ls
        echo ""
        
        echo "DETALLE DE RED DEL PROYECTO:"
        docker network inspect "$NETWORK_NAME" 2>/dev/null || echo "Red no encontrada"
        echo ""
        
        echo "PUERTOS EXPUESTOS:"
        docker-compose ps
        echo ""
        
        echo "ESTADO DE SERVICIOS:"
        docker-compose ps --services | while read service; do
            echo "=== $service ==="
            docker-compose logs --tail=5 "$service" 2>/dev/null || echo "No logs available"
            echo ""
        done
        
    } > "$report_file"
    
    echo "Reporte generado: $report_file"
    echo "Para ver el reporte: cat $report_file"
}

# Función para mostrar ayuda
show_help() {
    echo "USO: $0 [COMANDO]"
    echo ""
    echo "COMANDOS:"
    echo "  test                - Ejecutar todos los tests de conectividad"
    echo "  services            - Verificar solo estado de servicios"
    echo "  network             - Verificar solo configuración de red"
    echo "  connectivity        - Probar solo conectividad entre servicios"
    echo "  ports               - Probar solo puertos y endpoints"
    echo "  security            - Verificar solo seguridad de red"
    echo "  report              - Generar reporte completo de red"
    echo "  help                - Mostrar esta ayuda"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0 test"
    echo "  $0 connectivity"
    echo "  $0 report"
}

# Función principal de test completo
run_complete_test() {
    echo "🧪 EJECUTANDO TEST COMPLETO DE RED..."
    echo "===================================="
    echo ""
    
    check_services_running
    check_docker_network
    test_service_connectivity
    test_ports_and_endpoints
    test_network_latency
    test_network_throughput
    test_network_security
    test_internal_dns
    
    echo "================================="
    echo "RESUMEN DE TESTS:"
    echo "================================="
    echo -e "${GREEN}✓ Tests pasados: $PASSED${NC}"
    echo -e "${YELLOW}⚠ Advertencias: $WARNINGS${NC}"
    echo -e "${RED}✗ Tests fallidos: $FAILED${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 ¡EXCELENTE! Conectividad de red perfecta.${NC}"
        exit 0
    elif [ $FAILED -eq 0 ]; then
        echo -e "${YELLOW}⚠ Conectividad OK con algunas advertencias.${NC}"
        exit 1
    else
        echo -e "${RED}❌ Problemas de conectividad detectados.${NC}"
        echo ""
        echo "PRÓXIMOS PASOS:"
        echo "1. Verificar que todos los servicios estén corriendo"
        echo "2. Revisar configuración de red en docker-compose.yml"
        echo "3. Verificar variables de entorno"
        echo "4. Revisar logs de servicios: docker-compose logs"
        exit 2
    fi
}

# Parsear argumentos
case "$1" in
    "test"|"")
        run_complete_test
        ;;
    "services")
        check_services_running
        ;;
    "network")
        check_docker_network
        ;;
    "connectivity")
        test_service_connectivity
        ;;
    "ports")
        test_ports_and_endpoints
        ;;
    "security")
        test_network_security
        ;;
    "report")
        generate_network_report
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}✗ Comando desconocido: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac