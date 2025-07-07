#!/bin/bash

# Script para configurar directorios de producción
echo "📁 CONFIGURANDO DIRECTORIOS DE PRODUCCIÓN"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar que se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script debe ejecutarse como root${NC}"
   exit 1
fi

# Variables
APP_USER="tuapp"
APP_GROUP="tuapp"
BASE_DIR="/opt/tuapp"
DATA_DIR="$BASE_DIR/data"
LOGS_DIR="$BASE_DIR/logs"
BACKUPS_DIR="$BASE_DIR/backups"
CONFIG_DIR="$BASE_DIR/config"

echo "1. CREANDO USUARIO Y GRUPO DE LA APLICACIÓN..."
echo "--------------------------------------------"

# Crear grupo si no existe
if ! getent group $APP_GROUP > /dev/null 2>&1; then
    groupadd $APP_GROUP
    echo -e "${GREEN}✓ Grupo $APP_GROUP creado${NC}"
else
    echo -e "${GREEN}✓ Grupo $APP_GROUP ya existe${NC}"
fi

# Crear usuario si no existe
if ! id $APP_USER > /dev/null 2>&1; then
    useradd -r -g $APP_GROUP -d $BASE_DIR -s /bin/bash $APP_USER
    echo -e "${GREEN}✓ Usuario $APP_USER creado${NC}"
else
    echo -e "${GREEN}✓ Usuario $APP_USER ya existe${NC}"
fi

echo ""
echo "2. CREANDO ESTRUCTURA DE DIRECTORIOS..."
echo "-------------------------------------"

# Crear directorios principales
directories=(
    "$BASE_DIR"
    "$DATA_DIR"
    "$DATA_DIR/postgres"
    "$DATA_DIR/redis"
    "$LOGS_DIR"
    "$LOGS_DIR/nginx"
    "$LOGS_DIR/backend"
    "$LOGS_DIR/postgres"
    "$BACKUPS_DIR"
    "$BACKUPS_DIR/postgres"
    "$BACKUPS_DIR/redis"
    "$CONFIG_DIR"
    "$CONFIG_DIR/nginx"
    "$CONFIG_DIR/ssl"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✓ Directorio $dir creado${NC}"
    else
        echo -e "${GREEN}✓ Directorio $dir ya existe${NC}"
    fi
done

echo ""
echo "3. CONFIGURANDO PERMISOS..."
echo "-------------------------"

# Configurar ownership
chown -R $APP_USER:$APP_GROUP $BASE_DIR

# Configurar permisos específicos
chmod 755 $BASE_DIR
chmod 755 $DATA_DIR
chmod 700 $DATA_DIR/postgres    # Solo el usuario de la app puede acceder
chmod 755 $DATA_DIR/redis
chmod 755 $LOGS_DIR
chmod 755 $LOGS_DIR/nginx
chmod 755 $LOGS_DIR/backend
chmod 755 $LOGS_DIR/postgres
chmod 750 $BACKUPS_DIR          # Lectura/escritura solo para el usuario y grupo
chmod 750 $BACKUPS_DIR/postgres
chmod 750 $BACKUPS_DIR/redis
chmod 755 $CONFIG_DIR
chmod 755 $CONFIG_DIR/nginx
chmod 700 $CONFIG_DIR/ssl       # Solo el usuario de la app puede acceder a SSL

echo -e "${GREEN}✓ Permisos configurados${NC}"

echo ""
echo "4. CONFIGURANDO LOGROTATE..."
echo "--------------------------"

# Configurar logrotate para logs de la aplicación
cat > /etc/logrotate.d/tuapp << 'EOF'
/opt/tuapp/logs/backend/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 tuapp tuapp
    postrotate
        docker-compose -f /opt/tuapp/docker-compose.prod.yml restart backend > /dev/null 2>&1 || true
    endscript
}

/opt/tuapp/logs/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 tuapp tuapp
    postrotate
        docker-compose -f /opt/tuapp/docker-compose.prod.yml exec nginx nginx -s reload > /dev/null 2>&1 || true
    endscript
}

/opt/tuapp/logs/postgres/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 tuapp tuapp
}
EOF

echo -e "${GREEN}✓ Logrotate configurado${NC}"

echo ""
echo "5. CONFIGURANDO SYSTEMD SERVICE..."
echo "--------------------------------"

# Crear servicio systemd para la aplicación
cat > /etc/systemd/system/tuapp.service << EOF
[Unit]
Description=TuAppDeAccesorios Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
ExecReload=/usr/bin/docker-compose -f docker-compose.prod.yml restart
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Habilitar pero no iniciar el servicio
systemctl daemon-reload
systemctl enable tuapp.service

echo -e "${GREEN}✓ Servicio systemd configurado${NC}"

echo ""
echo "6. CONFIGURANDO BACKUP AUTOMÁTICO..."
echo "----------------------------------"

# Script de backup externo adicional
cat > $BASE_DIR/backup-external.sh << 'BACKUP_SCRIPT'
#!/bin/bash

# Script de backup externo para TuAppDeAccesorios
BACKUP_DIR="/opt/tuapp/backups"
EXTERNAL_BACKUP="/backup/external/tuapp"  # Cambiar por tu directorio de backup externo
DATE=$(date +%Y%m%d_%H%M%S)

# Crear directorio externo si no existe
mkdir -p $EXTERNAL_BACKUP

# Backup de volúmenes Docker
echo "Creating external backup at $DATE"

