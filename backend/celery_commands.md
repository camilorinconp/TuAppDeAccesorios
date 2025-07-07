# ==================================================================
# COMANDOS DE CELERY - GUÍA DE USO
# ==================================================================

## Descripción

Esta guía contiene los comandos necesarios para ejecutar y gestionar los workers de Celery y el scheduler (Beat) para TuAppDeAccesorios.

## Requisitos Previos

1. **Redis**: Debe estar ejecutándose en `redis://localhost:6379/0`
2. **Variables de entorno**: Configurar `REDIS_URL` si usa una instancia diferente
3. **Base de datos**: PostgreSQL configurada y accesible

## Comandos de Ejecución

### Worker Principal (Cola por Defecto)

```bash
# Ejecutar worker con todas las colas
celery -A app.celery_app worker --loglevel=info --concurrency=4

# Ejecutar worker específico para cola de mantenimiento
celery -A app.celery_app worker --loglevel=info --queues=maintenance --concurrency=2

# Ejecutar worker específico para cola de inventario
celery -A app.celery_app worker --loglevel=info --queues=inventory --concurrency=2

# Ejecutar worker específico para cola de reportes
celery -A app.celery_app worker --loglevel=info --queues=reports --concurrency=1

# Ejecutar worker específico para cola de auditoría
celery -A app.celery_app worker --loglevel=info --queues=audit --concurrency=1

# Ejecutar worker específico para cola de notificaciones
celery -A app.celery_app worker --loglevel=info --queues=notifications --concurrency=3

# Ejecutar worker específico para cola de backup
celery -A app.celery_app worker --loglevel=info --queues=backup --concurrency=1
```

### Celery Beat (Scheduler)

```bash
# Ejecutar el scheduler para tareas programadas
celery -A app.celery_app beat --loglevel=info

# Ejecutar beat con archivo de schedule personalizado
celery -A app.celery_app beat --loglevel=info --schedule=celerybeat-schedule
```

### Flower (Interfaz Web de Monitoreo)

```bash
# Instalar Flower (si no está instalado)
pip install flower

# Ejecutar Flower para monitoreo web
celery -A app.celery_app flower --port=5555

# Acceder a: http://localhost:5555
```

### Comandos de Monitoreo

```bash
# Ver workers activos
celery -A app.celery_app inspect active

# Ver tareas programadas
celery -A app.celery_app inspect scheduled

# Ver estadísticas de workers
celery -A app.celery_app inspect stats

# Ver workers registrados
celery -A app.celery_app inspect registered

# Ver configuración
celery -A app.celery_app inspect conf
```

### Comandos de Control

```bash
# Cancelar tarea específica
celery -A app.celery_app control revoke TASK_ID --terminate

# Parar todos los workers
celery -A app.celery_app control shutdown

# Reiniciar workers
celery -A app.celery_app control pool_restart

# Purgar todas las tareas pendientes
celery -A app.celery_app purge

# Purgar cola específica
celery -A app.celery_app purge -Q maintenance
```

## Configuración de Producción

### Usando systemd (Linux)

1. **Crear archivo de servicio para worker:**

```ini
# /etc/systemd/system/celery-worker.service
[Unit]
Description=Celery Worker Service
After=network.target

[Service]
Type=forking
User=celery
Group=celery
EnvironmentFile=/etc/default/celery
WorkingDirectory=/path/to/TuAppDeAccesorios/backend
ExecStart=/path/to/venv/bin/celery -A app.celery_app worker --loglevel=info --pidfile=/var/run/celery/worker.pid --logfile=/var/log/celery/worker.log
ExecStop=/path/to/venv/bin/celery -A app.celery_app control shutdown
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Crear archivo de servicio para beat:**

```ini
# /etc/systemd/system/celery-beat.service
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
User=celery
Group=celery
EnvironmentFile=/etc/default/celery
WorkingDirectory=/path/to/TuAppDeAccesorios/backend
ExecStart=/path/to/venv/bin/celery -A app.celery_app beat --loglevel=info --pidfile=/var/run/celery/beat.pid --logfile=/var/log/celery/beat.log
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Configurar variables de entorno:**

```bash
# /etc/default/celery
CELERY_APP="app.celery_app"
CELERY_USER="celery"
CELERY_GROUP="celery"
REDIS_URL="redis://localhost:6379/0"
DATABASE_URL="postgresql://user:password@localhost/tuapp"
```

4. **Comandos de systemd:**

```bash
# Habilitar y iniciar servicios
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat

# Ver estado
sudo systemctl status celery-worker celery-beat

# Reiniciar servicios
sudo systemctl restart celery-worker celery-beat

# Ver logs
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f
```

## Configuración de Desarrollo

