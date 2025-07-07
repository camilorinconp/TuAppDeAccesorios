#!/bin/bash

# Sistema completo de backup y recuperación para TuAppDeAccesorios
# Uso: ./scripts/backup-system.sh [backup|restore|test|schedule]

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

# Configuración
BACKUP_DIR="/backups"
S3_BUCKET="tuapp-backups"
RETENTION_DAYS=30
POSTGRES_CONTAINER="db"
REDIS_CONTAINER="redis"
DATE=$(date +%Y%m%d_%H%M%S)

# Cargar variables de entorno
if [ -f ".env.prod" ]; then
    source .env.prod
fi

# Crear directorio de backups si no existe
mkdir -p $BACKUP_DIR

# Función para backup de PostgreSQL
backup_postgres() {
    log_step "Iniciando backup de PostgreSQL..."
    
    local backup_file="$BACKUP_DIR/postgres_backup_$DATE.sql"
    local compressed_file="$backup_file.gz"
    
    # Crear backup
    docker exec $POSTGRES_CONTAINER pg_dump \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        --no-password \
        --verbose \
        --format=custom \
        --blobs \
        --no-privileges \
        --no-owner \
        > "$backup_file.custom" 2>/dev/null
    
    # También crear backup en SQL plano para facilidad de lectura
    docker exec $POSTGRES_CONTAINER pg_dump \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        --no-password \
        --verbose \
        --format=plain \
        --no-privileges \
        --no-owner \
        > "$backup_file"
    
    # Comprimir backups
    gzip "$backup_file"
    gzip "$backup_file.custom"
    
    # Verificar integridad
    if [ -f "$compressed_file" ]; then
        local size=$(stat -f%z "$compressed_file" 2>/dev/null || stat -c%s "$compressed_file" 2>/dev/null)
        if [ $size -gt 1000 ]; then
            log_info "✅ Backup PostgreSQL completado: $compressed_file ($size bytes)"
            echo "$compressed_file" >> "$BACKUP_DIR/postgres_backups.log"
        else
            log_error "❌ Backup PostgreSQL falló - archivo muy pequeño"
            return 1
        fi
    else
        log_error "❌ Backup PostgreSQL falló - archivo no creado"
        return 1
    fi
}

# Función para backup de Redis
backup_redis() {
    log_step "Iniciando backup de Redis..."
    
    local backup_file="$BACKUP_DIR/redis_backup_$DATE.rdb"
    
    # Forzar escritura de datos a disco
    docker exec $REDIS_CONTAINER redis-cli BGSAVE
    
    # Esperar a que termine el backup
    while [ "$(docker exec $REDIS_CONTAINER redis-cli BGSAVE)" = "Background saving already in progress" ]; do
        sleep 1
    done
    
    # Copiar archivo RDB
    docker cp $REDIS_CONTAINER:/data/dump.rdb "$backup_file"
    
    # Comprimir
    gzip "$backup_file"
    
    # Verificar
    if [ -f "$backup_file.gz" ]; then
        log_info "✅ Backup Redis completado: $backup_file.gz"
        echo "$backup_file.gz" >> "$BACKUP_DIR/redis_backups.log"
    else
        log_error "❌ Backup Redis falló"
        return 1
    fi
}

# Función para backup de archivos de configuración
backup_configs() {
    log_step "Iniciando backup de configuraciones..."
    
    local backup_file="$BACKUP_DIR/configs_backup_$DATE.tar.gz"
    
    # Crear archivo tar con configuraciones importantes
    tar -czf "$backup_file" \
        --exclude='*.env*' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='logs' \
        docker-compose.prod.yml \
        nginx/ \
        scripts/ \
        backend/requirements.txt \
        backend/alembic.ini \
        backend/migrations/ \
        frontend/package.json \
        frontend/package-lock.json \
        monitoring/ \
        README.md \
        2>/dev/null || true
    
    if [ -f "$backup_file" ]; then
        log_info "✅ Backup configuraciones completado: $backup_file"
        echo "$backup_file" >> "$BACKUP_DIR/configs_backups.log"
    else
        log_error "❌ Backup configuraciones falló"
        return 1
    fi
}

