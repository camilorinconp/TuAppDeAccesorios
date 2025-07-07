#!/bin/bash

# ==========================================
# Setup de Backups Cifrados para TuAppDeAccesorios
# ==========================================

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/var/backups/tuapp"
ENCRYPTION_KEY_FILE="/etc/tuapp/backup-encryption.key"
BACKUP_RETENTION_DAYS=30
AWS_REGION="${AWS_REGION:-us-east-1}"

# Verificar que estamos ejecutando como root o con sudo
if [[ $EUID -ne 0 ]]; then
   error "Este script debe ejecutarse como root o con sudo"
   exit 1
fi

log "🔒 Configurando sistema de backups cifrados para TuAppDeAccesorios..."

# ==========================================
# 1. Crear directorios necesarios
# ==========================================
log "📁 Creando directorios de backup..."

mkdir -p "$BACKUP_DIR"/{database,files,logs}
mkdir -p /etc/tuapp
mkdir -p /var/log/tuapp-backups

# ==========================================
# 2. Generar clave de cifrado para backups
# ==========================================
log "🔑 Generando clave de cifrado para backups..."

if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
    # Generar clave aleatoria de 256 bits
    openssl rand -base64 32 > "$ENCRYPTION_KEY_FILE"
    chmod 600 "$ENCRYPTION_KEY_FILE"
    chown root:root "$ENCRYPTION_KEY_FILE"
    
    log "✅ Clave de cifrado generada en $ENCRYPTION_KEY_FILE"
    
    # Mostrar la clave para que el usuario la guarde en lugar seguro
    warn "IMPORTANTE: Guarde esta clave en un lugar seguro. Sin ella, no podrá recuperar los backups cifrados:"
    echo -e "${BLUE}$(cat "$ENCRYPTION_KEY_FILE")${NC}"
    warn "Esta clave también debe agregarse a las variables de entorno como BACKUP_ENCRYPTION_KEY"
else
    log "✅ Clave de cifrado ya existe"
fi

# ==========================================
# 3. Instalar herramientas necesarias
# ==========================================
log "🛠️  Instalando herramientas de backup y cifrado..."

# Actualizar repositorios
apt-get update -qq

# Instalar herramientas necesarias
apt-get install -y \
    postgresql-client \
    awscli \
    gnupg \
    gzip \
    openssl \
    coreutils \
    jq

# Verificar instalación
if ! command -v pg_dump &> /dev/null; then
    error "pg_dump no está disponible. Verifique la instalación de postgresql-client"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    warn "AWS CLI no está disponible. Los backups a S3 no funcionarán"
fi

# ==========================================
# 4. Crear script de backup principal
# ==========================================
log "📝 Creando script de backup principal..."

cat > /usr/local/bin/tuapp-backup.sh << 'EOF'
#!/bin/bash

# TuApp Encrypted Backup Script
set -euo pipefail

# Variables de configuración
BACKUP_DIR="/var/backups/tuapp"
ENCRYPTION_KEY_FILE="/etc/tuapp/backup-encryption.key"
LOG_FILE="/var/log/tuapp-backups/backup.log"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
AWS_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-tuapp_production}"
POSTGRES_USER="${POSTGRES_USER:-tuapp_prod_user}"

# Logging
log_backup() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_backup() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Verificar prerrequisitos
if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
    error_backup "Clave de cifrado no encontrada en $ENCRYPTION_KEY_FILE"
    exit 1
fi

ENCRYPTION_KEY=$(cat "$ENCRYPTION_KEY_FILE")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="tuapp_backup_$TIMESTAMP"

log_backup "🔄 Iniciando backup cifrado: $BACKUP_NAME"

# ==========================================
# Backup de Base de Datos
# ==========================================
log_backup "📊 Realizando backup de base de datos..."

DB_BACKUP_FILE="$BACKUP_DIR/database/${BACKUP_NAME}_database.sql"
DB_ENCRYPTED_FILE="$BACKUP_DIR/database/${BACKUP_NAME}_database.sql.enc"

