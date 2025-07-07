#!/bin/bash

# Script para configurar SSL con Let's Encrypt
# Uso: ./ssl-setup.sh tudominio.com

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar argumentos
if [ $# -ne 1 ]; then
    log_error "Uso: $0 <dominio>"
    log_error "Ejemplo: $0 tuapp.com"
    exit 1
fi

DOMAIN=$1
EMAIL="admin@${DOMAIN}"

log_info "Configurando SSL para dominio: ${DOMAIN}"

# Crear directorio para certificados
mkdir -p nginx/ssl
mkdir -p nginx/ssl/live/${DOMAIN}

# Función para obtener certificados con certbot
setup_letsencrypt() {
    log_info "Instalando certbot..."
    
    # Verificar si certbot está instalado
    if ! command -v certbot &> /dev/null; then
        # Instalar certbot según el sistema operativo
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update
            sudo apt-get install -y certbot python3-certbot-nginx
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install certbot
        else
            log_error "Sistema operativo no soportado. Instala certbot manualmente."
            exit 1
        fi
    fi
    
    log_info "Obteniendo certificados SSL para ${DOMAIN}..."
    
    # Obtener certificados
    sudo certbot certonly \
        --standalone \
        --agree-tos \
        --non-interactive \
        --email ${EMAIL} \
        -d ${DOMAIN} \
        -d www.${DOMAIN} || {
        log_error "Error al obtener certificados. Verifica que el dominio apunte a este servidor."
        exit 1
    }
    
    # Copiar certificados al directorio de nginx
    sudo cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem nginx/ssl/cert.pem
    sudo cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem nginx/ssl/private.key
    
    # Cambiar permisos
    sudo chmod 644 nginx/ssl/cert.pem
    sudo chmod 600 nginx/ssl/private.key
    sudo chown $(whoami):$(whoami) nginx/ssl/cert.pem nginx/ssl/private.key
    
    log_info "Certificados SSL configurados correctamente"
}

# Función para generar certificados auto-firmados (desarrollo)
setup_self_signed() {
    log_warn "Generando certificados auto-firmados para desarrollo..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/private.key \
        -out nginx/ssl/cert.pem \
        -subj "/C=MX/ST=Mexico/L=Mexico/O=TuApp/OU=IT/CN=${DOMAIN}"
    
    log_warn "Certificados auto-firmados generados. Solo para desarrollo."
}

# Función para configurar renovación automática
setup_auto_renewal() {
    log_info "Configurando renovación automática..."
    
    # Crear script de renovación
    cat > /tmp/renew-ssl.sh << 'EOF'
#!/bin/bash
certbot renew --quiet
if [ $? -eq 0 ]; then
    # Copiar certificados actualizados
    cp /etc/letsencrypt/live/*/fullchain.pem /path/to/nginx/ssl/cert.pem
    cp /etc/letsencrypt/live/*/privkey.pem /path/to/nginx/ssl/private.key
    
    # Recargar nginx
    docker-compose exec nginx nginx -s reload
    
    echo "Certificados renovados exitosamente"
fi
EOF
    
    # Actualizar path en el script
    sed -i "s|/path/to/nginx|$(pwd)/nginx|g" /tmp/renew-ssl.sh
    
    # Mover script a ubicación final
    sudo mv /tmp/renew-ssl.sh /usr/local/bin/renew-ssl.sh
    sudo chmod +x /usr/local/bin/renew-ssl.sh
    
    # Configurar cron job para renovación automática
    (crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/renew-ssl.sh") | crontab -
    
    log_info "Renovación automática configurada (diaria a las 3 AM)"
}

# Función para actualizar configuración de nginx
update_nginx_config() {
    log_info "Actualizando configuración de nginx con el dominio ${DOMAIN}..."
    
    # Reemplazar dominio en configuración
    sed -i.bak "s/tudominio.com/${DOMAIN}/g" nginx/nginx.conf
    
    log_info "Configuración de nginx actualizada"
}

# Función para validar SSL
validate_ssl() {
    log_info "Validando configuración SSL..."
    
    # Verificar que los archivos existen
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/private.key" ]; then
        log_error "Archivos de certificado no encontrados"
        exit 1
    fi
    
    # Verificar validez del certificado
    if ! openssl x509 -in nginx/ssl/cert.pem -text -noout &> /dev/null; then
        log_error "Certificado SSL inválido"
        exit 1
    fi
    
    log_info "Configuración SSL válida"
}

# Menú principal
echo "¿Cómo deseas configurar SSL?"
echo "1) Let's Encrypt (Producción)"
echo "2) Certificado auto-firmado (Desarrollo)"
read -p "Selecciona una opción (1-2): " option

case $option in
    1)
        setup_letsencrypt
        setup_auto_renewal
        ;;
    2)
        setup_self_signed
        ;;
    *)
        log_error "Opción inválida"
        exit 1
        ;;
esac

# Actualizar configuración y validar
update_nginx_config
validate_ssl

log_info "SSL configurado exitosamente para ${DOMAIN}"
log_info "Reinicia los servicios con: docker-compose restart"

# Mostrar información adicional
echo
echo "=== INFORMACIÓN ADICIONAL ==="
echo "- Certificados ubicados en: nginx/ssl/"
echo "- Configuración nginx actualizada"
echo "- Dominio configurado: ${DOMAIN}"
if [ $option -eq 1 ]; then
    echo "- Renovación automática configurada"
    echo "- Próxima renovación: $(date -d '+90 days' '+%Y-%m-%d')"
fi
echo
echo "=== SIGUIENTES PASOS ==="
echo "1. Asegúrate de que el dominio ${DOMAIN} apunte a este servidor"
echo "2. Reinicia los servicios: docker-compose restart"
echo "3. Verifica HTTPS en: https://${DOMAIN}"
echo "4. Ejecuta el security check: ./scripts/security-check.sh"