# Función para subir backups a S3 (si está configurado)
upload_to_s3() {
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        log_warn "Credenciales AWS no configuradas, saltando upload a S3"
        return 0
    fi
    
    log_step "Subiendo backups a S3..."
    
    # Instalar AWS CLI si no está disponible
    if ! command -v aws &> /dev/null; then
        log_info "Instalando AWS CLI..."
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    fi
    
    # Subir archivos de backup del día actual
    for file in $BACKUP_DIR/*_$DATE.*; do
        if [ -f "$file" ]; then
            aws s3 cp "$file" "s3://$S3_BUCKET/$(date +%Y/%m/%d)/" --storage-class STANDARD_IA
            log_info "📤 Subido a S3: $(basename $file)"
        fi
    done
}

# Función para limpiar backups antiguos
cleanup_old_backups() {
    log_step "Limpiando backups antiguos (>$RETENTION_DAYS días)..."
    
    # Limpiar backups locales
    find $BACKUP_DIR -name "*backup_*" -type f -mtime +$RETENTION_DAYS -delete
    
    # Limpiar en S3 si está configurado
    if command -v aws &> /dev/null && [ -n "$AWS_ACCESS_KEY_ID" ]; then
        aws s3 ls "s3://$S3_BUCKET/" --recursive | \
        awk '$1 <= "'$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)'"' | \
        awk '{print $4}' | \
        xargs -I {} aws s3 rm "s3://$S3_BUCKET/{}"
    fi
    
    log_info "🧹 Limpieza de backups antiguos completada"
}

# Función para verificar integridad de backups
verify_backups() {
    log_step "Verificando integridad de backups..."
    
    local errors=0
    
    # Verificar backups PostgreSQL
    for backup in $BACKUP_DIR/postgres_backup_*.sql.gz; do
        if [ -f "$backup" ]; then
            if ! gzip -t "$backup" 2>/dev/null; then
                log_error "❌ Backup corrupto: $backup"
                ((errors++))
            fi
        fi
    done
    
    # Verificar backups Redis
    for backup in $BACKUP_DIR/redis_backup_*.rdb.gz; do
        if [ -f "$backup" ]; then
            if ! gzip -t "$backup" 2>/dev/null; then
                log_error "❌ Backup corrupto: $backup"
                ((errors++))
            fi
        fi
    done
    
    if [ $errors -eq 0 ]; then
        log_info "✅ Todos los backups son válidos"
        return 0
    else
        log_error "❌ Se encontraron $errors backups corruptos"
        return 1
    fi
}

# Función para restaurar PostgreSQL
restore_postgres() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        log_error "Debe especificar el archivo de backup"
        return 1
    fi
    
    log_step "Restaurando PostgreSQL desde $backup_file..."
    
    # Verificar que el archivo existe
    if [ ! -f "$backup_file" ]; then
        log_error "Archivo de backup no encontrado: $backup_file"
        return 1
    fi
    
    # Crear base de datos temporal para restauración
    docker exec $POSTGRES_CONTAINER createdb \
        -U $POSTGRES_USER \
        -T template0 \
        "${POSTGRES_DB}_restore_$(date +%s)"
    
    # Restaurar desde backup
    if [[ "$backup_file" == *.custom.gz ]]; then
        # Backup en formato custom
        gunzip -c "$backup_file" | \
        docker exec -i $POSTGRES_CONTAINER pg_restore \
            -U $POSTGRES_USER \
            -d "${POSTGRES_DB}_restore_$(date +%s)" \
            --verbose \
            --clean \
            --if-exists
    else
        # Backup en formato SQL
        gunzip -c "$backup_file" | \
        docker exec -i $POSTGRES_CONTAINER psql \
            -U $POSTGRES_USER \
            -d "${POSTGRES_DB}_restore_$(date +%s)"
    fi
    
    log_info "✅ Restauración PostgreSQL completada"
}

# Función para restaurar Redis
restore_redis() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        log_error "Debe especificar el archivo de backup"
        return 1
    fi
    
    log_step "Restaurando Redis desde $backup_file..."
    
    # Detener Redis temporalmente
    docker stop $REDIS_CONTAINER
    
    # Restaurar archivo RDB
    gunzip -c "$backup_file" > /tmp/dump.rdb
    docker cp /tmp/dump.rdb $REDIS_CONTAINER:/data/dump.rdb
    rm /tmp/dump.rdb
    
    # Reiniciar Redis
    docker start $REDIS_CONTAINER
    
    log_info "✅ Restauración Redis completada"
}

# Función para test de disaster recovery
test_disaster_recovery() {
    log_step "Iniciando test de disaster recovery..."
    
    # Crear backup de test
    backup_postgres
    backup_redis
    
    # Simular fallo creando containers de test
    log_info "Creando entorno de test..."
    
    # Test de restauración en containers separados
    docker run --name postgres_test \
        -e POSTGRES_USER=$POSTGRES_USER \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e POSTGRES_DB=${POSTGRES_DB}_test \
        -d postgres:15-alpine
    
    sleep 10
    
    # Restaurar último backup
    local latest_postgres=$(ls -t $BACKUP_DIR/postgres_backup_*.sql.gz | head -1)
    if [ -n "$latest_postgres" ]; then
        log_info "Testeando restauración de PostgreSQL..."
        POSTGRES_CONTAINER="postgres_test" restore_postgres "$latest_postgres"
    fi
    
    # Limpiar containers de test
    docker stop postgres_test && docker rm postgres_test
    
    log_info "✅ Test de disaster recovery completado"
}

# Función para configurar backup automático
schedule_backups() {
    log_step "Configurando backup automático..."
    
    # Crear script de backup automático
    cat > /usr/local/bin/tuapp-backup << 'EOF'
#!/bin/bash
cd /path/to/tuapp
./scripts/backup-system.sh backup
EOF
    
    # Actualizar path
    sed -i "s|/path/to/tuapp|$(pwd)|g" /usr/local/bin/tuapp-backup
    chmod +x /usr/local/bin/tuapp-backup
    
    # Configurar cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/tuapp-backup") | crontab -
    
    log_info "✅ Backup automático configurado (diario a las 2 AM)"
}

# Función para generar reporte de backups
generate_report() {
    log_step "Generando reporte de backups..."
    
    local report_file="$BACKUP_DIR/backup_report_$(date +%Y%m%d).html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Reporte de Backups - TuAppDeAccesorios</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .success { color: green; }
        .error { color: red; }
        .warning { color: orange; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Reporte de Backups - TuAppDeAccesorios</h1>
        <p>Fecha: $(date)</p>
    </div>
    
    <div class="section">
        <h2>Estado de Backups</h2>
        <table>
            <tr><th>Componente</th><th>Último Backup</th><th>Tamaño</th><th>Estado</th></tr>
EOF
    
    # PostgreSQL
    local latest_pg=$(ls -t $BACKUP_DIR/postgres_backup_*.sql.gz 2>/dev/null | head -1)
    if [ -n "$latest_pg" ]; then
        local pg_size=$(stat -f%z "$latest_pg" 2>/dev/null || stat -c%s "$latest_pg" 2>/dev/null)
        echo "            <tr><td>PostgreSQL</td><td>$(basename $latest_pg)</td><td>$pg_size bytes</td><td class=\"success\">✅ OK</td></tr>" >> "$report_file"
    else
        echo "            <tr><td>PostgreSQL</td><td>-</td><td>-</td><td class=\"error\">❌ Sin backup</td></tr>" >> "$report_file"
    fi
    
    # Redis
    local latest_redis=$(ls -t $BACKUP_DIR/redis_backup_*.rdb.gz 2>/dev/null | head -1)
    if [ -n "$latest_redis" ]; then
        local redis_size=$(stat -f%z "$latest_redis" 2>/dev/null || stat -c%s "$latest_redis" 2>/dev/null)
        echo "            <tr><td>Redis</td><td>$(basename $latest_redis)</td><td>$redis_size bytes</td><td class=\"success\">✅ OK</td></tr>" >> "$report_file"
    else
        echo "            <tr><td>Redis</td><td>-</td><td>-</td><td class=\"error\">❌ Sin backup</td></tr>" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF
        </table>
    </div>
    
    <div class="section">
        <h2>Configuración de Retención</h2>
        <p>Días de retención: $RETENTION_DAYS</p>
        <p>Directorio de backups: $BACKUP_DIR</p>
        <p>Bucket S3: $S3_BUCKET</p>
    </div>
    
    <div class="section">
        <h2>Archivos de Backup</h2>
        <pre>$(ls -la $BACKUP_DIR/*backup_* 2>/dev/null || echo "No hay backups disponibles")</pre>
    </div>
</body>
</html>
EOF
    
    log_info "📊 Reporte generado: $report_file"
}

# Función principal
main() {
    local action=${1:-backup}
    
    case $action in
        "backup")
            log_info "🔄 Iniciando proceso de backup completo..."
            backup_postgres
            backup_redis
            backup_configs
            upload_to_s3
            cleanup_old_backups
            verify_backups
            generate_report
            log_info "✅ Proceso de backup completado"
            ;;
        "restore")
            local postgres_file=$2
            local redis_file=$3
            
            if [ -n "$postgres_file" ]; then
                restore_postgres "$postgres_file"
            fi
            
            if [ -n "$redis_file" ]; then
                restore_redis "$redis_file"
            fi
            ;;
        "test")
            test_disaster_recovery
            ;;
        "schedule")
            schedule_backups
            ;;
        "verify")
            verify_backups
            ;;
        "report")
            generate_report
            ;;
        *)
            echo "Uso: $0 [backup|restore|test|schedule|verify|report]"
            echo ""
            echo "Comandos:"
            echo "  backup   - Crear backup completo"
            echo "  restore  - Restaurar desde backup"
            echo "  test     - Test de disaster recovery"
            echo "  schedule - Configurar backup automático"
            echo "  verify   - Verificar integridad de backups"
            echo "  report   - Generar reporte de backups"
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@"