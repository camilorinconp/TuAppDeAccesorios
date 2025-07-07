#!/bin/bash

# ============================================
# SCRIPT DE CONFIGURACIÓN DE BACKUPS AUTOMÁTICOS
# TuAppDeAccesorios
# ============================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "💾 Configurando Sistema de Backups Automáticos"
echo "=============================================="

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   log_error "Este script debe ejecutarse como root (sudo)"
   exit 1
fi

# Cargar variables de entorno
if [[ -f ".env.production" ]]; then
    source .env.production
    log_info "Variables de entorno cargadas desde .env.production"
else
    log_error "No se encontró el archivo .env.production"
    log_info "Ejecuta primero: ./scripts/generate-production-env.sh"
    exit 1
fi

# Crear directorios necesarios
log_info "Creando estructura de directorios..."
mkdir -p /opt/tuapp/backups/{database,logs,config}
mkdir -p /opt/tuapp/scripts
chown -R root:root /opt/tuapp

# Configurar variables por defecto
BACKUP_DIR="/opt/tuapp/backups"
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
BACKUP_SCHEDULE=${BACKUP_SCHEDULE:-"0 2 * * *"}

log_info "Directorio de backups: $BACKUP_DIR"
log_info "Retención de backups: $BACKUP_RETENTION_DAYS días"
log_info "Programación: $BACKUP_SCHEDULE"

# Instalar dependencias
log_info "Instalando dependencias..."
apt-get update -qq
apt-get install -y postgresql-client-15 gzip bzip2 aws-cli

# Crear script principal de backup
log_info "Creando script de backup principal..."
cat > /opt/tuapp/scripts/backup-database.sh << 'EOF'
#!/bin/bash

# ============================================
# SCRIPT DE BACKUP DE BASE DE DATOS
# TuAppDeAccesorios
# ============================================

set -e

# Configuración
BACKUP_DIR="/opt/tuapp/backups/database"
CONFIG_DIR="/opt/tuapp/backups/config"
LOG_FILE="/opt/tuapp/backups/logs/backup.log"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Crear función de logging
log_backup() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Función para limpiar en caso de error
cleanup_on_error() {
    log_backup "ERROR: Backup falló. Limpiando archivos temporales..."
    rm -f "$BACKUP_DIR/backup_$(date +'%Y-%m-%d_%H-%M-%S')_incomplete.sql.gz"
    exit 1
}

# Configurar trap para errores
trap cleanup_on_error ERR

# Crear directorio de logs si no existe
mkdir -p "$(dirname "$LOG_FILE")"

log_backup "=== INICIANDO BACKUP ==="
log_backup "Directorio de backups: $BACKUP_DIR"
log_backup "Retención: $RETENTION_DAYS días"

# Cargar variables de entorno
if [[ -f "/opt/tuapp/.env.production" ]]; then
    source /opt/tuapp/.env.production
    log_backup "Variables de entorno cargadas"
else
    log_backup "ERROR: No se encontró archivo .env.production"
    exit 1
fi

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Generar nombre del archivo de backup
TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"
TEMP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}_incomplete.sql.gz"

log_backup "Creando backup: $BACKUP_FILE"

# Realizar backup de la base de datos
log_backup "Iniciando dump de PostgreSQL..."
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h localhost \
    -p 5433 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --verbose \
    --clean \
    --if-exists \
    --create \
    --format=plain \
    --no-password \
    2>>"$LOG_FILE" | gzip > "$TEMP_FILE"

# Verificar que el backup se creó correctamente
if [[ -f "$TEMP_FILE" && -s "$TEMP_FILE" ]]; then
    mv "$TEMP_FILE" "$BACKUP_FILE"
    log_backup "Backup completado exitosamente"
    
    # Obtener tamaño del archivo
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_backup "Tamaño del backup: $BACKUP_SIZE"
    
    # Verificar integridad del archivo comprimido
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_backup "Integridad del backup verificada"
    else
        log_backup "ERROR: Backup corrupto"
        exit 1
    fi
