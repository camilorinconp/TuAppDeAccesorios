# 🚀 Configuración Segura para Render

## **Variables de Entorno Críticas**

### **🔐 OBLIGATORIAS - Configurar en Render Dashboard**

```bash
# ===== SEGURIDAD CRÍTICA =====
SECRET_KEY=_AtpyGC8L37d3DJNfpHjwAQnXBx3ghKc8EYhRqm2LbwKEmlTS7vsDeKOZBFaMXhq
DATABASE_MASTER_KEY=rFibeB-_aLasC698RuH4bOmehxlE8jAIlLeRRGeVOsc
BACKUP_ENCRYPTION_KEY=RSCaY5c3f9XO1g09sVYjCh7UtGRjyPK-sdZXfgsZD8Q

# ===== APLICACIÓN =====
ENVIRONMENT=production
PROJECT_NAME=TuAppDeAccesorios
LOG_LEVEL=INFO

# ===== CORS - ACTUALIZAR CON TUS DOMINIOS =====
CORS_ORIGINS=https://tu-frontend.onrender.com,https://tudominio.com
ALLOWED_HOSTS=tu-backend.onrender.com,tudominio.com

# ===== AUTENTICACIÓN =====
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===== SEGURIDAD WEB =====
FORCE_HTTPS=true
SECURE_COOKIES=true

# ===== RATE LIMITING =====
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=3600
RATE_LIMIT_BURST=10

# ===== CACHE REDIS =====
REDIS_CACHE_ENABLED=true
REDIS_CACHE_DEFAULT_TTL=300

# ===== AUDITORÍA =====
AUDIT_ENABLED=true
AUDIT_RETENTION_DAYS=365
AUDIT_LOG_SENSITIVE_DATA=false

# ===== BACKUPS =====
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30

# ===== PERFORMANCE =====
WORKERS=2
TIMEOUT=120
MAX_UPLOAD_SIZE=10485760
```

## **🔧 Configuración Automática de Render**

Las siguientes variables las configura automáticamente Render:
- `DATABASE_URL` - URL de PostgreSQL
- `REDIS_URL` - URL de Redis
- `PORT` - Puerto del servicio

## **⚠️ IMPORTANTES**

1. **NUNCA** subir `.env` al repositorio
2. **Rotar claves** cada 90 días
3. **Monitorear** logs de seguridad
4. **Actualizar** CORS_ORIGINS con dominios reales

## **📋 Checklist de Deployment**

- [ ] Variables configuradas en Render
- [ ] CORS_ORIGINS actualizado
- [ ] SSL/HTTPS habilitado
- [ ] Rate limiting activado
- [ ] Monitoreo configurado
- [ ] Backups habilitados