# Crear backup de PostgreSQL
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --verbose \
    --clean \
    --create \
    --if-exists \
    > "$DB_BACKUP_FILE" 2>> "$LOG_FILE"

if [[ $? -eq 0 ]]; then
    log_backup "✅ Backup de base de datos completado"
    
    # Cifrar backup de base de datos
    log_backup "🔒 Cifrando backup de base de datos..."
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$DB_BACKUP_FILE" \
        -out "$DB_ENCRYPTED_FILE" \
        -pass pass:"$ENCRYPTION_KEY"
    
    # Verificar cifrado
    if [[ -f "$DB_ENCRYPTED_FILE" ]]; then
        log_backup "✅ Backup de base de datos cifrado exitosamente"
        # Eliminar archivo sin cifrar
        rm "$DB_BACKUP_FILE"
        
        # Calcular hash para integridad
        DB_HASH=$(sha256sum "$DB_ENCRYPTED_FILE" | cut -d' ' -f1)
        echo "$DB_HASH" > "$DB_ENCRYPTED_FILE.sha256"
        log_backup "📝 Hash de integridad: $DB_HASH"
    else
        error_backup "Error cifrando backup de base de datos"
        exit 1
    fi
else
    error_backup "Error en backup de base de datos"
    exit 1
fi

unset PGPASSWORD

# ==========================================
# Backup de Archivos
# ==========================================
log_backup "📁 Realizando backup de archivos de aplicación..."

FILES_BACKUP_DIR="$BACKUP_DIR/files"
FILES_ARCHIVE="$FILES_BACKUP_DIR/${BACKUP_NAME}_files.tar.gz"
FILES_ENCRYPTED="$FILES_BACKUP_DIR/${BACKUP_NAME}_files.tar.gz.enc"

# Crear archivo tar con archivos importantes
tar -czf "$FILES_ARCHIVE" \
    -C "/" \
    --exclude="node_modules" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".git" \
    --exclude="logs" \
    --exclude="*.log" \
    opt/tuapp/ \
    etc/tuapp/ 2>> "$LOG_FILE" || true

# Cifrar archivo de files
if [[ -f "$FILES_ARCHIVE" ]]; then
    log_backup "🔒 Cifrando backup de archivos..."
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$FILES_ARCHIVE" \
        -out "$FILES_ENCRYPTED" \
        -pass pass:"$ENCRYPTION_KEY"
    
    if [[ -f "$FILES_ENCRYPTED" ]]; then
        log_backup "✅ Backup de archivos cifrado exitosamente"
        rm "$FILES_ARCHIVE"
        
        # Hash de integridad
        FILES_HASH=$(sha256sum "$FILES_ENCRYPTED" | cut -d' ' -f1)
        echo "$FILES_HASH" > "$FILES_ENCRYPTED.sha256"
        log_backup "📝 Hash de archivos: $FILES_HASH"
    else
        error_backup "Error cifrando backup de archivos"
    fi
fi

# ==========================================
# Backup de Configuración Docker
# ==========================================
log_backup "🐳 Realizando backup de configuración Docker..."

DOCKER_BACKUP_DIR="$BACKUP_DIR/docker"
mkdir -p "$DOCKER_BACKUP_DIR"

# Backup de volúmenes Docker importantes
docker run --rm \
    -v tuapp_postgres_data:/source:ro \
    -v "$DOCKER_BACKUP_DIR":/backup \
    alpine:latest \
    tar -czf "/backup/${BACKUP_NAME}_docker_volumes.tar.gz" -C /source . 2>> "$LOG_FILE" || true

