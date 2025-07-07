#!/bin/bash

# Script completo para gestión de base de datos
echo "🗄️ GESTIÓN DE BASE DE DATOS"
echo "========================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Funciones de utilidad
check_dependencies() {
    echo "Verificando dependencias..."
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker no está instalado${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗ Docker Compose no está instalado${NC}"
        exit 1
    fi
    
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        echo -e "${RED}✗ docker-compose.yml no encontrado${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Dependencias verificadas${NC}"
}

show_help() {
    echo "USO: $0 [COMANDO] [OPCIONES]"
    echo ""
    echo "COMANDOS:"
    echo "  init                    - Inicializar base de datos"
    echo "  migrate                 - Ejecutar migraciones pendientes"
    echo "  rollback [steps]        - Retroceder migraciones (default: 1 paso)"
    echo "  create-migration [name] - Crear nueva migración"
    echo "  status                  - Ver estado de migraciones"
    echo "  backup                  - Crear backup de la base de datos"
    echo "  restore [file]          - Restaurar desde backup"
    echo "  reset                   - Resetear base de datos (PELIGROSO)"
    echo "  validate                - Validar integridad de la base de datos"
    echo "  seed                    - Insertar datos de prueba"
    echo "  cleanup                 - Limpiar logs y datos temporales"
    echo "  help                    - Mostrar esta ayuda"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0 init"
    echo "  $0 migrate"
    echo "  $0 create-migration add_user_preferences"
    echo "  $0 backup"
    echo "  $0 restore backup_2024-01-01.sql.gz"
    echo "  $0 rollback 2"
}

wait_for_db() {
    echo "Esperando a que la base de datos esté lista..."
    
    local max_tries=30
    local try=0
    
    while [ $try -lt $max_tries ]; do
        if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Base de datos lista${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 1
        ((try++))
    done
    
    echo -e "${RED}✗ Timeout esperando la base de datos${NC}"
    return 1
}

init_database() {
    echo "Inicializando base de datos..."
    
    # Verificar si Docker Compose está corriendo
    if ! docker-compose ps | grep -q "Up"; then
        echo "Iniciando servicios de Docker Compose..."
        docker-compose up -d db redis
    fi
    
    # Esperar a que la DB esté lista
    wait_for_db
    
    # Verificar si Alembic está configurado
    if [ ! -f "$BACKEND_DIR/alembic.ini" ]; then
        echo -e "${RED}✗ alembic.ini no encontrado${NC}"
        exit 1
    fi
    
    # Cambiar al directorio del backend
    cd "$BACKEND_DIR"
    
    # Instalar dependencias si es necesario
    if [ ! -d "venv" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Verificar si la base de datos ya tiene migraciones
    if docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} -c "SELECT * FROM alembic_version;" 2>/dev/null | grep -q "001"; then
        echo -e "${YELLOW}⚠ Base de datos ya inicializada${NC}"
        return 0
    fi
    
    # Ejecutar migraciones iniciales
    echo "Ejecutando migraciones iniciales..."
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Base de datos inicializada correctamente${NC}"
    else
        echo -e "${RED}✗ Error inicializando base de datos${NC}"
        exit 1
    fi
}

run_migrations() {
    echo "Ejecutando migraciones..."
    
    cd "$BACKEND_DIR"
    
    # Activar entorno virtual
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    
    # Verificar estado actual
    echo "Estado actual de migraciones:"
    alembic current
    
    # Mostrar migraciones pendientes
    echo "Migraciones pendientes:"
    alembic heads
    
    # Ejecutar migraciones
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migraciones ejecutadas correctamente${NC}"
        
        # Mostrar estado final
        echo "Estado final:"
        alembic current
    else
        echo -e "${RED}✗ Error ejecutando migraciones${NC}"
        exit 1
    fi
}

rollback_migrations() {
    local steps=${1:-1}
    echo "Retrocediendo $steps migración(es)..."
    
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    
    # Mostrar estado actual
    echo "Estado actual:"
    alembic current
    
    # Calcular revisión objetivo
    if [ "$steps" = "1" ]; then
        echo "Retrocediendo 1 paso..."
        alembic downgrade -1
    else
        echo "Retrocediendo $steps pasos..."
        alembic downgrade -$steps
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rollback completado${NC}"
        echo "Estado final:"
        alembic current
    else
        echo -e "${RED}✗ Error en rollback${NC}"
        exit 1
    fi
}

create_migration() {
    local migration_name="$1"
    
    if [ -z "$migration_name" ]; then
        echo -e "${RED}✗ Nombre de migración requerido${NC}"
        echo "Uso: $0 create-migration <nombre_migracion>"
        exit 1
    fi
    
    echo "Creando migración: $migration_name"
    
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    
    # Crear migración automática
    alembic revision --autogenerate -m "$migration_name"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migración creada correctamente${NC}"
        echo "Revisa el archivo generado en migrations/versions/"
    else
        echo -e "${RED}✗ Error creando migración${NC}"
        exit 1
    fi
}

show_migration_status() {
    echo "Estado de migraciones:"
    
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    
    echo "Revisión actual:"
    alembic current
    
    echo ""
    echo "Historial de migraciones:"
    alembic history --verbose
    
    echo ""
    echo "Migraciones pendientes:"
    alembic show head
}

backup_database() {
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_file="$PROJECT_ROOT/backups/${backup_name}.sql.gz"
    
    echo "Creando backup de la base de datos..."
    
    # Crear directorio de backups si no existe
    mkdir -p "$PROJECT_ROOT/backups"
    
    # Crear backup
    docker-compose exec -T db pg_dump -U ${POSTGRES_USER:-tuapp_user} ${POSTGRES_DB:-tuapp_db} | gzip > "$backup_file"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup creado: $backup_file${NC}"
        
        # Mostrar información del backup
        echo "Información del backup:"
        echo "  Archivo: $backup_file"
        echo "  Tamaño: $(du -h "$backup_file" | cut -f1)"
        echo "  Fecha: $(date)"
    else
        echo -e "${RED}✗ Error creando backup${NC}"
        exit 1
    fi
}

restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        echo -e "${RED}✗ Archivo de backup requerido${NC}"
        echo "Uso: $0 restore <archivo_backup>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}✗ Archivo de backup no encontrado: $backup_file${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}⚠ ADVERTENCIA: Esta operación sobrescribirá la base de datos actual${NC}"
    read -p "¿Continuar? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operación cancelada"
        exit 0
    fi
    
    echo "Restaurando base de datos desde: $backup_file"
    
    # Detener la aplicación
    docker-compose stop backend
    
    # Restaurar backup
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db}
    else
        cat "$backup_file" | docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db}
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Base de datos restaurada correctamente${NC}"
        
        # Reiniciar la aplicación
        docker-compose start backend
    else
        echo -e "${RED}✗ Error restaurando base de datos${NC}"
        exit 1
    fi
}

