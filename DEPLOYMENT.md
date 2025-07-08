# 🚀 DEPLOYMENT GUIDE - RENDER

Esta guía te ayudará a desplegar TuAppDeAccesorios en Render de manera segura y eficiente.

## 📋 PREREQUISITOS

1. **Cuenta en Render**: [render.com](https://render.com)
2. **Repositorio GitHub**: Código subido a GitHub
3. **Cuenta AWS S3** (opcional): Para backups automáticos

## 🔧 CONFIGURACIÓN PASO A PASO

### 1. PREPARAR EL REPOSITORIO

```bash
# Commit todos los cambios
git add .
git commit -m "feat: configure for Render deployment"
git push origin main
```

### 2. CREAR SERVICIOS EN RENDER

#### **A. Base de Datos PostgreSQL**

1. En Render Dashboard → **New** → **PostgreSQL**
2. Configuración:
   - **Name**: `tuapp-postgres`
   - **Database Name**: `tuapp_production`
   - **User**: `tuapp_user`
   - **Plan**: Starter (gratis) o Standard
3. **Create Database**
4. **Guardar la DATABASE_URL** generada

#### **B. Redis Cache**

1. En Render Dashboard → **New** → **Redis**
2. Configuración:
   - **Name**: `tuapp-redis`
   - **Plan**: Starter (gratis)
3. **Create Redis**
4. **Guardar la REDIS_URL** generada

#### **C. Web Service (Backend)**

1. En Render Dashboard → **New** → **Web Service**
2. Conectar repositorio GitHub
3. Configuración básica:
   - **Name**: `tuapp-backend`
   - **Environment**: `Python 3`
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Build Command**: 
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     chmod +x ./scripts/render-startup.sh && ./scripts/render-startup.sh
     ```

### 3. CONFIGURAR VARIABLES DE ENTORNO

En el dashboard del Web Service, añadir estas **Environment Variables**:

#### **🔒 VARIABLES DE SEGURIDAD** (Generar valores seguros)
```bash
SECRET_KEY=<generar-clave-segura-64-caracteres>
DATABASE_MASTER_KEY=<generar-clave-segura-32-caracteres>
BACKUP_ENCRYPTION_KEY=<generar-clave-segura-32-caracteres>
```

#### **📦 VARIABLES DE APLICACIÓN**
```bash
ENVIRONMENT=production
PROJECT_NAME=TuAppDeAccesorios
LOG_LEVEL=INFO
WORKERS=2
TIMEOUT=120
```

#### **🗄️ VARIABLES DE BASE DE DATOS**
```bash
DATABASE_URL=<copiar-url-de-postgresql-creado>
```

#### **🔴 VARIABLES DE REDIS**
```bash
REDIS_URL=<copiar-url-de-redis-creado>
REDIS_CACHE_ENABLED=true
REDIS_CACHE_DEFAULT_TTL=300
```

#### **🌐 VARIABLES DE CORS** (Actualizar después del despliegue)
```bash
CORS_ORIGINS=https://tu-app-backend.onrender.com
ALLOWED_HOSTS=tu-app-backend.onrender.com
```

#### **🔐 VARIABLES DE SEGURIDAD**
```bash
FORCE_HTTPS=true
SECURE_COOKIES=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=3600
```

#### **📊 VARIABLES DE AUDITORÍA**
```bash
AUDIT_ENABLED=true
AUDIT_RETENTION_DAYS=365
AUDIT_LOG_SENSITIVE_DATA=false
AUDIT_ASYNC_LOGGING=true
```

#### **💾 VARIABLES DE BACKUP**
```bash
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

### 4. GENERAR CLAVES SEGURAS

Usar estos comandos para generar claves seguras:

```bash
# SECRET_KEY (64 caracteres)
openssl rand -hex 32

# DATABASE_MASTER_KEY y BACKUP_ENCRYPTION_KEY (32 caracteres)
openssl rand -hex 16
```

### 5. DEPLOY

1. **Save Changes** en las variables de entorno
2. **Manual Deploy** o esperar auto-deploy
3. Verificar logs durante el despliegue

## 🧪 VERIFICACIÓN POST-DEPLOYMENT

### 1. Health Check
```bash
curl https://tu-app-backend.onrender.com/health
```

### 2. API Documentation
```bash
https://tu-app-backend.onrender.com/docs
```

### 3. Verificar Servicios
```bash
# Database
curl https://tu-app-backend.onrender.com/api/users/me

# Cache
curl https://tu-app-backend.onrender.com/api/cache/stats

# Security
curl https://tu-app-backend.onrender.com/api/security/health
```

## 🔧 CONFIGURACIÓN OPCIONAL

### A. AWS S3 para Backups

Si quieres backups automáticos en S3, añadir:

```bash
BACKUP_S3_BUCKET=tu-bucket-s3
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_REGION=us-east-1
```

### B. Notificaciones

Para alertas automáticas:

```bash
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@tudominio.com
SMTP_PASSWORD=tu-password-smtp
ALERT_EMAIL=admin@tudominio.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### C. Dominio Personalizado

1. En Render Dashboard → Service Settings → **Custom Domains**
2. Añadir tu dominio
3. Configurar DNS según las instrucciones
4. Actualizar `CORS_ORIGINS` y `ALLOWED_HOSTS`

## 📊 MONITOREO

### Logs en Tiempo Real
```bash
# En Render Dashboard → Service → Logs
```

### Métricas
```bash
# Endpoint de métricas
GET https://tu-app-backend.onrender.com/metrics
```

### Auditoría
```bash
# Dashboard de seguridad
GET https://tu-app-backend.onrender.com/api/security/dashboard
```

## 🚨 TROUBLESHOOTING

### Error de Base de Datos
```bash
# Verificar DATABASE_URL
# Verificar que PostgreSQL esté running
# Check migration logs
```

### Error de Redis
```bash
# Verificar REDIS_URL
# El sistema funcionará sin Redis (cache deshabilitado)
```

### Error de Permisos
```bash
# Verificar que todas las variables de entorno estén configuradas
# Verificar SECRET_KEY generado correctamente
```

### Error de CORS
```bash
# Actualizar CORS_ORIGINS con la URL correcta de Render
# Formato: https://tu-service-name.onrender.com
```

## 🔄 UPDATES Y MAINTENANCE

### Auto-Deploy
```bash
# Configurado automáticamente desde GitHub
git push origin main  # Trigger auto-deploy
```

### Manual Deploy
```bash
# En Render Dashboard → Manual Deploy
```

### Database Migrations
```bash
# Se ejecutan automáticamente en el startup script
# Ver logs para verificar éxito
```

### Backups
```bash
# Manual backup
POST https://tu-app-backend.onrender.com/api/backup/create

# Ver status
GET https://tu-app-backend.onrender.com/api/backup/status
```

## 🛡️ SECURITY CHECKLIST

- [ ] SECRET_KEY generado correctamente (64 chars)
- [ ] DATABASE_MASTER_KEY configurado
- [ ] BACKUP_ENCRYPTION_KEY configurado
- [ ] FORCE_HTTPS=true
- [ ] SECURE_COOKIES=true
- [ ] RATE_LIMIT_ENABLED=true
- [ ] CORS_ORIGINS configurado con dominios correctos
- [ ] Variables sensibles marcadas como secrets en Render
- [ ] Database usando SSL (automático en Render)
- [ ] Logs sin información sensible

## 📞 SUPPORT

Si encuentras problemas:

1. **Check Render Logs** primero
2. **Verify Environment Variables**
3. **Test Health Endpoints**
4. **Review Database Connectivity**

**¡Tu aplicación está lista para producción con seguridad enterprise!** 🚀🔒