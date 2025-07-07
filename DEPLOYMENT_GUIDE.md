# 🚀 Guía de Deployment a Producción - TuAppDeAccesorios

Esta guía te llevará paso a paso para desplegar TuAppDeAccesorios en producción de manera segura y optimizada.

## ✅ **Recomendaciones Críticas Implementadas**

Las siguientes mejoras críticas han sido implementadas y están listas para producción:

### 1. ✅ **Variables de Entorno de Producción**
- **Archivo:** `.env.production` configurado
- **Script:** `./scripts/generate-production-env.sh`
- **Características:**
  - Generación automática de contraseñas seguras
  - Configuración específica por dominio
  - Validaciones de seguridad integradas
  - Separación clara entre desarrollo y producción

### 2. ✅ **SSL/TLS con Let's Encrypt**
- **Script:** `./scripts/setup-ssl.sh`
- **Características:**
  - Configuración automática de certificados SSL
  - Renovación automática configurada
  - Nginx optimizado para HTTPS
  - Redirección automática HTTP → HTTPS
  - Headers de seguridad incluidos

### 3. ✅ **Sistema de Backups Automáticos**
- **Script:** `./scripts/setup-backups.sh`
- **Características:**
  - Backups diarios automáticos de PostgreSQL
  - Retención configurable (30 días por defecto)
  - Compresión y verificación de integridad
  - Soporte para S3 (opcional)
  - Monitoreo y alertas integradas
  - Scripts de restauración incluidos

### 4. ✅ **Logs de Debug Eliminados**
- **Archivos limpiados:** 21 archivos procesados
- **Eliminado:** +50 console.log y print statements de debug
- **Mantenido:** Solo logs apropiados para producción
- **Resultado:** Código limpio y optimizado para producción

### 5. ✅ **Configuración CORS Validada**
- **Archivo:** `backend/app/config.py` mejorado
- **Características:**
  - Validación automática de origins en producción
  - Solo HTTPS permitido en producción
  - Validación de caracteres seguros
  - Fallback seguro configurado
  - Logging de seguridad incluido

## 🛠️ **Scripts de Deployment Disponibles**

### Scripts Principales
```bash
# Generar configuración de producción
./scripts/generate-production-env.sh

# Configurar SSL/TLS
sudo ./scripts/setup-ssl.sh

# Configurar sistema de backups
sudo ./scripts/setup-backups.sh

# Validar configuración antes del deployment
./scripts/validate-production-config.sh
```

### Scripts de Gestión
```bash
# Gestión de backups
tuapp-backup backup          # Crear backup manual
tuapp-backup list            # Listar backups
tuapp-backup restore <file>  # Restaurar backup
tuapp-backup status          # Estado del sistema

# Verificación SSL
/usr/local/bin/check-ssl.sh yourdomain.com
```

## 📋 **Checklist de Deployment**

### Pre-Deployment
- [ ] **Configurar servidor** con Docker y Docker Compose
- [ ] **Configurar DNS** para apuntar a tu servidor
- [ ] **Abrir puertos** 80, 443, 22 en firewall
- [ ] **Ejecutar:** `./scripts/generate-production-env.sh`
- [ ] **Ejecutar:** `./scripts/validate-production-config.sh`

### Deployment
- [ ] **Copiar proyecto** al servidor
- [ ] **Ejecutar:** `sudo ./scripts/setup-ssl.sh`
- [ ] **Ejecutar:** `sudo ./scripts/setup-backups.sh`
- [ ] **Iniciar servicios:** `docker-compose -f docker-compose.prod.yml up -d`

### Post-Deployment
- [ ] **Verificar SSL:** `/usr/local/bin/check-ssl.sh yourdomain.com`
- [ ] **Verificar aplicación:** `https://yourdomain.com`
- [ ] **Verificar backups:** `tuapp-backup status`
- [ ] **Configurar monitoreo** (Grafana dashboard)

## 🔧 **Comandos de Deployment**

### Paso 1: Configuración Inicial
```bash
# En tu máquina local
git clone <repository>
cd TuAppDeAccesorios

# Generar configuración de producción
./scripts/generate-production-env.sh
```

### Paso 2: Preparar Servidor
```bash
# En el servidor
# Instalar Docker y Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose

# Crear directorio de la aplicación
sudo mkdir -p /opt/tuapp
sudo chown $USER:$USER /opt/tuapp
```

