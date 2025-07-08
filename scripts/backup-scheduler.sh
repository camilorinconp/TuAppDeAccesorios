#!/bin/bash

# ============================================
# BACKUP SCHEDULER SCRIPT
# Sistema de backups automáticos cifrados
# ============================================

set -euo pipefail

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"
LOG_FILE="/var/log/tuapp/backup-scheduler.log"
LOCK_FILE="/tmp/tuapp-backup.lock"

# Configuración desde variables de entorno
BACKUP_TYPE="${BACKUP_TYPE:-full}"
BACKUP_COMPRESS="${BACKUP_COMPRESS:-true}"
BACKUP_ENCRYPT="${BACKUP_ENCRYPT:-true}"
BACKUP_UPLOAD_S3="${BACKUP_UPLOAD_S3:-true}"
BACKUP_CLEANUP_ENABLED="${BACKUP_CLEANUP_ENABLED:-true}"
BACKUP_NOTIFICATION_ENABLED="${BACKUP_NOTIFICATION_ENABLED:-true}"

# URLs de notificación
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

# Configuración de Docker
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-docker-compose.yml}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-backend}"

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de logging
log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $timestamp - $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $timestamp - $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $timestamp - $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Función para verificar dependencias
check_dependencies() {
    log "INFO" "Checking dependencies..."
    
    local missing_deps=()
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # Verificar curl para notificaciones
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    # Verificar jq para procesamiento JSON
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "ERROR" "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    log "INFO" "All dependencies satisfied"
}

# Función para verificar que el servicio esté funcionando
check_service_health() {
    log "INFO" "Checking service health..."
    
    # Verificar que el contenedor esté corriendo
    if ! docker-compose -f "$BACKEND_DIR/$DOCKER_COMPOSE_FILE" ps "$BACKEND_SERVICE_NAME" | grep -q "Up"; then
        log "ERROR" "Backend service is not running"
        return 1
    fi
    
    # Verificar endpoint de health
    local health_url="http://localhost:8000/health"
    if ! curl -s -f "$health_url" > /dev/null; then
        log "WARN" "Health endpoint not responding, but service is running"
    fi
    
    log "INFO" "Service health check passed"
    return 0
}

# Función para adquirir lock
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid=$(cat "$LOCK_FILE")
        if kill -0 "$lock_pid" 2>/dev/null; then
            log "WARN" "Backup already running (PID: $lock_pid)"
            exit 1
        else
            log "INFO" "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
    log "INFO" "Lock acquired (PID: $$)"
}

# Función para liberar lock
release_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log "INFO" "Lock released"
    fi
}

# Trap para limpiar al salir
trap release_lock EXIT

# Función para crear backup
create_backup() {
    log "INFO" "Starting backup creation..."
    
    local backup_payload=$(cat <<EOF
{
    "backup_type": "$BACKUP_TYPE",
    "compress": $BACKUP_COMPRESS,
    "encrypt": $BACKUP_ENCRYPT,
    "upload_to_s3": $BACKUP_UPLOAD_S3
}
EOF
)
    
    # Ejecutar backup via API del contenedor
    local backup_response
    backup_response=$(docker-compose -f "$BACKEND_DIR/$DOCKER_COMPOSE_FILE" exec -T "$BACKEND_SERVICE_NAME" \
        python -c "
import asyncio
import sys
sys.path.append('/app')
from app.security.backup_manager import backup_manager
import json

async def main():
    try:
        metadata = await backup_manager.create_database_backup(
            backup_type='$BACKUP_TYPE',
            compress=$BACKUP_COMPRESS,
            encrypt=$BACKUP_ENCRYPT,
            upload_to_s3=$BACKUP_UPLOAD_S3
        )
        
        if metadata:
            result = {
                'success': True,
                'backup_id': metadata.backup_id,
                'timestamp': metadata.timestamp.isoformat(),
                'file_size': metadata.file_size,
                's3_location': metadata.s3_location,
                'local_path': metadata.local_path
            }
        else:
            result = {'success': False, 'error': 'Backup creation failed'}
        
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))

asyncio.run(main())
")
    
    if [ $? -eq 0 ]; then
        local success=$(echo "$backup_response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            local backup_id=$(echo "$backup_response" | jq -r '.backup_id')
            local file_size=$(echo "$backup_response" | jq -r '.file_size')
            local file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)
            
            log "INFO" "Backup created successfully: $backup_id (${file_size_mb}MB)"
            
            # Retornar información del backup
            echo "$backup_response"
            return 0
        else
            local error=$(echo "$backup_response" | jq -r '.error')
            log "ERROR" "Backup creation failed: $error"
            return 1
        fi
    else
        log "ERROR" "Failed to execute backup command"
        return 1
    fi
}

# Función para limpiar backups antiguos
cleanup_old_backups() {
    if [ "$BACKUP_CLEANUP_ENABLED" != "true" ]; then
        log "INFO" "Backup cleanup disabled, skipping..."
        return 0
    fi
    
    log "INFO" "Starting backup cleanup..."
    
    local cleanup_response
    cleanup_response=$(docker-compose -f "$BACKEND_DIR/$DOCKER_COMPOSE_FILE" exec -T "$BACKEND_SERVICE_NAME" \
        python -c "
import asyncio
import sys
sys.path.append('/app')
from app.security.backup_manager import backup_manager
import json

async def main():
    try:
        result = await backup_manager.cleanup_old_backups()
        result['success'] = True
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))

asyncio.run(main())
")
    
    if [ $? -eq 0 ]; then
        local success=$(echo "$cleanup_response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            local local_deleted=$(echo "$cleanup_response" | jq -r '.local_deleted')
            local s3_deleted=$(echo "$cleanup_response" | jq -r '.s3_deleted')
            
            log "INFO" "Cleanup completed: $local_deleted local, $s3_deleted S3 backups removed"
            return 0
        else
            local error=$(echo "$cleanup_response" | jq -r '.error')
            log "WARN" "Backup cleanup failed: $error"
            return 1
        fi
    else
        log "WARN" "Failed to execute cleanup command"
        return 1
    fi
}

# Función para enviar notificación a Slack
send_slack_notification() {
    local message="$1"
    local color="$2"  # good, warning, danger
    
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        return 0
    fi
    
    local payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "TuApp Backup Notification",
            "text": "$message",
            "footer": "TuApp Backup System",
            "ts": $(date +%s)
        }
    ]
}
EOF
)
    
    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" > /dev/null
}

# Función para enviar notificación a Discord
send_discord_notification() {
    local message="$1"
    local color="$2"  # decimal color code
    
    if [ -z "$DISCORD_WEBHOOK_URL" ]; then
        return 0
    fi
    
    local payload=$(cat <<EOF
{
    "embeds": [
        {
            "title": "TuApp Backup Notification",
            "description": "$message",
            "color": $color,
            "footer": {
                "text": "TuApp Backup System"
            },
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
        }
    ]
}
EOF
)
    
    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$DISCORD_WEBHOOK_URL" > /dev/null
}

# Función para enviar email
send_email_notification() {
    local subject="$1"
    local message="$2"
    
    if [ -z "$ALERT_EMAIL" ]; then
        return 0
    fi
    
    # Usar sendmail si está disponible
    if command -v sendmail &> /dev/null; then
        {
            echo "To: $ALERT_EMAIL"
            echo "Subject: $subject"
            echo "Content-Type: text/plain; charset=UTF-8"
            echo ""
            echo "$message"
        } | sendmail "$ALERT_EMAIL"
    fi
}

# Función para enviar notificaciones
send_notifications() {
    local message="$1"
    local status="$2"  # success, warning, error
    
    if [ "$BACKUP_NOTIFICATION_ENABLED" != "true" ]; then
        return 0
    fi
    
    case "$status" in
        "success")
            send_slack_notification "$message" "good"
            send_discord_notification "$message" "65280"  # Green
            send_email_notification "TuApp Backup Success" "$message"
            ;;
        "warning")
            send_slack_notification "$message" "warning"
            send_discord_notification "$message" "16776960"  # Yellow
            send_email_notification "TuApp Backup Warning" "$message"
            ;;
        "error")
            send_slack_notification "$message" "danger"
            send_discord_notification "$message" "16711680"  # Red
            send_email_notification "TuApp Backup Error" "$message"
            ;;
    esac
}

# Función principal
main() {
    log "INFO" "Starting TuApp backup scheduler..."
    
    # Crear directorio de logs si no existe
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Verificar dependencias
    check_dependencies
    
    # Adquirir lock
    acquire_lock
    
    # Verificar estado del servicio
    if ! check_service_health; then
        local error_msg="Service health check failed. Backup aborted."
        log "ERROR" "$error_msg"
        send_notifications "$error_msg" "error"
        exit 1
    fi
    
    # Crear backup
    local backup_start_time=$(date +%s)
    local backup_result
    
    if backup_result=$(create_backup); then
        local backup_end_time=$(date +%s)
        local backup_duration=$((backup_end_time - backup_start_time))
        
        local backup_id=$(echo "$backup_result" | jq -r '.backup_id')
        local file_size=$(echo "$backup_result" | jq -r '.file_size')
        local file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)
        local s3_location=$(echo "$backup_result" | jq -r '.s3_location')
        
        local success_msg="✅ Backup completed successfully!
Backup ID: $backup_id
Size: ${file_size_mb}MB
Duration: ${backup_duration}s
Type: $BACKUP_TYPE
Encrypted: $BACKUP_ENCRYPT
Compressed: $BACKUP_COMPRESS
S3 Upload: $([ "$s3_location" != "null" ] && echo "✅" || echo "❌")"
        
        log "INFO" "Backup completed in ${backup_duration}s"
        send_notifications "$success_msg" "success"
        
        # Limpiar backups antiguos
        cleanup_old_backups
        
    else
        local error_msg="❌ Backup creation failed!
Type: $BACKUP_TYPE
Time: $(date)
Please check system logs for details."
        
        log "ERROR" "Backup creation failed"
        send_notifications "$error_msg" "error"
        exit 1
    fi
    
    log "INFO" "Backup scheduler completed successfully"
}

# Función de ayuda
show_help() {
    cat << EOF
TuApp Backup Scheduler

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -t, --type TYPE         Backup type (full, incremental, differential)
    -c, --compress BOOL     Enable compression (true/false)
    -e, --encrypt BOOL      Enable encryption (true/false)
    -s, --s3 BOOL          Upload to S3 (true/false)
    --cleanup BOOL         Enable cleanup (true/false)
    --notify BOOL          Enable notifications (true/false)
    --dry-run              Show what would be done without executing

ENVIRONMENT VARIABLES:
    BACKUP_TYPE                 Backup type (default: full)
    BACKUP_COMPRESS            Enable compression (default: true)
    BACKUP_ENCRYPT             Enable encryption (default: true)
    BACKUP_UPLOAD_S3           Upload to S3 (default: true)
    BACKUP_CLEANUP_ENABLED     Enable cleanup (default: true)
    BACKUP_NOTIFICATION_ENABLED Enable notifications (default: true)
    SLACK_WEBHOOK_URL          Slack webhook URL for notifications
    DISCORD_WEBHOOK_URL        Discord webhook URL for notifications
    ALERT_EMAIL               Email address for notifications

EXAMPLES:
    # Create full encrypted backup with S3 upload
    $0

    # Create incremental backup without S3 upload
    $0 --type incremental --s3 false

    # Create backup with notifications disabled
    $0 --notify false

    # Dry run to see what would be done
    $0 --dry-run

EOF
}

# Procesamiento de argumentos de línea de comandos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -c|--compress)
            BACKUP_COMPRESS="$2"
            shift 2
            ;;
        -e|--encrypt)
            BACKUP_ENCRYPT="$2"
            shift 2
            ;;
        -s|--s3)
            BACKUP_UPLOAD_S3="$2"
            shift 2
            ;;
        --cleanup)
            BACKUP_CLEANUP_ENABLED="$2"
            shift 2
            ;;
        --notify)
            BACKUP_NOTIFICATION_ENABLED="$2"
            shift 2
            ;;
        --dry-run)
            echo "DRY RUN MODE - Would execute backup with:"
            echo "  Type: $BACKUP_TYPE"
            echo "  Compress: $BACKUP_COMPRESS"
            echo "  Encrypt: $BACKUP_ENCRYPT"
            echo "  Upload S3: $BACKUP_UPLOAD_S3"
            echo "  Cleanup: $BACKUP_CLEANUP_ENABLED"
            echo "  Notifications: $BACKUP_NOTIFICATION_ENABLED"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ejecutar función principal
main "$@"