### Script de desarrollo (desarrollo.sh)

```bash
#!/bin/bash
# Archivo: scripts/desarrollo.sh

echo "🚀 Iniciando servicios de desarrollo..."

# Terminal 1: FastAPI
gnome-terminal --tab --title="FastAPI" -- bash -c "cd /path/to/backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000; exec bash"

# Terminal 2: Celery Worker
gnome-terminal --tab --title="Celery Worker" -- bash -c "cd /path/to/backend && source venv/bin/activate && celery -A app.celery_app worker --loglevel=info --concurrency=2; exec bash"

# Terminal 3: Celery Beat
gnome-terminal --tab --title="Celery Beat" -- bash -c "cd /path/to/backend && source venv/bin/activate && celery -A app.celery_app beat --loglevel=info; exec bash"

# Terminal 4: Flower
gnome-terminal --tab --title="Flower Monitor" -- bash -c "cd /path/to/backend && source venv/bin/activate && celery -A app.celery_app flower --port=5555; exec bash"

echo "✅ Servicios iniciados:"
echo "   - FastAPI: http://localhost:8000"
echo "   - Flower: http://localhost:5555"
```

## Tareas Programadas

### Tareas Diarias
- **06:00**: Reporte diario de inventario
- **07:00**: Pre-carga de caché matutina
- **07:30**: Resumen diario por notificación
- **08:00**: Reporte de seguridad diario
- **09:00**: Verificación de stock bajo (mañana)
- **10:00**: Verificación de consignaciones vencidas
- **12:00**: Análisis de salud del sistema
- **15:00**: Verificación de stock bajo (tarde)

### Tareas de Mantenimiento
- **01:00**: Backup incremental diario
- **02:00**: Optimización de base de datos
- **03:00**: Limpieza de logs de auditoría (domingos)
- **04:00**: Reconciliación de inventario (domingos)
- **05:00**: Sincronización de datos de productos

### Tareas por Hora
- **Cada hora**: Limpieza de caché expirado

### Tareas Semanales
- **Lunes 09:00**: Reporte semanal de ventas
- **Lunes 10:00**: Reporte semanal de consignaciones
- **Domingo 00:00**: Backup completo semanal

### Tareas Mensuales
- **Día 1 08:00**: Reporte mensual de ventas

## Monitoreo y Logging

### Ubicaciones de Logs

```bash
# Logs de workers
/var/log/celery/worker.log

# Logs de beat
/var/log/celery/beat.log

# Logs de aplicación
/var/log/tuapp/celery.log
```

### Comandos útiles de monitoreo

```bash
# Ver tareas activas en tiempo real
watch -n 2 'celery -A app.celery_app inspect active'

# Monitorear cola específica
celery -A app.celery_app events --camera=djcelery.camera.Camera

# Ver estadísticas de rendimiento
celery -A app.celery_app inspect stats | grep -E "(pool|prefetch|total)"
```

## Resolución de Problemas

### Worker no se conecta a Redis

```bash
# Verificar conexión Redis
redis-cli ping

# Verificar configuración
echo $REDIS_URL

# Reiniciar Redis
sudo systemctl restart redis
```

### Tareas se quedan en PENDING

```bash
# Verificar workers activos
celery -A app.celery_app inspect active

# Purgar tareas pendientes
celery -A app.celery_app purge

# Reiniciar workers
celery -A app.celery_app control pool_restart
```

### Beat no programa tareas

```bash
# Eliminar archivo de schedule y reiniciar
rm celerybeat-schedule
celery -A app.celery_app beat --loglevel=debug
```

### Problemas de memoria

```bash
# Configurar límite de memoria por worker
celery -A app.celery_app worker --max-memory-per-child=200000  # 200MB

# Monitorear uso de memoria
ps aux | grep celery | awk '{print $6}' | awk '{sum+=$1} END {print "Total Memory (KB):", sum}'
```

## Mejores Prácticas

1. **Separar workers por tipo de tarea**: Usar colas específicas para diferentes tipos de operaciones
2. **Configurar timeouts apropiados**: Evitar tareas que se ejecuten indefinidamente
3. **Monitorear regularmente**: Usar Flower para supervisión visual
4. **Backup de configuración**: Mantener respaldos del archivo de schedule de beat
5. **Logs centralizados**: Configurar logging estructurado para análisis
6. **Escalamiento horizontal**: Agregar más workers según la carga
7. **Rate limiting**: Configurar límites para evitar sobrecarga del sistema

## Comandos de Emergencia

```bash
# Parar todo inmediatamente
pkill -f celery

# Limpiar Redis completamente
redis-cli FLUSHALL

# Reinicio completo del sistema Celery
sudo systemctl stop celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```