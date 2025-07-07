#!/bin/bash

# Script para configurar auto-renovación de certificados Let's Encrypt
echo "🔐 CONFIGURACIÓN AUTO-RENOVACIÓN LET'S ENCRYPT"
echo "============================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuración
DOMAIN="${1:-tudominio.com}"
EMAIL="${2:-admin@tudominio.com}"
WEBROOT="/var/www/html"
NGINX_CONF_DIR="/etc/nginx/sites-available"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
BACKUP_DIR="/opt/ssl-backups"
LOG_FILE="/var/log/letsencrypt-renewal.log"

echo -e "${BLUE}Configurando auto-renovación para:${NC}"
echo "Dominio: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Verificar que se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script debe ejecutarse como root${NC}"
   exit 1
fi

echo "1. INSTALANDO CERTBOT..."
echo "----------------------"

# Instalar certbot y plugin nginx
if ! command -v certbot &> /dev/null; then
    apt update
    apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓ Certbot instalado${NC}"
else
    echo -e "${GREEN}✓ Certbot ya está instalado${NC}"
fi

echo ""
echo "2. CONFIGURANDO DIRECTORIO WEBROOT..."
echo "------------------------------------"

# Crear directorio webroot si no existe
mkdir -p $WEBROOT/.well-known/acme-challenge
chown -R www-data:www-data $WEBROOT
chmod -R 755 $WEBROOT

echo -e "${GREEN}✓ Directorio webroot configurado${NC}"

echo ""
echo "3. CONFIGURANDO NGINX BÁSICO..."
echo "-----------------------------"

# Configuración básica de nginx para el desafío HTTP-01
cat > $NGINX_CONF_DIR/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Let's Encrypt challenge
    location ^~ /.well-known/acme-challenge/ {
        root $WEBROOT;
        allow all;
    }
    
    # Redireccionar todo lo demás a HTTPS (después de obtener el certificado)
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# Configuración HTTPS (se activará después de obtener el certificado)
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # Certificados SSL (Let's Encrypt los configurará automáticamente)
    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    
    # Configuración SSL moderna y segura
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Otros headers de seguridad
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Configuración del proxy reverso hacia la aplicación
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Servir archivos estáticos del frontend
    location /static/ {
        alias /app/frontend/build/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Let's Encrypt challenge (mantener accesible)
    location ^~ /.well-known/acme-challenge/ {
        root $WEBROOT;
        allow all;
    }
}
EOF

# Habilitar configuración
ln -sf $NGINX_CONF_DIR/$DOMAIN /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo -e "${GREEN}✓ Configuración básica de Nginx creada${NC}"

echo ""
echo "4. OBTENIENDO CERTIFICADO INICIAL..."
echo "----------------------------------"

# Obtener certificado inicial
if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    echo "Obteniendo certificado inicial para $DOMAIN..."
    certbot certonly \
        --nginx \
        --non-interactive \
        --agree-tos \
        --email $EMAIL \
        --domains $DOMAIN,www.$DOMAIN \
        --expand
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Certificado inicial obtenido${NC}"
        nginx -t && systemctl reload nginx
    else
        echo -e "${RED}✗ Error obteniendo certificado inicial${NC}"
        echo "Verifica que:"
        echo "1. El dominio $DOMAIN apunte a esta IP"
        echo "2. Los puertos 80 y 443 estén abiertos"
        echo "3. Nginx esté funcionando correctamente"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Certificado ya existe${NC}"
fi

echo ""
echo "5. CONFIGURANDO SISTEMA DE BACKUP..."
echo "----------------------------------"

# Crear directorio de backups
mkdir -p $BACKUP_DIR
chmod 700 $BACKUP_DIR

# Script de backup de certificados
cat > /usr/local/bin/backup-ssl-certs.sh << 'BACKUP_SCRIPT'
#!/bin/bash

# Script de backup de certificados SSL
BACKUP_DIR="/opt/ssl-backups"
DATE=$(date +%Y%m%d_%H%M%S)
LETSENCRYPT_DIR="/etc/letsencrypt"
LOG_FILE="/var/log/letsencrypt-renewal.log"

echo "[$(date)] Iniciando backup de certificados SSL" >> $LOG_FILE

# Crear backup
tar -czf "$BACKUP_DIR/letsencrypt-backup-$DATE.tar.gz" -C / etc/letsencrypt

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup SSL completado: letsencrypt-backup-$DATE.tar.gz" >> $LOG_FILE
    
    # Mantener solo los últimos 30 backups
    ls -t $BACKUP_DIR/letsencrypt-backup-*.tar.gz | tail -n +31 | xargs -r rm
    echo "[$(date)] Backups antiguos limpiados" >> $LOG_FILE
else
    echo "[$(date)] ERROR: Falló el backup SSL" >> $LOG_FILE
    exit 1
fi

# Verificar integridad de certificados
certbot certificates --quiet
if [ $? -eq 0 ]; then
    echo "[$(date)] Verificación de integridad exitosa" >> $LOG_FILE
else
    echo "[$(date)] WARNING: Problema en la verificación de certificados" >> $LOG_FILE