reset_database() {
    echo -e "${RED}⚠ PELIGRO: Esta operación eliminará TODOS los datos${NC}"
    echo "Esta operación:"
    echo "  1. Eliminará todas las tablas"
    echo "  2. Eliminará todos los datos"
    echo "  3. Reinicializará la base de datos"
    echo ""
    read -p "¿Estás SEGURO de que quieres continuar? (type 'YES' to confirm): " -r
    
    if [ "$REPLY" != "YES" ]; then
        echo "Operación cancelada"
        exit 0
    fi
    
    echo "Reseteando base de datos..."
    
    # Crear backup automático antes de resetear
    echo "Creando backup automático de seguridad..."
    backup_database
    
    # Detener aplicación
    docker-compose stop backend
    
    # Eliminar y recrear base de datos
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-tuapp_db};"
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -c "CREATE DATABASE ${POSTGRES_DB:-tuapp_db};"
    
    # Reinicializar
    init_database
    
    echo -e "${GREEN}✓ Base de datos reseteada${NC}"
}

validate_database() {
    echo "Validando integridad de la base de datos..."
    
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Verificar conexión
    if ! wait_for_db; then
        echo -e "${RED}✗ No se puede conectar a la base de datos${NC}"
        exit 1
    fi
    
    # Verificar migraciones
    echo "Verificando estado de migraciones..."
    export DATABASE_URL="${DATABASE_URL:-postgresql://tuapp_user:tuapp_password@localhost:5433/tuapp_db}"
    alembic current
    
    # Verificar integridad de datos
    echo "Verificando integridad de datos..."
    
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} << 'EOF'
-- Verificar constraints
\echo "Verificando constraints..."
SELECT schemaname, tablename, constraintname 
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace n ON t.relnamespace = n.oid
WHERE n.nspname = 'public'
ORDER BY tablename, constraintname;

