#!/bin/bash

# Script para monitorear volúmenes Docker y persistencia de datos
echo "📊 MONITOREO DE VOLÚMENES Y PERSISTENCIA"
echo "======================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
PROJECT_NAME="tuapp"
THRESHOLD_WARNING=80
THRESHOLD_CRITICAL=90

# Funciones de utilidad
format_bytes() {
    local bytes=$1
    local sizes=("B" "KB" "MB" "GB" "TB")
    local size=0
    
    while (( bytes > 1024 && size < ${#sizes[@]} - 1 )); do
        bytes=$((bytes / 1024))
        ((size++))
    done
    
    echo "${bytes}${sizes[$size]}"
}

check_docker_volume() {
    local volume_name="$1"
    local description="$2"
    
    echo "📁 $description ($volume_name)"
    echo "----------------------------------------"
    
    # Verificar si el volumen existe
    if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
        echo -e "${RED}✗ Volumen no existe${NC}"
        return 1
    fi
    
    # Obtener información del volumen
    local mountpoint=$(docker volume inspect "$volume_name" --format '{{.Mountpoint}}')
    local driver=$(docker volume inspect "$volume_name" --format '{{.Driver}}')
    local scope=$(docker volume inspect "$volume_name" --format '{{.Scope}}')
    
    echo "Driver: $driver"
    echo "Scope: $scope"
    echo "Mountpoint: $mountpoint"
    
    # Verificar espacio usando un contenedor temporal
    echo "Analizando uso de espacio..."
    
    local usage_info=$(docker run --rm -v "$volume_name":/volume:ro alpine sh -c '
        df -h /volume | tail -1
        echo "---"
        du -sh /volume/* 2>/dev/null | sort -hr | head -10
    ')
    
    echo "$usage_info"
    
    # Extraer porcentaje de uso
    local usage_percent=$(echo "$usage_info" | head -1 | awk '{print $5}' | sed 's/%//')
    
    if [ -n "$usage_percent" ] && [ "$usage_percent" -ge "$THRESHOLD_CRITICAL" ]; then
        echo -e "${RED}🚨 CRÍTICO: Uso de espacio $usage_percent%${NC}"
    elif [ -n "$usage_percent" ] && [ "$usage_percent" -ge "$THRESHOLD_WARNING" ]; then
        echo -e "${YELLOW}⚠ ADVERTENCIA: Uso de espacio $usage_percent%${NC}"
    else
        echo -e "${GREEN}✓ Uso de espacio OK: $usage_percent%${NC}"
    fi
    
    echo ""
}

check_bind_mount() {
    local host_path="$1"
    local description="$2"
    
    echo "📂 $description"
    echo "----------------------------------------"
    
    if [ ! -d "$host_path" ]; then
        echo -e "${RED}✗ Directorio no existe: $host_path${NC}"
        return 1
    fi
    
    # Información del directorio
    echo "Ruta: $host_path"
    echo "Propietario: $(stat -c '%U:%G' "$host_path" 2>/dev/null || echo "N/A")"
    echo "Permisos: $(stat -c '%a' "$host_path" 2>/dev/null || echo "N/A")"
    
    # Espacio usado
    local usage=$(du -sh "$host_path" 2>/dev/null | cut -f1)
    echo "Espacio usado: $usage"
    
    # Verificar espacio disponible en el sistema de archivos
    local fs_info=$(df -h "$host_path" | tail -1)
    echo "Sistema de archivos:"
    echo "  $fs_info"
    
    # Extraer porcentaje de uso del sistema de archivos
    local fs_usage=$(echo "$fs_info" | awk '{print $5}' | sed 's/%//')
    
    if [ "$fs_usage" -ge "$THRESHOLD_CRITICAL" ]; then
        echo -e "${RED}🚨 CRÍTICO: Sistema de archivos $fs_usage% lleno${NC}"
    elif [ "$fs_usage" -ge "$THRESHOLD_WARNING" ]; then
        echo -e "${YELLOW}⚠ ADVERTENCIA: Sistema de archivos $fs_usage% lleno${NC}"
    else
        echo -e "${GREEN}✓ Sistema de archivos OK: $fs_usage% usado${NC}"
    fi
    
    echo ""
}

check_volume_integrity() {
    local volume_name="$1"
    local expected_files="$2"
    
    echo "🔍 Verificando integridad de $volume_name..."
    
    # Verificar archivos esperados
    if [ -n "$expected_files" ]; then
        echo "Archivos/directorios esperados:"
        IFS=',' read -ra FILES <<< "$expected_files"
        for file in "${FILES[@]}"; do
            if docker run --rm -v "$volume_name":/volume:ro alpine test -e "/volume/$file"; then
                echo -e "${GREEN}✓${NC} $file"
            else
                echo -e "${RED}✗${NC} $file (FALTANTE)"
            fi
        done
    fi
    
    # Verificar permisos básicos
    echo "Verificando permisos..."
    local perms=$(docker run --rm -v "$volume_name":/volume:ro alpine stat -c '%a' /volume)
    if [ "$perms" = "755" ] || [ "$perms" = "750" ] || [ "$perms" = "700" ]; then
        echo -e "${GREEN}✓${NC} Permisos OK ($perms)"
    else
        echo -e "${YELLOW}⚠${NC} Permisos inusuales ($perms)"
    fi
    
    echo ""
}

generate_volume_report() {
    echo "📋 GENERANDO REPORTE COMPLETO..."
    echo "==============================="
    
    local report_file="/tmp/volume-report-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "REPORTE DE VOLÚMENES - $(date)"
        echo "=============================="
        echo ""
        
        echo "VOLÚMENES DOCKER:"
        docker volume ls --filter name=${PROJECT_NAME}
        echo ""
        
        echo "CONTENEDORES USANDO VOLÚMENES:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Mounts}}" | grep ${PROJECT_NAME}
        echo ""
        
        echo "ESPACIO TOTAL USADO POR VOLÚMENES:"
        docker system df -v | grep ${PROJECT_NAME}
        echo ""
        
        echo "ESTADÍSTICAS DEL SISTEMA:"
        df -h
        echo ""
        
        echo "MEMORIA Y CPU:"
        free -h
        echo ""
        
    } > "$report_file"
    
    echo "Reporte generado: $report_file"
    echo "Para ver el reporte: cat $report_file"
}

backup_volume() {
    local volume_name="$1"
    local backup_dir="${2:-/opt/tuapp/backups/volumes}"
    
    echo "💾 Creando backup de volumen $volume_name..."
    
    # Crear directorio de backup
    mkdir -p "$backup_dir"
    
    local backup_file="$backup_dir/${volume_name}_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Crear backup del volumen
    docker run --rm \
        -v "$volume_name":/source:ro \
        -v "$backup_dir":/backup \
        alpine tar czf "/backup/$(basename "$backup_file")" -C /source .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup creado: $backup_file${NC}"
        echo "Tamaño: $(du -h "$backup_file" | cut -f1)"
    else
        echo -e "${RED}✗ Error creando backup${NC}"
        return 1
    fi
}

cleanup_old_data() {
    echo "🧹 LIMPIEZA DE DATOS ANTIGUOS..."
    echo "==============================="
    
    # Limpiar logs antiguos en volúmenes
    echo "Limpiando logs antiguos..."
    
    # PostgreSQL logs (más de 30 días)
    docker run --rm -v ${PROJECT_NAME}_postgres_logs:/logs alpine \
        find /logs -name "*.log" -mtime +30 -delete 2>/dev/null
    
    # Backend logs (más de 7 días)
    docker run --rm -v ${PROJECT_NAME}_backend_logs:/logs alpine \
        find /logs -name "*.log" -mtime +7 -delete 2>/dev/null
    
    # Backups antiguos (más de 90 días)
    if [ -d "/opt/tuapp/backups" ]; then
        find /opt/tuapp/backups -name "*.tar.gz" -mtime +90 -delete 2>/dev/null
        find /opt/tuapp/backups -name "*.sql.gz" -mtime +90 -delete 2>/dev/null
    fi
    
    echo -e "${GREEN}✓ Limpieza completada${NC}"
}

monitor_volume_performance() {
    echo "⚡ MONITOREO DE RENDIMIENTO..."
    echo "============================="
    
    # Test de escritura
    echo "Probando velocidad de escritura..."
    local write_speed=$(docker run --rm -v ${PROJECT_NAME}_postgres_data:/test alpine \
        sh -c 'dd if=/dev/zero of=/test/speed_test bs=1M count=100 2>&1 | grep copied' | \
        awk '{print $(NF-1), $NF}')
    
    echo "Velocidad de escritura: $write_speed"
    
    # Limpiar archivo de prueba
    docker run --rm -v ${PROJECT_NAME}_postgres_data:/test alpine rm -f /test/speed_test
    
    # Test de lectura
    echo "Probando velocidad de lectura..."
    local read_speed=$(docker run --rm -v ${PROJECT_NAME}_postgres_data:/test alpine \
        sh -c 'dd if=/dev/zero of=/test/read_test bs=1M count=50 && dd if=/test/read_test of=/dev/null bs=1M 2>&1 | grep copied' | \
        tail -1 | awk '{print $(NF-1), $NF}')
    
    echo "Velocidad de lectura: $read_speed"
    
    # Limpiar archivo de prueba
    docker run --rm -v ${PROJECT_NAME}_postgres_data:/test alpine rm -f /test/read_test
    
    echo ""
}

show_help() {
    echo "USO: $0 [COMANDO]"
    echo ""
    echo "COMANDOS:"
    echo "  status              - Mostrar estado de todos los volúmenes"
    echo "  check               - Verificar integridad de volúmenes"
    echo "  report              - Generar reporte completo"
    echo "  backup [volume]     - Crear backup de volumen específico"
    echo "  cleanup             - Limpiar datos antiguos"
    echo "  performance         - Test de rendimiento de volúmenes"
    echo "  help                - Mostrar esta ayuda"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0 status"
    echo "  $0 backup ${PROJECT_NAME}_postgres_data"
    echo "  $0 cleanup"
}

# Función principal para verificar estado
check_volume_status() {
    echo "🔍 VERIFICANDO ESTADO DE VOLÚMENES..."
    echo "===================================="
    echo ""
    
    # Verificar volúmenes Docker
    check_docker_volume "${PROJECT_NAME}_postgres_data" "Base de Datos PostgreSQL"
    check_docker_volume "${PROJECT_NAME}_redis_data" "Cache Redis"
    check_docker_volume "${PROJECT_NAME}_backend_logs" "Logs del Backend"
    
    # Verificar bind mounts (solo en producción)
    if [ -d "/opt/tuapp" ]; then
        echo "🗂️  VERIFICANDO DIRECTORIOS DE PRODUCCIÓN..."
        echo "==========================================="
        echo ""
        
        check_bind_mount "/opt/tuapp/data/postgres" "Datos PostgreSQL (Host)"
        check_bind_mount "/opt/tuapp/data/redis" "Datos Redis (Host)"
        check_bind_mount "/opt/tuapp/backups" "Directorio de Backups"
        check_bind_mount "/opt/tuapp/logs" "Logs de Aplicación"
    fi
    
    # Verificar integridad
    echo "🔍 VERIFICANDO INTEGRIDAD..."
    echo "=========================="
    echo ""
    
    check_volume_integrity "${PROJECT_NAME}_postgres_data" "base,global,pg_stat,pg_xact"
    check_volume_integrity "${PROJECT_NAME}_redis_data" "dump.rdb,appendonly.aof"
    
    echo -e "${GREEN}✓ Verificación de volúmenes completada${NC}"
}

# Parsear argumentos
case "$1" in
    "status"|"")
        check_volume_status
        ;;
    "check")
        check_volume_status
        ;;
    "report")
        generate_volume_report
        ;;
    "backup")
        if [ -n "$2" ]; then
            backup_volume "$2" "$3"
        else
            echo "Creando backups de todos los volúmenes..."
            backup_volume "${PROJECT_NAME}_postgres_data"
            backup_volume "${PROJECT_NAME}_redis_data"
        fi
        ;;
    "cleanup")
        cleanup_old_data
        ;;
    "performance")
        monitor_volume_performance
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