fi
BACKUP_SCRIPT

chmod +x /usr/local/bin/backup-ssl-certs.sh
echo -e "${GREEN}✓ Sistema de backup configurado${NC}"

echo ""
echo "6. CONFIGURANDO AUTO-RENOVACIÓN..."
echo "--------------------------------"

# Script de renovación personalizado
cat > /usr/local/bin/renew-ssl-certs.sh << 'RENEWAL_SCRIPT'
#!/bin/bash

# Script personalizado de renovación de certificados Let's Encrypt
LOG_FILE="/var/log/letsencrypt-renewal.log"
NGINX_CONFIG_TEST="nginx -t"
DOMAINS="tudominio.com,www.tudominio.com"  # Personalizar según necesidades

echo "[$(date)] === INICIO RENOVACIÓN SSL ===" >> $LOG_FILE

# Pre-hook: Backup antes de renovar
echo "[$(date)] Ejecutando backup pre-renovación" >> $LOG_FILE
/usr/local/bin/backup-ssl-certs.sh

# Renovar certificados
echo "[$(date)] Iniciando renovación de certificados" >> $LOG_FILE
certbot renew \
    --quiet \
    --no-self-upgrade \
    --pre-hook "echo '[$(date)] Pre-hook: Preparando renovación' >> $LOG_FILE" \
    --post-hook "/usr/local/bin/ssl-renewal-post-hook.sh" \
    --deploy-hook "/usr/local/bin/ssl-deployment-hook.sh"

RENEWAL_EXIT_CODE=$?

if [ $RENEWAL_EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Renovación completada exitosamente" >> $LOG_FILE
else
    echo "[$(date)] ERROR: Renovación falló con código $RENEWAL_EXIT_CODE" >> $LOG_FILE
    
    # Notificar por email (opcional)
    if command -v mail &> /dev/null; then
        echo "La renovación SSL falló en $(hostname) el $(date)" | \
            mail -s "ERROR: Renovación SSL falló" admin@tudominio.com
    fi
fi

echo "[$(date)] === FIN RENOVACIÓN SSL ===" >> $LOG_FILE
echo "" >> $LOG_FILE

exit $RENEWAL_EXIT_CODE
RENEWAL_SCRIPT

chmod +x /usr/local/bin/renew-ssl-certs.sh

# Post-hook script
cat > /usr/local/bin/ssl-renewal-post-hook.sh << 'POST_HOOK'
#!/bin/bash

LOG_FILE="/var/log/letsencrypt-renewal.log"

echo "[$(date)] Post-hook: Verificando configuración Nginx" >> $LOG_FILE

# Verificar configuración de Nginx
nginx -t >> $LOG_FILE 2>&1
if [ $? -eq 0 ]; then
    echo "[$(date)] Post-hook: Configuración Nginx OK" >> $LOG_FILE
    systemctl reload nginx >> $LOG_FILE 2>&1
    echo "[$(date)] Post-hook: Nginx recargado" >> $LOG_FILE
else
    echo "[$(date)] ERROR Post-hook: Configuración Nginx inválida" >> $LOG_FILE
    exit 1
fi
POST_HOOK

chmod +x /usr/local/bin/ssl-renewal-post-hook.sh

# Deployment hook script
cat > /usr/local/bin/ssl-deployment-hook.sh << 'DEPLOY_HOOK'
#!/bin/bash

LOG_FILE="/var/log/letsencrypt-renewal.log"

echo "[$(date)] Deploy-hook: Certificados renovados exitosamente" >> $LOG_FILE

# Reiniciar servicios que usan SSL si es necesario
# Por ejemplo, si tienes otros servicios:
# systemctl restart docker-compose@tuapp >> $LOG_FILE 2>&1

# Verificar que los servicios estén funcionando
curl -f -s -o /dev/null https://tudominio.com
if [ $? -eq 0 ]; then
    echo "[$(date)] Deploy-hook: Verificación HTTPS exitosa" >> $LOG_FILE
else
    echo "[$(date)] WARNING Deploy-hook: Verificación HTTPS falló" >> $LOG_FILE
fi

# Actualizar fecha de última renovación exitosa
echo $(date) > /var/log/last-ssl-renewal.txt
DEPLOY_HOOK

chmod +x /usr/local/bin/ssl-deployment-hook.sh

echo -e "${GREEN}✓ Scripts de renovación configurados${NC}"

echo ""
echo "7. CONFIGURANDO CRON JOBS..."
echo "--------------------------"

# Configurar cron para renovación automática
cat > /etc/cron.d/letsencrypt-renewal << 'CRON_CONFIG'
# Renovación automática de certificados Let's Encrypt
# Ejecutar dos veces al día a horas aleatorias
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Renovación principal (2 veces al día)
23 2,14 * * * root /usr/local/bin/renew-ssl-certs.sh >/dev/null 2>&1

# Backup diario independiente
15 3 * * * root /usr/local/bin/backup-ssl-certs.sh >/dev/null 2>&1

# Verificación semanal de estado
0 6 * * 1 root certbot certificates >> /var/log/letsencrypt-renewal.log 2>&1
CRON_CONFIG

# Reiniciar cron
systemctl restart cron
echo -e "${GREEN}✓ Cron jobs configurados${NC}"

echo ""
echo "8. CONFIGURANDO MONITOREO..."
echo "--------------------------"

# Script de monitoreo de certificados
cat > /usr/local/bin/monitor-ssl-certs.sh << 'MONITOR_SCRIPT'
#!/bin/bash

# Script de monitoreo de certificados SSL
LOG_FILE="/var/log/ssl-monitoring.log"
DOMAINS="tudominio.com www.tudominio.com"
ALERT_DAYS=7  # Alertar si el certificado expira en menos de 7 días

echo "[$(date)] === MONITOREO SSL ===" >> $LOG_FILE

for domain in $DOMAINS; do
    echo "[$(date)] Verificando $domain" >> $LOG_FILE
    
    # Obtener fecha de expiración
    exp_date=$(echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | \
               openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    
    if [ ! -z "$exp_date" ]; then
        exp_epoch=$(date -d "$exp_date" +%s)
        current_epoch=$(date +%s)
        days_until_expiry=$(( (exp_epoch - current_epoch) / 86400 ))
        
        echo "[$(date)] $domain expira en $days_until_expiry días" >> $LOG_FILE
        
        if [ $days_until_expiry -lt $ALERT_DAYS ]; then
            echo "[$(date)] ALERTA: $domain expira en $days_until_expiry días" >> $LOG_FILE
            
            # Enviar alerta por email si está disponible
            if command -v mail &> /dev/null; then
                echo "El certificado SSL para $domain expira en $days_until_expiry días" | \
                    mail -s "ALERTA SSL: $domain expira pronto" admin@tudominio.com
            fi
        fi
    else
        echo "[$(date)] ERROR: No se pudo verificar $domain" >> $LOG_FILE
    fi
done

echo "[$(date)] === FIN MONITOREO SSL ===" >> $LOG_FILE
echo "" >> $LOG_FILE
MONITOR_SCRIPT

chmod +x /usr/local/bin/monitor-ssl-certs.sh

# Agregar monitoreo al cron
echo "0 8 * * * root /usr/local/bin/monitor-ssl-certs.sh >/dev/null 2>&1" >> /etc/cron.d/letsencrypt-renewal

echo -e "${GREEN}✓ Monitoreo configurado${NC}"

echo ""
echo "9. CONFIGURANDO LOGROTATE..."
echo "-------------------------"

# Configurar rotación de logs
cat > /etc/logrotate.d/letsencrypt-custom << 'LOGROTATE_CONFIG'
/var/log/letsencrypt-renewal.log /var/log/ssl-monitoring.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 0644 root root
    postrotate
        # Reiniciar cron si es necesario
        systemctl reload cron > /dev/null 2>&1 || true
    endscript
}
LOGROTATE_CONFIG

echo -e "${GREEN}✓ Logrotate configurado${NC}"

echo ""
echo "10. PRUEBA INICIAL..."
echo "------------------"

# Ejecutar test de renovación
echo "Ejecutando test de renovación (dry-run)..."
certbot renew --dry-run --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Test de renovación exitoso${NC}"
else
    echo -e "${YELLOW}⚠ Test de renovación con advertencias${NC}"
    echo "Revisa los logs en /var/log/letsencrypt/"
fi

# Verificar estado actual de certificados
echo ""
echo "Estado actual de certificados:"
certbot certificates

echo ""
echo "================================================================"
echo "AUTO-RENOVACIÓN LET'S ENCRYPT CONFIGURADA"
echo "================================================================"
echo ""
echo -e "${GREEN}✓ Certbot instalado y configurado${NC}"
echo -e "${GREEN}✓ Certificado inicial obtenido${NC}"
echo -e "${GREEN}✓ Auto-renovación configurada (2x día)${NC}"
echo -e "${GREEN}✓ Sistema de backup implementado${NC}"
echo -e "${GREEN}✓ Monitoreo de expiración activado${NC}"
echo -e "${GREEN}✓ Rotación de logs configurada${NC}"
echo ""
echo -e "${BLUE}ARCHIVOS IMPORTANTES:${NC}"
echo "• Certificados: $CERT_DIR/"
echo "• Logs renovación: /var/log/letsencrypt-renewal.log"
echo "• Logs monitoreo: /var/log/ssl-monitoring.log"
echo "• Backups: $BACKUP_DIR/"
echo "• Configuración cron: /etc/cron.d/letsencrypt-renewal"
echo ""
echo -e "${BLUE}COMANDOS ÚTILES:${NC}"
echo "• Ver estado: certbot certificates"
echo "• Test renovación: certbot renew --dry-run"
echo "• Renovación manual: /usr/local/bin/renew-ssl-certs.sh"
echo "• Monitoreo manual: /usr/local/bin/monitor-ssl-certs.sh"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASOS:${NC}"
echo "1. Personalizar dominios en los scripts de monitoreo"
echo "2. Configurar email para alertas (instalar mailutils)"
echo "3. Verificar que los puertos 80 y 443 están abiertos"
echo "4. Programar backups externos de $BACKUP_DIR/"