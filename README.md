# 🚀 TuAppDeAccesorios

**Sistema completo de gestión para tiendas de accesorios para celulares con seguridad enterprise.**

[![Deployment](https://img.shields.io/badge/Render-Ready-green)](https://render.com)
[![Security](https://img.shields.io/badge/Security-Enterprise-blue)](#security)
[![Python](https://img.shields.io/badge/Python-3.11+-brightgreen)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com)

## 📋 Descripción

TuAppDeAccesorios es una aplicación web moderna para gestionar inventario, ventas, usuarios y operaciones de punto de venta (POS) en tiendas de accesorios para celulares. Incluye funcionalidades avanzadas de seguridad, auditoría, backups automáticos y monitoreo en tiempo real.

## ⚡ Características Principales

### 🏪 **Gestión de Negocio**
- **Inventario completo** con categorías y distribuidores
- **Punto de Venta (POS)** con carrito de compras
- **Gestión de usuarios** con roles y permisos
- **Reportes y analytics** de ventas y productos
- **Consignaciones** y préstamos de productos

### 🛡️ **Seguridad Enterprise**
- **Autenticación JWT** con blacklist de tokens
- **Cifrado AES-256** para datos sensibles
- **Rate limiting** avanzado por endpoint
- **Headers de seguridad** (HSTS, CSP, XSS Protection)
- **Validación robusta** contra SQL injection y XSS
- **Auditoría completa** de todas las acciones
- **Monitoreo en tiempo real** con alertas automáticas

### 💾 **Backup y Recuperación**
- **Backups automáticos cifrados** con programación
- **Almacenamiento multi-tier** (local + AWS S3)
- **Compresión y verificación** de integridad
- **Restauración rápida** con un solo comando
- **Retención automática** de backups antiguos

### 📊 **Monitoreo y Analytics**
- **Dashboard de seguridad** en tiempo real
- **Métricas de performance** y uso
- **Alertas automáticas** via Slack/Discord/Email
- **Logs estructurados** con análisis

## 🚀 Deployment en Render

### Despliegue Rápido

1. **Fork/Clone** este repositorio
2. **Crear cuenta** en [Render](https://render.com)
3. **Seguir la guía** completa en [DEPLOYMENT.md](./DEPLOYMENT.md)

### Arquitectura de Despliegue

```
🌐 Internet
    ↓
📡 Render Load Balancer (HTTPS)
    ↓
🐍 FastAPI App (Backend)
    ↓
🗄️  PostgreSQL (Database)
    ↓
🔴 Redis (Cache)
    ↓
☁️  AWS S3 (Backups)
```

## 🛠️ Stack Tecnológico

### **Backend**
- **FastAPI** - Framework web moderno y rápido
- **SQLAlchemy** - ORM para base de datos
- **Alembic** - Migraciones de base de datos
- **Redis** - Cache y sesiones
- **PostgreSQL** - Base de datos principal

### **Seguridad**
- **PassLib + Bcrypt** - Hashing de contraseñas
- **Python-JOSE** - JWT tokens
- **Cryptography** - Cifrado AES-256
- **Bleach** - Sanitización HTML

### **Infraestructura**
- **Gunicorn + Uvicorn** - Servidor ASGI
- **Docker** - Containerización
- **AWS S3** - Almacenamiento de backups
- **Render** - Hosting y deployment

## 🔧 Configuración Local

### Prerequisitos
- Python 3.11+
- PostgreSQL o SQLite
- Redis (opcional)

### Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/TuAppDeAccesorios.git
cd TuAppDeAccesorios

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
cd backend
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 5. Ejecutar migraciones
python -m alembic upgrade head

# 6. Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Variables de Entorno Importantes

```bash
# Básicas
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=tu-clave-super-secreta
ENVIRONMENT=development

# Seguridad
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=http://localhost:3000

# Cache (opcional)
REDIS_URL=redis://localhost:6379
```

## 📊 API Documentation

Una vez iniciado el servidor, accede a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Endpoints Principales

```bash
# Autenticación
POST /token                 # Login
POST /refresh              # Refresh token
POST /logout               # Logout

# Usuarios
GET  /api/users/me         # Usuario actual
POST /api/users/           # Crear usuario
GET  /api/users/           # Listar usuarios

# Productos
GET  /api/products/        # Listar productos
POST /api/products/        # Crear producto
GET  /api/products/search  # Buscar productos

# POS
POST /api/pos/sales        # Crear venta
GET  /api/pos/cart         # Ver carrito

# Seguridad
GET  /api/security/dashboard    # Dashboard de seguridad
GET  /api/audit/trail          # Trail de auditoría
GET  /api/backup/status        # Status de backups
```

## 🔐 Características de Seguridad

### Autenticación y Autorización
- JWT tokens con refresh automático
- Blacklist de tokens revocados
- Roles de usuario (admin, user, distributor)
- Sesiones seguras con expiración

### Protección de Datos
- Cifrado AES-256 para datos sensibles
- Hashing seguro de contraseñas (bcrypt)
- Sanitización automática de inputs
- Headers de seguridad automáticos

### Monitoreo y Auditoría
- Log de todas las acciones de usuarios
- Detección de patrones sospechosos
- Alertas automáticas por email/Slack/Discord
- Dashboard de seguridad en tiempo real

### Rate Limiting
- Límites específicos por endpoint
- Protección contra ataques de fuerza bruta
- Bloqueo automático de IPs sospechosas
- Límites dinámicos basados en usuario

## 💾 Sistema de Backups

### Características
- **Automático**: Programado con cron
- **Cifrado**: AES-256 con salt único
- **Compresión**: GZIP para optimizar espacio
- **Multi-storage**: Local + AWS S3
- **Verificación**: Hash SHA-256 de integridad

### Uso

```bash
# Crear backup manual
curl -X POST https://tu-app.onrender.com/api/backup/create \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ver status de backups
curl https://tu-app.onrender.com/api/backup/status

# Listar backups disponibles
curl https://tu-app.onrender.com/api/backup/list
```

## 🤝 Contribuir

1. **Fork** el proyecto
2. **Crear branch** feature (`git checkout -b feature/amazing-feature`)
3. **Commit** cambios (`git commit -m 'Add amazing feature'`)
4. **Push** al branch (`git push origin feature/amazing-feature`)
5. **Abrir Pull Request**

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## 🆘 Soporte

Si encuentras problemas o necesitas ayuda:

1. **Revisar issues** existentes en GitHub
2. **Crear nuevo issue** con detalles del problema
3. **Consultar logs** en Render Dashboard
4. **Verificar configuración** en DEPLOYMENT.md

---

**¡Hecho con ❤️ para la comunidad de desarrolladores!**

*TuAppDeAccesorios - Sistema completo y seguro para tu negocio.*