# Cifrar backup de Docker si existe
DOCKER_ARCHIVE="$DOCKER_BACKUP_DIR/${BACKUP_NAME}_docker_volumes.tar.gz"
if [[ -f "$DOCKER_ARCHIVE" ]]; then
    DOCKER_ENCRYPTED="$DOCKER_BACKUP_DIR/${BACKUP_NAME}_docker_volumes.tar.gz.enc"
    
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$DOCKER_ARCHIVE" \
        -out "$DOCKER_ENCRYPTED" \
        -pass pass:"$ENCRYPTION_KEY"
    
    if [[ -f "$DOCKER_ENCRYPTED" ]]; then
        log_backup "✅ Backup de Docker cifrado exitosamente"
        rm "$DOCKER_ARCHIVE"
        
        DOCKER_HASH=$(sha256sum "$DOCKER_ENCRYPTED" | cut -d' ' -f1)
        echo "$DOCKER_HASH" > "$DOCKER_ENCRYPTED.sha256"
    fi
fi

# ==========================================
# Subir a S3 si está configurado
# ==========================================
if [[ -n "$AWS_S3_BUCKET" ]]; then
    log_backup "☁️  Subiendo backups a S3..."
    
    # Subir archivos cifrados a S3
    for encrypted_file in "$BACKUP_DIR"/*/*"$TIMESTAMP"*.enc; do
        if [[ -f "$encrypted_file" ]]; then
            aws s3 cp "$encrypted_file" "s3://$AWS_S3_BUCKET/backups/$(basename "$encrypted_file")" \
                --storage-class STANDARD_IA \
                --region "$AWS_REGION" || error_backup "Error subiendo $encrypted_file a S3"
            
            # Subir también el hash
            hash_file="${encrypted_file}.sha256"
            if [[ -f "$hash_file" ]]; then
                aws s3 cp "$hash_file" "s3://$AWS_S3_BUCKET/backups/$(basename "$hash_file")" \
                    --region "$AWS_REGION" || true
            fi
        fi
    done
    
    log_backup "✅ Backups subidos a S3"
fi

# ==========================================
# Limpiar backups antiguos
# ==========================================
log_backup "🧹 Limpiando backups antiguos (>$RETENTION_DAYS días)..."

find "$BACKUP_DIR" -name "tuapp_backup_*" -type f -mtime +$RETENTION_DAYS -delete 2>> "$LOG_FILE" || true

# Limpiar también en S3 si está configurado
if [[ -n "$AWS_S3_BUCKET" ]]; then
    # Configurar lifecycle policy para limpieza automática en S3
    aws s3api put-bucket-lifecycle-configuration \
        --bucket "$AWS_S3_BUCKET" \
        --lifecycle-configuration '{
            "Rules": [{
                "ID": "tuapp-backup-cleanup",
                "Status": "Enabled",
                "Filter": {"Prefix": "backups/"},
                "Expiration": {"Days": '$RETENTION_DAYS'}
            }]
        }' --region "$AWS_REGION" 2>> "$LOG_FILE" || true
fi

# ==========================================
# Reporte final
# ==========================================
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_backup "✅ Backup completado exitosamente"
log_backup "📊 Tamaño total de backups: $BACKUP_SIZE"
log_backup "🏷️  Nombre del backup: $BACKUP_NAME"

# Crear resumen del backup
cat > "$BACKUP_DIR/logs/${BACKUP_NAME}_summary.json" << SUMMARY
{
  "backup_name": "$BACKUP_NAME",
  "timestamp": "$(date -Iseconds)",
  "database_backup": "$(ls "$BACKUP_DIR"/database/*"$TIMESTAMP"*.enc 2>/dev/null | head -1 || echo 'none')",
  "files_backup": "$(ls "$BACKUP_DIR"/files/*"$TIMESTAMP"*.enc 2>/dev/null | head -1 || echo 'none')",
  "docker_backup": "$(ls "$BACKUP_DIR"/docker/*"$TIMESTAMP"*.enc 2>/dev/null | head -1 || echo 'none')",
  "total_size": "$BACKUP_SIZE",
  "s3_upload": "$([ -n "$AWS_S3_BUCKET" ] && echo 'true' || echo 'false')",
  "retention_days": $RETENTION_DAYS
}
SUMMARY

log_backup "📄 Resumen guardado en: $BACKUP_DIR/logs/${BACKUP_NAME}_summary.json"
EOF

# Hacer ejecutable el script
chmod +x /usr/local/bin/tuapp-backup.sh

# ==========================================
# 5. Crear script de restauración
# ==========================================
log "🔄 Creando script de restauración..."

cat > /usr/local/bin/tuapp-restore.sh << 'EOF'
#!/bin/bash

# TuApp Encrypted Restore Script
set -euo pipefail

# Variables
BACKUP_DIR="/var/backups/tuapp"
ENCRYPTION_KEY_FILE="/etc/tuapp/backup-encryption.key"
LOG_FILE="/var/log/tuapp-backups/restore.log"

# Logging
log_restore() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_restore() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Función de ayuda
show_help() {
    cat << HELP
TuApp Encrypted Restore Script

Uso: $0 [OPCIONES] BACKUP_NAME

OPCIONES:
    -d, --database-only     Restaurar solo la base de datos
    -f, --files-only        Restaurar solo los archivos
    -v, --verify            Solo verificar integridad del backup
    -h, --help              Mostrar esta ayuda

BACKUP_NAME: Nombre del backup (ej: tuapp_backup_20241207_143000)

Ejemplos:
    $0 tuapp_backup_20241207_143000                 # Restaurar todo
    $0 -d tuapp_backup_20241207_143000              # Solo base de datos
    $0 -v tuapp_backup_20241207_143000              # Solo verificar
HELP
}

# Parsear argumentos
DATABASE_ONLY=false
FILES_ONLY=false
VERIFY_ONLY=false
BACKUP_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--database-only)
            DATABASE_ONLY=true
            shift
            ;;
        -f|--files-only)
            FILES_ONLY=true
            shift
            ;;
        -v|--verify)
            VERIFY_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            BACKUP_NAME="$1"
            shift
            ;;
    esac
done

if [[ -z "$BACKUP_NAME" ]]; then
    error_restore "Debe especificar un nombre de backup"
    show_help
    exit 1
fi

# Verificar prerrequisitos
if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
    error_restore "Clave de cifrado no encontrada en $ENCRYPTION_KEY_FILE"
    exit 1
fi

ENCRYPTION_KEY=$(cat "$ENCRYPTION_KEY_FILE")

log_restore "🔄 Iniciando restauración de backup: $BACKUP_NAME"

# ==========================================
# Verificar integridad de backups
# ==========================================
verify_backup_integrity() {
    local backup_file="$1"
    local hash_file="${backup_file}.sha256"
    
    if [[ ! -f "$hash_file" ]]; then
        error_restore "Archivo de hash no encontrado: $hash_file"
        return 1
    fi
    
    local expected_hash=$(cat "$hash_file")
    local actual_hash=$(sha256sum "$backup_file" | cut -d' ' -f1)
    
    if [[ "$expected_hash" == "$actual_hash" ]]; then
        log_restore "✅ Integridad verificada: $(basename "$backup_file")"
        return 0
    else
        error_restore "❌ Integridad falló: $(basename "$backup_file")"
        error_restore "   Esperado: $expected_hash"
        error_restore "   Actual:   $actual_hash"
        return 1
    fi
}

# ==========================================
# Restaurar base de datos
# ==========================================
restore_database() {
    local db_encrypted_file="$BACKUP_DIR/database/${BACKUP_NAME}_database.sql.enc"
    
    if [[ ! -f "$db_encrypted_file" ]]; then
        error_restore "Backup de base de datos no encontrado: $db_encrypted_file"
        return 1
    fi
    
    log_restore "🔍 Verificando integridad del backup de base de datos..."
    if ! verify_backup_integrity "$db_encrypted_file"; then
        return 1
    fi
    
    log_restore "🔓 Descifrando backup de base de datos..."
    local db_decrypted_file="${db_encrypted_file%.enc}"
    
    openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
        -in "$db_encrypted_file" \
        -out "$db_decrypted_file" \
        -pass pass:"$ENCRYPTION_KEY"
    
    if [[ ! -f "$db_decrypted_file" ]]; then
        error_restore "Error descifrando backup de base de datos"
        return 1
    fi
    
    log_restore "📊 Restaurando base de datos..."
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql \
        -h "${POSTGRES_HOST:-localhost}" \
        -p "${POSTGRES_PORT:-5432}" \
        -U "${POSTGRES_USER:-tuapp_prod_user}" \
        -d "${POSTGRES_DB:-tuapp_production}" \
        -f "$db_decrypted_file" >> "$LOG_FILE" 2>&1
    
    local restore_result=$?
    
    # Limpiar archivo descifrado
    rm "$db_decrypted_file"
    unset PGPASSWORD
    
    if [[ $restore_result -eq 0 ]]; then
        log_restore "✅ Base de datos restaurada exitosamente"
        return 0
    else
        error_restore "❌ Error restaurando base de datos"
        return 1
    fi
}

# ==========================================
# Restaurar archivos
# ==========================================
restore_files() {
    local files_encrypted_file="$BACKUP_DIR/files/${BACKUP_NAME}_files.tar.gz.enc"
    
    if [[ ! -f "$files_encrypted_file" ]]; then
        error_restore "Backup de archivos no encontrado: $files_encrypted_file"
        return 1
    fi
    
    log_restore "🔍 Verificando integridad del backup de archivos..."
    if ! verify_backup_integrity "$files_encrypted_file"; then
        return 1
    fi
    
    log_restore "🔓 Descifrando backup de archivos..."
    local files_decrypted_file="${files_encrypted_file%.enc}"
    
    openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
        -in "$files_encrypted_file" \
        -out "$files_decrypted_file" \
        -pass pass:"$ENCRYPTION_KEY"
    
    if [[ ! -f "$files_decrypted_file" ]]; then
        error_restore "Error descifrando backup de archivos"
        return 1
    fi
    
    log_restore "📁 Restaurando archivos..."
    tar -xzf "$files_decrypted_file" -C "/" >> "$LOG_FILE" 2>&1
    
    local restore_result=$?
    
    # Limpiar archivo descifrado
    rm "$files_decrypted_file"
    
    if [[ $restore_result -eq 0 ]]; then
        log_restore "✅ Archivos restaurados exitosamente"
        return 0
    else
        error_restore "❌ Error restaurando archivos"
        return 1
    fi
}

# ==========================================
# Verificar solo integridad
# ==========================================
if [[ "$VERIFY_ONLY" == true ]]; then
    log_restore "🔍 Verificando integridad de backups..."
    
    errors=0
    
    # Verificar backup de base de datos
    db_file="$BACKUP_DIR/database/${BACKUP_NAME}_database.sql.enc"
    if [[ -f "$db_file" ]]; then
        verify_backup_integrity "$db_file" || ((errors++))
    else
        error_restore "Backup de base de datos no encontrado"
        ((errors++))
    fi
    
    # Verificar backup de archivos
    files_file="$BACKUP_DIR/files/${BACKUP_NAME}_files.tar.gz.enc"
    if [[ -f "$files_file" ]]; then
        verify_backup_integrity "$files_file" || ((errors++))
    else
        error_restore "Backup de archivos no encontrado"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_restore "✅ Todos los backups tienen integridad correcta"
        exit 0
    else
        error_restore "❌ Se encontraron $errors errores de integridad"
        exit 1
    fi
fi

# ==========================================
# Ejecutar restauración
# ==========================================
errors=0

if [[ "$FILES_ONLY" != true ]]; then
    restore_database || ((errors++))
fi

if [[ "$DATABASE_ONLY" != true ]]; then
    restore_files || ((errors++))
fi

if [[ $errors -eq 0 ]]; then
    log_restore "🎉 Restauración completada exitosamente"
    exit 0
else
    error_restore "❌ Restauración completada con $errors errores"
    exit 1
fi
EOF

chmod +x /usr/local/bin/tuapp-restore.sh

# ==========================================
# 6. Configurar cron para backups automáticos
# ==========================================
log "⏰ Configurando backups automáticos..."

# Crear cron job para backup diario a las 2 AM
cat > /etc/cron.d/tuapp-backup << 'EOF'
# TuApp Automated Encrypted Backups
# Ejecutar backup diario a las 2:00 AM
0 2 * * * root /usr/local/bin/tuapp-backup.sh

# Verificar integridad semanal los domingos a las 3:00 AM
0 3 * * 0 root find /var/backups/tuapp -name "tuapp_backup_*_summary.json" -mtime -7 -exec /usr/local/bin/tuapp-restore.sh -v $(basename {} _summary.json) \; >> /var/log/tuapp-backups/weekly-verify.log 2>&1
EOF

# ==========================================
# 7. Configurar logrotate
# ==========================================
log "📝 Configurando rotación de logs..."

cat > /etc/logrotate.d/tuapp-backups << 'EOF'
/var/log/tuapp-backups/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    copytruncate
    notifempty
    su root root
}
EOF

# ==========================================
# 8. Configurar permisos
# ==========================================
log "🔐 Configurando permisos de seguridad..."

# Permisos restrictivos para directorio de backups
chown -R root:root "$BACKUP_DIR"
chmod -R 700 "$BACKUP_DIR"

# Permisos para logs
chown -R root:root /var/log/tuapp-backups
chmod -R 750 /var/log/tuapp-backups

# Permisos para configuración
chown root:root /etc/tuapp
chmod 700 /etc/tuapp
chmod 600 "$ENCRYPTION_KEY_FILE"

# ==========================================
# 9. Crear archivo de variables de entorno
# ==========================================
log "📄 Creando archivo de variables de entorno..."

cat > /etc/tuapp/backup.env << EOF
# TuApp Backup Configuration
BACKUP_RETENTION_DAYS=$BACKUP_RETENTION_DAYS
BACKUP_S3_BUCKET=${BACKUP_S3_BUCKET:-}
AWS_REGION=$AWS_REGION
POSTGRES_HOST=\${POSTGRES_HOST:-localhost}
POSTGRES_PORT=\${POSTGRES_PORT:-5432}
POSTGRES_DB=\${POSTGRES_DB:-tuapp_production}
POSTGRES_USER=\${POSTGRES_USER:-tuapp_prod_user}
POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
BACKUP_ENCRYPTION_KEY=$(cat "$ENCRYPTION_KEY_FILE")
EOF

chmod 600 /etc/tuapp/backup.env

# ==========================================
# 10. Crear script de monitoreo
# ==========================================
log "📊 Creando script de monitoreo de backups..."

cat > /usr/local/bin/tuapp-backup-monitor.sh << 'EOF'
#!/bin/bash

# TuApp Backup Monitoring Script
BACKUP_DIR="/var/backups/tuapp"
LOG_FILE="/var/log/tuapp-backups/monitor.log"

# Verificar que hay backups recientes (últimas 48 horas)
recent_backups=$(find "$BACKUP_DIR" -name "tuapp_backup_*" -mtime -2 | wc -l)

if [[ $recent_backups -eq 0 ]]; then
    echo "[$(date)] ERROR: No se encontraron backups recientes" >> "$LOG_FILE"
    # Aquí se puede agregar notificación (email, Slack, etc.)
    exit 1
else
    echo "[$(date)] OK: $recent_backups backups recientes encontrados" >> "$LOG_FILE"
fi

# Verificar espacio en disco
available_space=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
if [[ $available_space -lt 1048576 ]]; then  # Menos de 1GB
    echo "[$(date)] WARNING: Poco espacio disponible para backups: ${available_space}KB" >> "$LOG_FILE"
fi

# Verificar integridad del último backup
latest_backup=$(find "$BACKUP_DIR" -name "tuapp_backup_*_summary.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
if [[ -n "$latest_backup" ]]; then
    backup_name=$(basename "$latest_backup" _summary.json)
    /usr/local/bin/tuapp-restore.sh -v "$backup_name" >> "$LOG_FILE" 2>&1
fi
EOF

chmod +x /usr/local/bin/tuapp-backup-monitor.sh

# Agregar monitoreo cada 6 horas
echo "0 */6 * * * root /usr/local/bin/tuapp-backup-monitor.sh" >> /etc/cron.d/tuapp-backup

