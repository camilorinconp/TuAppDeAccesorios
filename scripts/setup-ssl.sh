#!/bin/bash

# ============================================
# SCRIPT DE CONFIGURACIÓN SSL/TLS CON LET'S ENCRYPT
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

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   log_error "Este script debe ejecutarse como root (sudo)"
   exit 1
fi

echo "🔒 Configurando SSL/TLS con Let's Encrypt para TuAppDeAccesorios"
echo "================================================================="

# Cargar variables de entorno
if [[ -f ".env.production" ]]; then
    source .env.production
    log_info "Variables de entorno cargadas desde .env.production"
else
    log_error "No se encontró el archivo .env.production"
    log_info "Ejecuta primero: ./scripts/generate-production-env.sh"
    exit 1
fi

# Verificar que DOMAIN_NAME esté configurado
if [[ -z "$DOMAIN_NAME" ]]; then
    log_error "DOMAIN_NAME no está configurado en .env.production"
    exit 1
fi

# Solicitar email para Let's Encrypt si no está configurado
if [[ -z "$ALERT_EMAIL" ]]; then
    read -p "📧 Email para Let's Encrypt: " ALERT_EMAIL
    if [[ -z "$ALERT_EMAIL" ]]; then
        log_error "Email requerido para Let's Encrypt"
        exit 1
    fi
fi

log_info "Configurando SSL para dominio: $DOMAIN_NAME"
log_info "Email de contacto: $ALERT_EMAIL"

# Actualizar sistema
log_info "Actualizando sistema..."
apt-get update -qq

# Instalar dependencias
log_info "Instalando dependencias..."
apt-get install -y certbot python3-certbot-nginx curl

# Verificar que nginx esté instalado
if ! command -v nginx &> /dev/null; then
    log_info "Instalando nginx..."
    apt-get install -y nginx
fi

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado. Instala Docker primero."
    exit 1
fi

# Verificar que Docker Compose esté instalado
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado. Instala Docker Compose primero."
    exit 1
fi

# Crear directorio para desafíos de Let's Encrypt
log_info "Creando directorio para challenges de Let's Encrypt..."
mkdir -p /var/www/html/.well-known/acme-challenge
chown -R www-data:www-data /var/www/html

# Crear configuración temporal de nginx para obtener certificado
log_info "Creando configuración temporal de nginx..."
cat > /tmp/nginx-temp.conf << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
    location / {
        return 200 'TuAppDeAccesorios - Configurando SSL...';
        add_header Content-Type text/plain;
    }
}
EOF

# Detener nginx si está corriendo
systemctl stop nginx 2>/dev/null || true

# Crear sitio temporal
cp /tmp/nginx-temp.conf /etc/nginx/sites-available/tuapp-temp
ln -sf /etc/nginx/sites-available/tuapp-temp /etc/nginx/sites-enabled/tuapp-temp

# Remover sitio por defecto
rm -f /etc/nginx/sites-enabled/default

# Iniciar nginx
systemctl start nginx
systemctl enable nginx

# Verificar configuración de nginx
nginx -t
if [[ $? -ne 0 ]]; then
    log_error "Error en configuración de nginx"
    exit 1
fi

log_success "Nginx configurado temporalmente"

# Obtener certificado SSL
log_info "Obteniendo certificado SSL de Let's Encrypt..."
certbot certonly \
    --webroot \
    --webroot-path=/var/www/html \
    --email "$ALERT_EMAIL" \
    --agree-tos \
    --no-eff-email \
    --domains "$DOMAIN_NAME" \
    --domains "www.$DOMAIN_NAME" \
    --non-interactive

if [[ $? -ne 0 ]]; then
    log_error "Error obteniendo certificado SSL"
    exit 1
fi

log_success "Certificado SSL obtenido exitosamente"

# Verificar que los certificados fueron creados
if [[ ! -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]]; then
    log_error "Certificado no encontrado en /etc/letsencrypt/live/$DOMAIN_NAME/"
    exit 1