# Crear backup completo incluyendo volúmenes
docker run --rm \
    -v tuapp_postgres_data:/source/postgres:ro \
    -v tuapp_redis_data:/source/redis:ro \
    -v $EXTERNAL_BACKUP:/backup \
    alpine tar czf /backup/volumes-backup-$DATE.tar.gz -C /source .

# Backup específico de PostgreSQL (dump)
docker-compose -f /opt/tuapp/docker-compose.prod.yml exec -T db \
    pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > $EXTERNAL_BACKUP/postgres-dump-$DATE.sql.gz

# Mantener solo los últimos 7 backups externos
find $EXTERNAL_BACKUP -name "*.tar.gz" -mtime +7 -delete
find $EXTERNAL_BACKUP -name "*.sql.gz" -mtime +7 -delete

echo "External backup completed: $DATE"
BACKUP_SCRIPT

chmod +x $BASE_DIR/backup-external.sh
chown $APP_USER:$APP_GROUP $BASE_DIR/backup-external.sh

# Configurar cron para backup externo semanal
cat > /etc/cron.d/tuapp-backup << 'CRON_CONFIG'
# Backup externo semanal de TuAppDeAccesorios
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Ejecutar backup externo todos los domingos a las 2:00 AM
0 2 * * 0 tuapp /opt/tuapp/backup-external.sh >/dev/null 2>&1
CRON_CONFIG

echo -e "${GREEN}✓ Backup automático configurado${NC}"

echo ""
echo "7. CONFIGURANDO MONITOREO DE ESPACIO..."
echo "------------------------------------"

# Script para monitorear espacio en disco
cat > $BASE_DIR/check-disk-space.sh << 'DISK_SCRIPT'
#!/bin/bash

# Verificar espacio en disco para TuAppDeAccesorios
THRESHOLD=85  # Porcentaje de umbral de alerta
EMAIL="admin@tudominio.com"  # Cambiar por email del administrador

# Verificar espacio en /opt/tuapp
USAGE=$(df /opt/tuapp | tail -1 | awk '{print $5}' | sed 's/%//')

if [ $USAGE -gt $THRESHOLD ]; then
    echo "WARNING: Disk usage is ${USAGE}% on /opt/tuapp"
    
    # Enviar alerta por email si está configurado
    if command -v mail &> /dev/null; then
        echo "Disk usage on /opt/tuapp has exceeded ${THRESHOLD}%. Current usage: ${USAGE}%" | \
            mail -s "TuAppDeAccesorios: Disk Space Alert" $EMAIL
    fi
    
    # Log de alerta
    echo "$(date): Disk usage alert - ${USAGE}%" >> /opt/tuapp/logs/disk-usage.log
fi

# Verificar tamaño de backups
BACKUP_SIZE=$(du -sh /opt/tuapp/backups | cut -f1)
echo "$(date): Backup directory size: $BACKUP_SIZE" >> /opt/tuapp/logs/backup-size.log
DISK_SCRIPT

chmod +x $BASE_DIR/check-disk-space.sh
chown $APP_USER:$APP_GROUP $BASE_DIR/check-disk-space.sh

# Configurar cron para verificación diaria de espacio
echo "0 6 * * * tuapp /opt/tuapp/check-disk-space.sh >/dev/null 2>&1" >> /etc/cron.d/tuapp-backup

echo -e "${GREEN}✓ Monitoreo de espacio configurado${NC}"

echo ""
echo "8. CONFIGURANDO FIREWALL..."
echo "-------------------------"

# Configurar UFW si está disponible
if command -v ufw &> /dev/null; then
    # Permitir SSH
    ufw allow ssh
    
    # Permitir HTTP y HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Denegar acceso directo a bases de datos desde el exterior
    ufw deny 5432/tcp
    ufw deny 6379/tcp
    
    echo -e "${GREEN}✓ Reglas de firewall configuradas${NC}"
    echo -e "${YELLOW}⚠ Ejecutar 'ufw enable' para activar el firewall${NC}"
else
    echo -e "${YELLOW}⚠ UFW no está instalado${NC}"
fi

echo ""
echo "========================================"
echo "CONFIGURACIÓN DE DIRECTORIOS COMPLETADA"
echo "========================================"
echo ""
echo -e "${GREEN}✓ Usuario y grupo creados: $APP_USER:$APP_GROUP${NC}"
echo -e "${GREEN}✓ Directorios configurados en: $BASE_DIR${NC}"
echo -e "${GREEN}✓ Permisos aplicados correctamente${NC}"
echo -e "${GREEN}✓ Logrotate configurado${NC}"
echo -e "${GREEN}✓ Servicio systemd configurado${NC}"
echo -e "${GREEN}✓ Backup automático configurado${NC}"
echo -e "${GREEN}✓ Monitoreo de espacio configurado${NC}"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASOS:${NC}"
echo "1. Copiar archivos de la aplicación a $BASE_DIR"
echo "2. Configurar variables de entorno en $BASE_DIR/.env.prod"
echo "3. Iniciar la aplicación: systemctl start tuapp"
echo "4. Verificar estado: systemctl status tuapp"
echo "5. Ver logs: docker-compose -f $BASE_DIR/docker-compose.prod.yml logs"
echo ""
echo -e "${YELLOW}ESTRUCTURA CREADA:${NC}"
tree $BASE_DIR 2>/dev/null || ls -la $BASE_DIR