# ==========================================
# 11. Configuración final y tests
# ==========================================
log "🧪 Ejecutando tests de configuración..."

# Test de cifrado
if openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in <(echo "test encryption") \
    -pass pass:"$(cat "$ENCRYPTION_KEY_FILE")" | \
   openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
    -pass pass:"$(cat "$ENCRYPTION_KEY_FILE")" > /dev/null; then
    log "✅ Test de cifrado exitoso"
else
    error "❌ Test de cifrado falló"
    exit 1
fi

# Verificar cron
if crontab -l | grep -q tuapp-backup; then
    log "✅ Cron jobs configurados correctamente"
else
    warn "⚠️  Cron jobs no detectados, verificar manualmente"
fi

# ==========================================
# Resumen final
# ==========================================
log "🎉 Configuración de backups cifrados completada exitosamente!"

echo
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    RESUMEN DE CONFIGURACIÓN DE BACKUPS${NC}"
echo -e "${BLUE}===========================================${NC}"
echo
echo -e "${GREEN}✅ Directorios creados:${NC}"
echo "   - $BACKUP_DIR (backups cifrados)"
echo "   - /var/log/tuapp-backups (logs)"
echo "   - /etc/tuapp (configuración)"
echo
echo -e "${GREEN}✅ Scripts instalados:${NC}"
echo "   - /usr/local/bin/tuapp-backup.sh (backup principal)"
echo "   - /usr/local/bin/tuapp-restore.sh (restauración)"
echo "   - /usr/local/bin/tuapp-backup-monitor.sh (monitoreo)"
echo
echo -e "${GREEN}✅ Cron jobs configurados:${NC}"
echo "   - Backup diario a las 2:00 AM"
echo "   - Verificación semanal los domingos"
echo "   - Monitoreo cada 6 horas"
echo
echo -e "${GREEN}✅ Clave de cifrado:${NC}"
echo "   - Ubicación: $ENCRYPTION_KEY_FILE"
echo "   - Permisos: 600 (solo root)"
echo
echo -e "${YELLOW}📋 Próximos pasos:${NC}"
echo "1. Configurar variables de entorno de PostgreSQL"
echo "2. Configurar AWS credentials si usa S3"
echo "3. Probar backup manual: sudo /usr/local/bin/tuapp-backup.sh"
echo "4. Probar restauración: sudo /usr/local/bin/tuapp-restore.sh -v BACKUP_NAME"
echo
echo -e "${RED}⚠️  IMPORTANTE:${NC}"
echo "- Guarde la clave de cifrado en un lugar seguro"
echo "- Configure variables de entorno necesarias"
echo "- Teste los backups antes de confiar en ellos"
echo

# Mostrar comandos útiles
echo -e "${BLUE}Comandos útiles:${NC}"
echo "  Ver backups:     ls -la $BACKUP_DIR/*/"
echo "  Backup manual:   sudo /usr/local/bin/tuapp-backup.sh"
echo "  Verificar:       sudo /usr/local/bin/tuapp-restore.sh -v BACKUP_NAME"
echo "  Logs:           tail -f /var/log/tuapp-backups/backup.log"
echo "  Monitoreo:      sudo /usr/local/bin/tuapp-backup-monitor.sh"
EOF