fi

log_success "Certificados SSL verificados"

# Configurar renovación automática
log_info "Configurando renovación automática..."
cat > /etc/cron.d/certbot-renew << EOF
# Renovación automática de certificados Let's Encrypt
0 2 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
EOF

chmod 644 /etc/cron.d/certbot-renew

# Crear script de renovación con Docker
cat > /usr/local/bin/renew-ssl.sh << 'EOF'
#!/bin/bash
# Script de renovación SSL para TuAppDeAccesorios

# Renovar certificados
certbot renew --quiet

# Reiniciar nginx en Docker si está corriendo
if docker ps | grep -q nginx; then
    docker-compose -f /opt/tuapp/docker-compose.prod.yml restart nginx
fi

# Log de renovación
echo "$(date): Renovación SSL ejecutada" >> /var/log/ssl-renewal.log
EOF

chmod +x /usr/local/bin/renew-ssl.sh

# Actualizar cron para usar el nuevo script
cat > /etc/cron.d/certbot-renew << EOF
# Renovación automática de certificados Let's Encrypt
0 2 * * * root /usr/local/bin/renew-ssl.sh
EOF

log_success "Renovación automática configurada"

# Configurar firewall si está habilitado
if ufw status | grep -q "Status: active"; then
    log_info "Configurando firewall..."
    ufw allow 'Nginx Full'
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    log_success "Firewall configurado"
fi

# Crear script de verificación SSL
cat > /usr/local/bin/check-ssl.sh << 'EOF'
#!/bin/bash
# Script de verificación SSL para TuAppDeAccesorios

DOMAIN_NAME="$1"
if [[ -z "$DOMAIN_NAME" ]]; then
    echo "Uso: $0 <dominio>"
    exit 1
fi

echo "🔍 Verificando SSL para $DOMAIN_NAME..."

# Verificar certificado
openssl s_client -servername "$DOMAIN_NAME" -connect "$DOMAIN_NAME:443" </dev/null 2>/dev/null | \
    openssl x509 -noout -dates

# Verificar configuración SSL
echo "🔐 Verificando configuración SSL..."
curl -I "https://$DOMAIN_NAME" 2>/dev/null | head -5

# Verificar headers de seguridad
echo "🛡️  Verificando headers de seguridad..."
curl -I "https://$DOMAIN_NAME" 2>/dev/null | grep -i "strict-transport-security\|x-content-type-options\|x-frame-options"

echo "✅ Verificación completada"
EOF

chmod +x /usr/local/bin/check-ssl.sh

# Detener nginx temporal
systemctl stop nginx

# Remover configuración temporal
rm -f /etc/nginx/sites-enabled/tuapp-temp
rm -f /etc/nginx/sites-available/tuapp-temp

log_success "SSL/TLS configurado exitosamente"

echo
echo "🎉 ¡Configuración SSL completada!"
echo "================================="
echo
echo "📋 Resumen:"
echo "  - Certificado SSL obtenido para: $DOMAIN_NAME"
echo "  - Renovación automática configurada"
echo "  - Firewall configurado (si estaba activo)"
echo "  - Scripts de verificación creados"
echo
echo "🚀 Próximos pasos:"
echo "  1. Iniciar la aplicación: docker-compose -f docker-compose.prod.yml up -d"
echo "  2. Verificar SSL: /usr/local/bin/check-ssl.sh $DOMAIN_NAME"
echo "  3. Probar la aplicación: https://$DOMAIN_NAME"
echo
echo "🔧 Comandos útiles:"
echo "  - Verificar certificados: certbot certificates"
echo "  - Renovar manualmente: certbot renew"
echo "  - Verificar SSL: /usr/local/bin/check-ssl.sh $DOMAIN_NAME"
echo "  - Ver logs SSL: tail -f /var/log/ssl-renewal.log"
echo
log_success "¡Listo para producción con SSL!"
EOF