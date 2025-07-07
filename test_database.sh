#!/bin/bash

echo "🗄️  PRUEBAS DE BASE DE DATOS - TuAppDeAccesorios"
echo "==============================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para ejecutar SQL y mostrar resultado
run_sql() {
    echo -e "${BLUE}🔍 $1${NC}"
    echo "SQL: $2"
    echo ""
    RESULT=$(docker-compose exec -T db psql -U tuappuser -d tuappdb -c "$2" 2>/dev/null)
    echo "$RESULT"
    echo ""
}

# Verificar conexión
echo "🔌 VERIFICANDO CONEXIÓN A BASE DE DATOS"
echo "======================================="
docker-compose exec -T db pg_isready -U tuappuser -d tuappdb
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL está accesible${NC}"
else
    echo -e "${RED}❌ Error conectando a PostgreSQL${NC}"
    exit 1
fi
echo ""

# Información general de la base de datos
echo "📊 INFORMACIÓN GENERAL DE LA BASE DE DATOS"
echo "=========================================="

run_sql "Versión de PostgreSQL" "SELECT version();"

run_sql "Tamaño de la base de datos" "
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database 
WHERE datname = 'tuappdb';"

run_sql "Lista de tablas en el esquema público" "
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;"

# Análisis de datos
echo "📈 ANÁLISIS DE DATOS"
echo "==================="

run_sql "Conteo de registros por tabla" "
SELECT 
    'users' as tabla, COUNT(*) as registros FROM users
UNION ALL
SELECT 
    'products' as tabla, COUNT(*) as registros FROM products
UNION ALL
SELECT 
    'distributors' as tabla, COUNT(*) as registros FROM distributors
UNION ALL
SELECT 
    'point_of_sale_transactions' as tabla, COUNT(*) as registros FROM point_of_sale_transactions
UNION ALL
SELECT 
    'consignment_loans' as tabla, COUNT(*) as registros FROM consignment_loans
ORDER BY tabla;"

run_sql "Detalles de usuarios registrados" "
SELECT 
    id,
    username,
    role,
    CASE 
        WHEN hashed_password IS NOT NULL THEN 'Password configurado'
        ELSE 'Sin password'
    END as password_status
FROM users;"

run_sql "Inventario de productos" "
SELECT 
    id,
    sku,
    name,
    cost_price,
    selling_price,
    stock_quantity,
    ROUND((selling_price - cost_price), 2) as margen
FROM products
ORDER BY stock_quantity DESC;"

# Verificar índices
echo "🔍 VERIFICACIÓN DE ÍNDICES"
echo "========================="

run_sql "Índices en la tabla products" "
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'products'
ORDER BY indexname;"

run_sql "Estadísticas de uso de índices" "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('products', 'users', 'distributors')
ORDER BY tablename, indexname;"

# Pruebas de performance
echo "⚡ PRUEBAS DE PERFORMANCE"
echo "========================"

run_sql "Tiempo de consulta de productos" "
EXPLAIN ANALYZE 
SELECT * FROM products 
WHERE stock_quantity > 0 
ORDER BY selling_price DESC;"

# Verificar configuración
echo "⚙️  CONFIGURACIÓN DE POSTGRESQL"
echo "==============================="

run_sql "Configuración de memoria" "
SELECT 
    name,
    setting,
    unit,
    context
FROM pg_settings 
WHERE name IN (
    'shared_buffers',
    'effective_cache_size',
    'work_mem',
    'maintenance_work_mem',
    'max_connections'
);"

run_sql "Configuración de logging" "
SELECT 
    name,
    setting,
    context
FROM pg_settings 
WHERE name LIKE 'log_%' 
AND name IN (
    'log_min_duration_statement',
    'log_connections',
    'log_disconnections',
    'log_checkpoints'
);"

# Estado de las conexiones
echo "🔗 ESTADO DE CONEXIONES"
echo "======================="

run_sql "Conexiones activas" "
SELECT 
    datname,
    usename,
    application_name,
    client_addr,
    state,
    backend_start,
    state_change
FROM pg_stat_activity 
WHERE datname = 'tuappdb';"

# Comandos útiles para desarrollo
echo ""
echo "🛠️  COMANDOS ÚTILES PARA BASE DE DATOS"
echo "====================================="
echo ""
echo "Conectar a PostgreSQL:"
echo "  docker-compose exec db psql -U tuappuser -d tuappdb"
echo ""
echo "Hacer backup:"
echo "  docker-compose exec db pg_dump -U tuappuser tuappdb > backup.sql"
echo ""
echo "Restaurar backup:"
echo "  docker-compose exec -T db psql -U tuappuser -d tuappdb < backup.sql"
echo ""
echo "Ver logs de PostgreSQL:"
echo "  docker-compose logs db -f"
echo ""
echo "Reiniciar solo la base de datos:"
echo "  docker-compose restart db"
echo ""
echo "Verificar espacio en disco:"
echo "  docker system df"
echo ""

echo "🎉 PRUEBAS DE BASE DE DATOS COMPLETADAS"