\echo "Verificando índices..."
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo "Verificando funciones personalizadas..."
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;

\echo "Verificando triggers..."
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;
EOF
    
    echo -e "${GREEN}✓ Validación completada${NC}"
}

seed_database() {
    echo "Insertando datos de prueba..."
    
    # Verificar que la base de datos esté inicializada
    if ! docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} -c "SELECT * FROM alembic_version;" &>/dev/null; then
        echo -e "${RED}✗ Base de datos no inicializada. Ejecuta primero: $0 init${NC}"
        exit 1
    fi
    
    # Insertar datos de prueba
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} << 'EOF'
-- Insertar usuarios de prueba
INSERT INTO users (username, hashed_password, role) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewfGw7bsS2fvQZZi', 'admin'),
('vendedor1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewfGw7bsS2fvQZZi', 'sales_staff')
ON CONFLICT (username) DO NOTHING;

-- Insertar productos de prueba
INSERT INTO products (sku, name, description, cost_price, selling_price, stock_quantity) VALUES
('CASE001', 'Funda Silicona iPhone 14', 'Funda de silicona resistente para iPhone 14', 5.00, 15.00, 50),
('CASE002', 'Funda Cristal Samsung S23', 'Funda de cristal transparente para Samsung Galaxy S23', 3.50, 12.00, 30),
('CHRG001', 'Cargador USB-C 20W', 'Cargador rápido USB-C de 20W', 8.00, 25.00, 25),
('CHRG002', 'Cable Lightning 1m', 'Cable Lightning certificado MFi 1 metro', 4.00, 12.00, 40),
('SCRN001', 'Protector Pantalla iPhone 14', 'Cristal templado 9H para iPhone 14', 2.00, 8.00, 60)
ON CONFLICT (sku) DO NOTHING;

-- Insertar distribuidores de prueba
INSERT INTO distributors (name, contact_person, phone_number, access_code) VALUES
('Distribuidora Central', 'Juan Pérez', '+1234567890', 'DIST001'),
('TechAccesorios SA', 'María García', '+0987654321', 'DIST002')
ON CONFLICT (access_code) DO NOTHING;

\echo "Datos de prueba insertados correctamente"
EOF
    
    echo -e "${GREEN}✓ Datos de prueba insertados${NC}"
}

cleanup_database() {
    echo "Limpiando logs y datos temporales..."
    
    # Limpiar logs antiguos de auditoría (más de 1 año)
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} << 'EOF'
DELETE FROM audit_log WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';
\echo "Logs de auditoría antiguos eliminados"
EOF
    
    # Limpiar archivos de backup antiguos (más de 30 días)
    if [ -d "$PROJECT_ROOT/backups" ]; then
        find "$PROJECT_ROOT/backups" -name "*.sql.gz" -mtime +30 -delete
        echo "Backups antiguos eliminados"
    fi
    
    # Optimizar base de datos
    docker-compose exec -T db psql -U ${POSTGRES_USER:-tuapp_user} -d ${POSTGRES_DB:-tuapp_db} << 'EOF'
VACUUM ANALYZE;
\echo "Base de datos optimizada"
EOF
    
    echo -e "${GREEN}✓ Limpieza completada${NC}"
}

# Verificar dependencias
check_dependencies

# Parsear argumentos
case "$1" in
    "init")
        init_database
        ;;
    "migrate")
        run_migrations
        ;;
    "rollback")
        rollback_migrations "$2"
        ;;
    "create-migration")
        create_migration "$2"
        ;;
    "status")
        show_migration_status
        ;;
    "backup")
        backup_database
        ;;
    "restore")
        restore_database "$2"
        ;;
    "reset")
        reset_database
        ;;
    "validate")
        validate_database
        ;;
    "seed")
        seed_database
        ;;
    "cleanup")
        cleanup_database
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo -e "${RED}✗ Comando desconocido: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac