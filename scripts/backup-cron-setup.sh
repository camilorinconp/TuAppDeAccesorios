#!/bin/bash

# ============================================
# CRON SETUP SCRIPT PARA BACKUPS AUTOMÁTICOS
# Configura tareas programadas para backups
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup-scheduler.sh"
CRON_LOG="/var/log/tuapp/cron.log"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message"
            ;;
    esac
}

# Función para verificar si el usuario actual puede usar cron
check_cron_permissions() {
    if ! command -v crontab &> /dev/null; then
        log "ERROR" "crontab command not found. Please install cron."
        exit 1
    fi
    
    # Intentar listar crontab para verificar permisos
    if ! crontab -l >/dev/null 2>&1; then
        log "WARN" "No existing crontab found or permission issues. This is normal for first setup."
    fi
    
    log "INFO" "Cron permissions verified"
}

# Función para crear directorio de logs
setup_logging() {
    local log_dir=$(dirname "$CRON_LOG")
    
    if [ ! -d "$log_dir" ]; then
        log "INFO" "Creating log directory: $log_dir"
        sudo mkdir -p "$log_dir"
        sudo chown $USER:$USER "$log_dir"
    fi
    
    if [ ! -f "$CRON_LOG" ]; then
        touch "$CRON_LOG"
    fi
    
    log "INFO" "Logging configured: $CRON_LOG"
}

# Función para mostrar configuraciones disponibles
show_schedule_options() {
    cat << EOF

Available backup schedule options:

1. Daily at 2:00 AM
   - Full backup every day
   - Recommended for small to medium databases

2. Daily at 2:00 AM + Weekly full backup
   - Incremental backups daily
   - Full backup on Sundays
   - Recommended for larger databases

3. Every 6 hours
   - Incremental backups every 6 hours
   - Full backup daily at 2:00 AM
   - Recommended for high-activity systems

4. Custom schedule
   - Define your own cron schedule

5. Production schedule (recommended)
   - Full backup: Daily at 2:00 AM
   - Incremental backup: Every 6 hours
   - Cleanup: Weekly on Sundays at 4:00 AM

EOF
}

# Función para configurar backup diario
setup_daily_backup() {
    local cron_entry="0 2 * * * $BACKUP_SCRIPT --type full --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    
    log "INFO" "Setting up daily backup at 2:00 AM..."
    add_cron_entry "$cron_entry" "Daily full backup"
}

# Función para configurar backup diario + semanal
setup_daily_weekly_backup() {
    local daily_cron="0 2 * * 1-6 $BACKUP_SCRIPT --type incremental --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    local weekly_cron="0 2 * * 0 $BACKUP_SCRIPT --type full --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    
    log "INFO" "Setting up daily incremental + weekly full backup..."
    add_cron_entry "$daily_cron" "Daily incremental backup (Mon-Sat)"
    add_cron_entry "$weekly_cron" "Weekly full backup (Sunday)"
}

# Función para configurar backup cada 6 horas
setup_6hourly_backup() {
    local sixhourly_cron="0 */6 * * * $BACKUP_SCRIPT --type incremental --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    local daily_full_cron="0 2 * * * $BACKUP_SCRIPT --type full --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    
    log "INFO" "Setting up 6-hourly incremental + daily full backup..."
    add_cron_entry "$sixhourly_cron" "6-hourly incremental backup"
    add_cron_entry "$daily_full_cron" "Daily full backup"
}

# Función para configurar backup de producción
setup_production_backup() {
    local full_backup_cron="0 2 * * * $BACKUP_SCRIPT --type full --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    local incremental_cron="0 */6 * * * $BACKUP_SCRIPT --type incremental --compress true --encrypt true --s3 true >> $CRON_LOG 2>&1"
    local cleanup_cron="0 4 * * 0 $BACKUP_SCRIPT --cleanup true >> $CRON_LOG 2>&1"
    
    log "INFO" "Setting up production backup schedule..."
    add_cron_entry "$full_backup_cron" "Daily full backup"
    add_cron_entry "$incremental_cron" "6-hourly incremental backup"
    add_cron_entry "$cleanup_cron" "Weekly cleanup (Sunday 4:00 AM)"
}

# Función para configurar horario personalizado
setup_custom_backup() {
    echo "Enter your custom cron schedule (e.g., '0 2 * * *' for daily at 2 AM):"
    read -r custom_schedule
    
    echo "Enter backup type (full/incremental/differential):"
    read -r backup_type
    
    echo "Enable compression? (true/false):"
    read -r enable_compression
    
    echo "Enable encryption? (true/false):"
    read -r enable_encryption
    
    echo "Upload to S3? (true/false):"
    read -r upload_s3
    
    local custom_cron="$custom_schedule $BACKUP_SCRIPT --type $backup_type --compress $enable_compression --encrypt $enable_encryption --s3 $upload_s3 >> $CRON_LOG 2>&1"
    
    log "INFO" "Setting up custom backup schedule: $custom_schedule"
    add_cron_entry "$custom_cron" "Custom backup schedule"
}

# Función para agregar entrada al crontab
add_cron_entry() {
    local cron_entry="$1"
    local description="$2"
    
    # Obtener crontab actual
    local current_crontab
    current_crontab=$(crontab -l 2>/dev/null || echo "")
    
    # Verificar si la entrada ya existe
    if echo "$current_crontab" | grep -F "$BACKUP_SCRIPT" > /dev/null; then
        log "WARN" "Backup entries already exist in crontab. Use --remove first if you want to replace them."
        return 1
    fi
    
    # Agregar nueva entrada
    {
        echo "$current_crontab"
        echo "# TuApp Backup - $description"
        echo "$cron_entry"
        echo ""
    } | crontab -
    
    log "INFO" "Added cron entry: $description"
}

# Función para remover entradas de backup del crontab
remove_backup_cron() {
    log "INFO" "Removing existing backup cron entries..."
    
    local current_crontab
    current_crontab=$(crontab -l 2>/dev/null || echo "")
    
    if [ -z "$current_crontab" ]; then
        log "INFO" "No existing crontab found"
        return 0
    fi
    
    # Filtrar entradas que no contengan el script de backup
    local new_crontab
    new_crontab=$(echo "$current_crontab" | grep -v "$BACKUP_SCRIPT" | grep -v "# TuApp Backup")
    
    # Aplicar nuevo crontab
    echo "$new_crontab" | crontab -
    
    log "INFO" "Backup cron entries removed"
}

# Función para mostrar entradas actuales
show_current_cron() {
    log "INFO" "Current crontab entries:"
    echo
    crontab -l 2>/dev/null || echo "No crontab entries found"
    echo
}

# Función para verificar configuración de backup
verify_backup_config() {
    log "INFO" "Verifying backup configuration..."
    
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        log "ERROR" "Backup script not found: $BACKUP_SCRIPT"
        exit 1
    fi
    
    if [ ! -x "$BACKUP_SCRIPT" ]; then
        log "ERROR" "Backup script is not executable: $BACKUP_SCRIPT"
        exit 1
    fi
    
    # Verificar variables de entorno básicas
    local missing_vars=()
    
    if [ -z "${DATABASE_URL:-}" ]; then
        missing_vars+=("DATABASE_URL")
    fi
    
    if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
        missing_vars+=("BACKUP_ENCRYPTION_KEY")
    fi
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log "WARN" "Missing environment variables: ${missing_vars[*]}"
        log "WARN" "Make sure to set these in your .env file or environment"
    fi
    
    log "INFO" "Backup configuration verified"
}

# Función para mostrar ayuda
show_help() {
    cat << EOF
TuApp Backup Cron Setup

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -s, --setup TYPE        Setup backup schedule:
                           daily, daily-weekly, 6hourly, production, custom
    -r, --remove            Remove existing backup cron entries
    -l, --list              Show current cron entries
    -v, --verify            Verify backup configuration
    --dry-run              Show what would be done without executing

EXAMPLES:
    # Setup daily backup at 2:00 AM
    $0 --setup daily

    # Setup production schedule (recommended)
    $0 --setup production

    # Remove existing backup cron entries
    $0 --remove

    # Show current cron entries
    $0 --list

    # Verify configuration
    $0 --verify

BACKUP SCHEDULES:
    daily           Daily full backup at 2:00 AM
    daily-weekly    Daily incremental + Sunday full backup
    6hourly         Incremental every 6h + daily full backup
    production      Full daily + incremental 6h + weekly cleanup
    custom          Interactive custom schedule setup

EOF
}

# Función principal
main() {
    local action=""
    local schedule_type=""
    local dry_run=false
    
    # Procesar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--setup)
                action="setup"
                schedule_type="$2"
                shift 2
                ;;
            -r|--remove)
                action="remove"
                shift
                ;;
            -l|--list)
                action="list"
                shift
                ;;
            -v|--verify)
                action="verify"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Mostrar modo dry-run
    if [ "$dry_run" = true ]; then
        log "INFO" "DRY RUN MODE - No changes will be made"
    fi
    
    # Verificar permisos de cron
    check_cron_permissions
    
    # Ejecutar acción
    case "$action" in
        "setup")
            if [ "$dry_run" = false ]; then
                setup_logging
                verify_backup_config
            fi
            
            case "$schedule_type" in
                "daily")
                    if [ "$dry_run" = true ]; then
                        log "INFO" "Would setup daily backup at 2:00 AM"
                    else
                        setup_daily_backup
                    fi
                    ;;
                "daily-weekly")
                    if [ "$dry_run" = true ]; then
                        log "INFO" "Would setup daily incremental + weekly full backup"
                    else
                        setup_daily_weekly_backup
                    fi
                    ;;
                "6hourly")
                    if [ "$dry_run" = true ]; then
                        log "INFO" "Would setup 6-hourly incremental + daily full backup"
                    else
                        setup_6hourly_backup
                    fi
                    ;;
                "production")
                    if [ "$dry_run" = true ]; then
                        log "INFO" "Would setup production backup schedule"
                    else
                        setup_production_backup
                    fi
                    ;;
                "custom")
                    if [ "$dry_run" = true ]; then
                        log "INFO" "Would setup custom backup schedule (interactive)"
                    else
                        setup_custom_backup
                    fi
                    ;;
                *)
                    log "ERROR" "Invalid schedule type: $schedule_type"
                    show_schedule_options
                    exit 1
                    ;;
            esac
            ;;
        "remove")
            if [ "$dry_run" = true ]; then
                log "INFO" "Would remove existing backup cron entries"
            else
                remove_backup_cron
            fi
            ;;
        "list")
            show_current_cron
            ;;
        "verify")
            verify_backup_config
            ;;
        "")
            log "INFO" "No action specified. Use --help for usage information."
            show_schedule_options
            ;;
        *)
            log "ERROR" "Invalid action: $action"
            exit 1
            ;;
    esac
    
    if [ "$action" = "setup" ] && [ "$dry_run" = false ]; then
        log "INFO" "Backup schedule configured successfully!"
        log "INFO" "Logs will be written to: $CRON_LOG"
        log "INFO" "Use '$0 --list' to see current cron entries"
        log "INFO" "Use '$0 --remove' to remove backup entries"
        
        echo
        log "INFO" "Current crontab after setup:"
        show_current_cron
    fi
}

# Ejecutar función principal
main "$@"