else
    log_backup "ERROR: Backup falló - archivo no creado o vacío"
    exit 1
fi

# Crear archivo de metadatos
cat > "$BACKUP_DIR/backup_${TIMESTAMP}.info" << EOL
# Información del Backup
# ======================
Fecha: $(date)
Servidor: $(hostname)
Base de datos: $POSTGRES_DB
Usuario: $POSTGRES_USER
Tamaño: $BACKUP_SIZE
Archivo: backup_${TIMESTAMP}.sql.gz
Comando: pg_dump -h localhost -p 5433 -U $POSTGRES_USER -d $POSTGRES_DB
EOL

log_backup "Archivo de metadatos creado"

# Limpiar backups antiguos
log_backup "Limpiando backups antiguos (más de $RETENTION_DAYS días)..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "backup_*.info" -mtime +$RETENTION_DAYS -delete

CLEANED_COUNT=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS | wc -l)
if [[ $CLEANED_COUNT -gt 0 ]]; then
    log_backup "Limpiados $CLEANED_COUNT backups antiguos"
else
    log_backup "No hay backups antiguos para limpiar"
fi

# Listar backups actuales
CURRENT_BACKUPS=$(ls -la "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | wc -l)
log_backup "Backups actuales: $CURRENT_BACKUPS"

# Subir a AWS S3 si está configurado
if [[ -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" && -n "$BACKUP_S3_BUCKET" ]]; then
    log_backup "Subiendo backup a S3..."
    aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_S3_BUCKET/database/" --region "${AWS_REGION:-us-east-1}"
    aws s3 cp "$BACKUP_DIR/backup_${TIMESTAMP}.info" "s3://$BACKUP_S3_BUCKET/database/" --region "${AWS_REGION:-us-east-1}"
    log_backup "Backup subido a S3 exitosamente"
else
    log_backup "Configuración S3 no encontrada - backup solo local"
fi

# Enviar notificación por email si está configurado
if [[ -n "$SMTP_HOST" && -n "$ALERT_EMAIL" ]]; then
    log_backup "Enviando notificación por email..."
    echo "Backup de TuAppDeAccesorios completado exitosamente.
    
Fecha: $(date)
Servidor: $(hostname)
Base de datos: $POSTGRES_DB
Tamaño: $BACKUP_SIZE
Archivo: backup_${TIMESTAMP}.sql.gz
Backups totales: $CURRENT_BACKUPS

Este es un mensaje automático." | \
    mail -s "Backup TuAppDeAccesorios - Exitoso" "$ALERT_EMAIL"
    log_backup "Notificación enviada"
fi

log_backup "=== BACKUP COMPLETADO ==="
log_backup ""
EOF

# Hacer ejecutable el script
chmod +x /opt/tuapp/scripts/backup-database.sh

# Crear script de restauración
log_info "Creando script de restauración..."
cat > /opt/tuapp/scripts/restore-database.sh << 'EOF'
#!/bin/bash

# ============================================
# SCRIPT DE RESTAURACIÓN DE BASE DE DATOS
# TuAppDeAccesorios
# ============================================

set -e

# Configuración
BACKUP_DIR="/opt/tuapp/backups/database"
LOG_FILE="/opt/tuapp/backups/logs/restore.log"

# Crear función de logging
log_restore() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [OPCIONES] <archivo_backup>"
    echo ""
    echo "Opciones:"
    echo "  -l, --list          Listar backups disponibles"
    echo "  -f, --force         Forzar restauración sin confirmación"
    echo "  -h, --help          Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 -l                                    # Listar backups"
    echo "  $0 backup_2024-01-15_02-00-00.sql.gz   # Restaurar backup específico"
    echo "  $0 -f backup_2024-01-15_02-00-00.sql.gz # Restaurar sin confirmación"
}

# Función para listar backups
list_backups() {
    echo "Backups disponibles en $BACKUP_DIR:"
    echo "=================================="
    ls -la "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | while read -r line; do
        filename=$(echo "$line" | awk '{print $9}')
        if [[ -n "$filename" ]]; then
            basename_file=$(basename "$filename")
            info_file="$BACKUP_DIR/${basename_file%.sql.gz}.info"
            if [[ -f "$info_file" ]]; then
                echo "📁 $basename_file"
                grep -E "^Fecha:|^Tamaño:" "$info_file" | sed 's/^/   /'
                echo ""
            else
                echo "📁 $basename_file (sin información adicional)"
            fi
        fi
    done
}

# Procesar argumentos
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            list_backups
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Verificar que se proporcionó un archivo de backup
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Error: Debes especificar un archivo de backup"
    echo ""
    show_help
    exit 1
fi

# Verificar que el archivo existe
if [[ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]]; then
    log_restore "ERROR: Archivo de backup no encontrado: $BACKUP_DIR/$BACKUP_FILE"
    echo ""
    list_backups
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p "$(dirname "$LOG_FILE")"

log_restore "=== INICIANDO RESTAURACIÓN ==="
log_restore "Archivo de backup: $BACKUP_FILE"

# Cargar variables de entorno
if [[ -f "/opt/tuapp/.env.production" ]]; then
    source /opt/tuapp/.env.production
    log_restore "Variables de entorno cargadas"
else
    log_restore "ERROR: No se encontró archivo .env.production"
    exit 1
fi

# Verificar integridad del backup
log_restore "Verificando integridad del backup..."
if gzip -t "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null; then
    log_restore "Integridad del backup verificada"
else
    log_restore "ERROR: Backup corrupto"
    exit 1
fi

# Confirmación si no se forzó
if [[ "$FORCE" != true ]]; then
    echo ""
    echo "⚠️  ADVERTENCIA: Esta operación:"
    echo "   - Eliminará todos los datos actuales de la base de datos"
    echo "   - Restaurará los datos desde el backup seleccionado"
    echo "   - Esta acción NO se puede deshacer"
    echo ""
    read -p "¿Estás seguro de que deseas continuar? (escribir 'SI' para confirmar): " confirm
    if [[ "$confirm" != "SI" ]]; then
        log_restore "Restauración cancelada por el usuario"
        exit 0
    fi
fi

# Crear backup de emergencia antes de restaurar
log_restore "Creando backup de emergencia antes de restaurar..."
EMERGENCY_BACKUP="/opt/tuapp/backups/database/emergency_$(date +'%Y-%m-%d_%H-%M-%S').sql.gz"
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h localhost \
    -p 5433 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --create \
    --format=plain \
    --no-password \
    2>>"$LOG_FILE" | gzip > "$EMERGENCY_BACKUP"

log_restore "Backup de emergencia creado: $EMERGENCY_BACKUP"

# Restaurar base de datos
log_restore "Iniciando restauración de la base de datos..."
zcat "$BACKUP_DIR/$BACKUP_FILE" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h localhost \
    -p 5433 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v ON_ERROR_STOP=1 \
    2>>"$LOG_FILE"

if [[ $? -eq 0 ]]; then
    log_restore "Restauración completada exitosamente"
else
    log_restore "ERROR: Falló la restauración"
    log_restore "Backup de emergencia disponible en: $EMERGENCY_BACKUP"
    exit 1
fi

# Verificar restauración
log_restore "Verificando restauración..."
TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5433 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
log_restore "Tablas restauradas: $TABLE_COUNT"

log_restore "=== RESTAURACIÓN COMPLETADA ==="
log_restore ""
EOF

# Hacer ejecutable el script de restauración
chmod +x /opt/tuapp/scripts/restore-database.sh

# Crear script de monitoreo de backups
log_info "Creando script de monitoreo..."
cat > /opt/tuapp/scripts/monitor-backups.sh << 'EOF'
#!/bin/bash

# ============================================
# SCRIPT DE MONITOREO DE BACKUPS
# TuAppDeAccesorios
# ============================================

BACKUP_DIR="/opt/tuapp/backups/database"
LOG_FILE="/opt/tuapp/backups/logs/monitor.log"
MAX_BACKUP_AGE_HOURS=25

# Función de logging
log_monitor() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Crear directorio de logs si no existe
mkdir -p "$(dirname "$LOG_FILE")"

log_monitor "=== MONITOREO DE BACKUPS ==="

# Verificar si existe al menos un backup reciente
RECENT_BACKUP=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime -1 | head -1)

if [[ -n "$RECENT_BACKUP" ]]; then
    BACKUP_AGE=$(stat -c %Y "$RECENT_BACKUP")
    CURRENT_TIME=$(date +%s)
    AGE_HOURS=$(( (CURRENT_TIME - BACKUP_AGE) / 3600 ))
    
    if [[ $AGE_HOURS -lt $MAX_BACKUP_AGE_HOURS ]]; then
        log_monitor "✅ Backup reciente encontrado (${AGE_HOURS}h de antigüedad)"
        exit 0
    else
        log_monitor "⚠️ Backup más reciente tiene ${AGE_HOURS}h de antigüedad"
    fi
else
    log_monitor "❌ No se encontraron backups recientes"
fi

# Enviar alerta si está configurado
if [[ -n "$ALERT_EMAIL" ]]; then
    echo "ALERTA: Problema con backups de TuAppDeAccesorios

Servidor: $(hostname)
Fecha: $(date)
Problema: No se encontraron backups recientes (últimas 24 horas)

Por favor, verificar el sistema de backups.

Este es un mensaje automático." | \
    mail -s "ALERTA: Problema con Backups TuAppDeAccesorios" "$ALERT_EMAIL"
    log_monitor "Alerta enviada por email"
fi

log_monitor "=== MONITOREO COMPLETADO ==="
exit 1
EOF

# Hacer ejecutable el script de monitoreo
chmod +x /opt/tuapp/scripts/monitor-backups.sh

# Copiar variables de entorno al directorio de scripts
cp .env.production /opt/tuapp/.env.production

# Configurar cron jobs
log_info "Configurando tareas programadas..."
cat > /etc/cron.d/tuapp-backups << EOF
# Backup automático de TuAppDeAccesorios
$BACKUP_SCHEDULE root /opt/tuapp/scripts/backup-database.sh

# Monitoreo de backups (cada 6 horas)
0 */6 * * * root /opt/tuapp/scripts/monitor-backups.sh

# Limpieza de logs (semanal)
0 3 * * 0 root find /opt/tuapp/backups/logs -name "*.log" -mtime +7 -delete
EOF

chmod 644 /etc/cron.d/tuapp-backups

# Crear script de gestión de backups
log_info "Creando script de gestión..."
cat > /opt/tuapp/scripts/manage-backups.sh << 'EOF'
#!/bin/bash

# ============================================
# SCRIPT DE GESTIÓN DE BACKUPS
# TuAppDeAccesorios
# ============================================

show_help() {
    echo "Gestión de Backups - TuAppDeAccesorios"
    echo "====================================="
    echo ""
    echo "Uso: $0 [COMANDO] [OPCIONES]"
    echo ""
    echo "Comandos:"
    echo "  backup              Crear backup manual"
    echo "  list                Listar backups disponibles"
    echo "  restore <archivo>   Restaurar desde backup"
    echo "  monitor             Verificar estado de backups"
    echo "  clean               Limpiar backups antiguos"
    echo "  status              Mostrar estado del sistema"
    echo "  help                Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 backup                           # Crear backup manual"
    echo "  $0 list                             # Listar backups"
    echo "  $0 restore backup_2024-01-15.sql.gz # Restaurar backup"
    echo "  $0 monitor                          # Verificar backups"
}

case "$1" in
    backup)
        /opt/tuapp/scripts/backup-database.sh
        ;;
    list)
        /opt/tuapp/scripts/restore-database.sh --list
        ;;
    restore)
        if [[ -z "$2" ]]; then
            echo "Error: Debes especificar un archivo de backup"
            echo "Usa: $0 list para ver backups disponibles"
            exit 1
        fi
        /opt/tuapp/scripts/restore-database.sh "$2"
        ;;
    monitor)
        /opt/tuapp/scripts/monitor-backups.sh
        ;;
    clean)
        echo "Limpiando backups antiguos..."
        find /opt/tuapp/backups/database -name "backup_*.sql.gz" -mtime +${BACKUP_RETENTION_DAYS:-30} -delete
        find /opt/tuapp/backups/database -name "backup_*.info" -mtime +${BACKUP_RETENTION_DAYS:-30} -delete
        echo "Limpieza completada"
        ;;
    status)
        echo "Estado del Sistema de Backups"
        echo "============================="
        echo "Directorio: /opt/tuapp/backups/database"
        echo "Backups totales: $(ls -1 /opt/tuapp/backups/database/backup_*.sql.gz 2>/dev/null | wc -l)"
        echo "Último backup: $(ls -t /opt/tuapp/backups/database/backup_*.sql.gz 2>/dev/null | head -1 | xargs ls -la 2>/dev/null | awk '{print $6, $7, $8, $9}' || echo 'No encontrado')"
        echo "Espacio usado: $(du -sh /opt/tuapp/backups 2>/dev/null | cut -f1)"
        echo "Programación: $(grep backup /etc/cron.d/tuapp-backups | cut -d' ' -f1-5)"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Error: Comando no reconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