### Paso 3: Deployment
```bash
# Copiar archivos al servidor
rsync -avz --exclude='.git' ./ user@server:/opt/tuapp/

# En el servidor
cd /opt/tuapp

# Configurar SSL
sudo ./scripts/setup-ssl.sh

# Configurar backups
sudo ./scripts/setup-backups.sh

# Validar configuración
./scripts/validate-production-config.sh

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d
```

### Paso 4: Verificación
```bash
# Verificar servicios
docker-compose -f docker-compose.prod.yml ps

# Verificar SSL
/usr/local/bin/check-ssl.sh yourdomain.com

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Verificar backups
tuapp-backup status
```

## 🔐 **Configuración de Seguridad**

### Variables de Entorno Críticas
```bash
# Estas variables DEBEN ser configuradas:
DOMAIN_NAME=yourdomain.com
SECRET_KEY=<generated-secure-key>
POSTGRES_PASSWORD=<generated-secure-password>
REDIS_PASSWORD=<generated-secure-password>
CORS_ORIGINS=["https://yourdomain.com"]
ENVIRONMENT=production
```

### Headers de Seguridad (Auto-configurados)
- **HSTS:** Strict-Transport-Security
- **CSP:** Content-Security-Policy
- **X-Frame-Options:** DENY
- **X-Content-Type-Options:** nosniff
- **X-XSS-Protection:** habilitado

## 📊 **Monitoreo y Alertas**

### Servicios de Monitoreo Incluidos
- **Prometheus:** Métricas del sistema
- **Grafana:** Dashboards visuales
- **Loki:** Agregación de logs
- **Alertmanager:** Gestión de alertas

### URLs de Monitoreo
- **Grafana:** `https://yourdomain.com:3000`
- **Prometheus:** `https://yourdomain.com:9090`

### Configuración de Alertas
```bash
# Editar configuración de alertas
sudo nano /opt/tuapp/monitoring/alertmanager/alertmanager.yml

# Reiniciar servicios de monitoreo
docker-compose -f docker-compose.monitoring.yml restart
```

## 💾 **Sistema de Backups**

### Configuración Automática
- **Frecuencia:** Diaria (2:00 AM)
- **Retención:** 30 días
- **Compresión:** GZIP
- **Verificación:** Automática

### Comandos de Backup
```bash
# Backup manual
tuapp-backup backup

# Listar backups
tuapp-backup list

# Restaurar backup
tuapp-backup restore backup_2024-01-15_02-00-00.sql.gz

# Monitorear estado
tuapp-backup monitor
```

## 🚨 **Troubleshooting**

### Problemas Comunes

#### SSL no funciona
```bash
# Verificar certificados
sudo certbot certificates

# Renovar certificados
sudo certbot renew

# Verificar nginx
sudo nginx -t
```

#### Base de datos no conecta
```bash
# Verificar servicios
docker-compose -f docker-compose.prod.yml ps

# Ver logs de base de datos
docker-compose -f docker-compose.prod.yml logs db

# Verificar conexión
docker-compose -f docker-compose.prod.yml exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

#### Backups fallan
```bash
# Ver logs de backup
tail -f /opt/tuapp/backups/logs/backup.log

# Verificar permisos
ls -la /opt/tuapp/backups/

# Ejecutar backup manual con debug
tuapp-backup backup
```

## 📞 **Soporte y Mantenimiento**

### Logs Importantes
```bash
# Logs de aplicación
docker-compose -f docker-compose.prod.yml logs -f backend

# Logs de nginx
docker-compose -f docker-compose.prod.yml logs -f nginx

# Logs de sistema
journalctl -f

# Logs de backups
tail -f /opt/tuapp/backups/logs/backup.log
```

### Comandos de Mantenimiento
```bash
# Actualizar aplicación
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Limpiar Docker
docker system prune

# Verificar espacio en disco
df -h
du -sh /opt/tuapp/

# Verificar servicios
systemctl status docker
systemctl status nginx
```

## 🎉 **¡Deployment Completado!**

Una vez completados todos los pasos, tu aplicación TuAppDeAccesorios estará:

✅ **Ejecutándose de forma segura** con HTTPS
✅ **Respaldada automáticamente** con backups diarios
✅ **Monitoreada constantemente** con alertas
✅ **Optimizada para producción** sin logs de debug
✅ **Configurada con CORS seguro** para tu dominio

**URLs de acceso:**
- **Aplicación:** `https://yourdomain.com`
- **Grafana:** `https://yourdomain.com:3000`
- **API Docs:** `https://yourdomain.com/docs`

¡Tu sistema está listo para gestionar el inventario y ventas de manera profesional y segura!