EOF

chmod +x /opt/tuapp/scripts/manage-backups.sh

# Crear enlace simbólico para fácil acceso
ln -sf /opt/tuapp/scripts/manage-backups.sh /usr/local/bin/tuapp-backup

# Configurar logrotate para los logs de backup
log_info "Configurando rotación de logs..."
cat > /etc/logrotate.d/tuapp-backups << EOF
/opt/tuapp/backups/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

# Prueba inicial
log_info "Realizando prueba inicial del sistema de backups..."
/opt/tuapp/scripts/monitor-backups.sh || true

log_success "Sistema de backups configurado exitosamente"

echo
echo "🎉 ¡Configuración de Backups Completada!"
echo "========================================"
echo
echo "📋 Resumen de configuración:"
echo "  - Directorio de backups: /opt/tuapp/backups"
echo "  - Programación: $BACKUP_SCHEDULE"
echo "  - Retención: $BACKUP_RETENTION_DAYS días"
echo "  - Monitoreo: Cada 6 horas"
echo "  - Logs: /opt/tuapp/backups/logs/"
echo
echo "🔧 Comandos disponibles:"
echo "  - tuapp-backup backup      # Crear backup manual"
echo "  - tuapp-backup list        # Listar backups"
echo "  - tuapp-backup restore     # Restaurar backup"
echo "  - tuapp-backup monitor     # Verificar estado"
echo "  - tuapp-backup status      # Estado del sistema"
echo
echo "📁 Archivos creados:"
echo "  - /opt/tuapp/scripts/backup-database.sh"
echo "  - /opt/tuapp/scripts/restore-database.sh"
echo "  - /opt/tuapp/scripts/monitor-backups.sh"
echo "  - /opt/tuapp/scripts/manage-backups.sh"
echo "  - /etc/cron.d/tuapp-backups"
echo
echo "🚀 Próximos pasos:"
echo "  1. Ejecutar primer backup: tuapp-backup backup"
echo "  2. Verificar funcionamiento: tuapp-backup status"
echo "  3. Configurar S3 (opcional): Editar .env.production"
echo
log_success "¡Sistema de backups listo para producción!"
EOF