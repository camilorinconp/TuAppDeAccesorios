#!/bin/bash

# Script para configurar el stack de monitoreo
# Uso: ./scripts/setup-monitoring.sh [dominio]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

DOMAIN=${1:-tudominio.com}

log_info "Configurando stack de monitoreo para ${DOMAIN}"

# Verificar que Docker y docker-compose están instalados
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado"
    exit 1
fi

log_step "1. Configurando variables de entorno para monitoreo..."

# Crear archivo de configuración para monitoreo
cat > monitoring.env << EOF
# Configuración de monitoreo
GRAFANA_ADMIN_PASSWORD=admin123
PROMETHEUS_RETENTION=15d
ALERTMANAGER_SMTP_HOST=smtp.gmail.com:587
ALERTMANAGER_SMTP_FROM=noreply@${DOMAIN}
ALERTMANAGER_SMTP_PASSWORD=changeme
ALERTMANAGER_EMAIL_TO=admin@${DOMAIN}
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
EOF

log_step "2. Actualizando configuración con el dominio ${DOMAIN}..."

# Actualizar configuración de Prometheus
sed -i.bak "s/tudominio.com/${DOMAIN}/g" monitoring/prometheus/prometheus.yml

# Actualizar configuración de AlertManager
sed -i.bak "s/tudominio.com/${DOMAIN}/g" monitoring/alertmanager/alertmanager.yml

log_step "3. Configurando permisos para Grafana..."

# Crear directorios con permisos correctos
mkdir -p monitoring/grafana/dashboards
sudo chown -R 472:472 monitoring/grafana/

log_step "4. Iniciando servicios de monitoreo..."

# Iniciar stack de monitoreo
docker-compose -f docker-compose.monitoring.yml up -d

log_step "5. Esperando a que los servicios estén listos..."

# Esperar a que los servicios estén listos
sleep 30

# Verificar que los servicios están funcionando
check_service() {
    local service=$1
    local port=$2
    local endpoint=${3:-"/"}
    
    log_info "Verificando $service en puerto $port..."
    
    for i in {1..30}; do
        if curl -s -f "http://localhost:$port$endpoint" > /dev/null 2>&1; then
            log_info "✅ $service está funcionando"
            return 0
        fi
        sleep 2
    done
    
    log_error "❌ $service no está respondiendo"
    return 1
}

# Verificar servicios
check_service "Prometheus" "9090" "/-/healthy"
check_service "Grafana" "3001" "/api/health"
check_service "AlertManager" "9093" "/-/healthy"
check_service "Loki" "3100" "/ready"
check_service "Uptime Kuma" "3002"

log_step "6. Configurando dashboards predeterminados..."

# Crear dashboard básico para la aplicación
cat > monitoring/grafana/dashboards/app-overview.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "TuApp - Overview",
    "tags": ["tuapp"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": "Active Users"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF

log_step "7. Configurando alertas de prueba..."

# Crear script para probar alertas
cat > scripts/test-alerts.sh << 'EOF'
#!/bin/bash

echo "Enviando alerta de prueba..."

# Enviar alerta de prueba a AlertManager
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning",
        "instance": "test-instance"
      },
      "annotations": {
        "summary": "Esta es una alerta de prueba",
        "description": "Alerta generada para probar el sistema de notificaciones"
      }
    }
  ]'

echo "Alerta de prueba enviada. Revisa tu email y Slack."
EOF

chmod +x scripts/test-alerts.sh

log_step "8. Configurando monitoreo externo..."

# Configurar script para monitoreo externo
cat > scripts/external-monitoring.sh << 'EOF'
#!/bin/bash

# Script para configurar monitoreo externo con UptimeRobot o similar
# Usar: ./scripts/external-monitoring.sh

DOMAIN=${1:-tudominio.com}

echo "Configurando monitoreo externo para ${DOMAIN}"

# Lista de endpoints para monitorear
ENDPOINTS=(
  "https://${DOMAIN}"
  "https://${DOMAIN}/api/health"
  "https://${DOMAIN}/api/metrics"
)

echo "Endpoints para monitorear:"
for endpoint in "${ENDPOINTS[@]}"; do
  echo "  - $endpoint"
done

echo ""
echo "Configuración manual necesaria:"
echo "1. Crear cuenta en UptimeRobot.com"
echo "2. Agregar cada endpoint como monitor"
echo "3. Configurar alertas por email/SMS"
echo "4. Configurar webhook para Slack si es necesario"
echo ""
echo "Alternativamente, usar Uptime Kuma en http://localhost:3002"
EOF

chmod +x scripts/external-monitoring.sh

log_info "Stack de monitoreo configurado exitosamente"

# Mostrar información de acceso
echo
echo "=================== MONITOREO CONFIGURADO ==================="
echo
log_info "Servicios disponibles:"
echo "  📊 Grafana:        http://localhost:3001 (admin/admin123)"
echo "  📈 Prometheus:     http://localhost:9090"
echo "  🚨 AlertManager:   http://localhost:9093"
echo "  📋 Loki:          http://localhost:3100"
echo "  ⏱️  Uptime Kuma:   http://localhost:3002"
echo
log_info "Dashboards principales:"
echo "  - App Overview:    http://localhost:3001/d/app-overview"
echo "  - Node Exporter:   http://localhost:3001/d/node-exporter"
echo "  - Docker:          http://localhost:3001/d/docker"
echo
log_info "Alertas configuradas:"
echo "  - Email:           admin@${DOMAIN}"
echo "  - Slack:           #alerts (configurar webhook)"
echo "  - Prueba:          ./scripts/test-alerts.sh"
echo
log_info "Monitoreo externo:"
echo "  - Configurar:      ./scripts/external-monitoring.sh"
echo "  - Uptime Kuma:     http://localhost:3002"
echo
log_warn "SIGUIENTE PASOS:"
echo "  1. Cambiar contraseña de Grafana"
echo "  2. Configurar webhook de Slack"
echo "  3. Configurar SMTP para alertas por email"
echo "  4. Probar alertas: ./scripts/test-alerts.sh"
echo "  5. Configurar monitoreo externo"
echo
log_warn "ARCHIVOS DE CONFIGURACIÓN:"
echo "  - monitoring.env"
echo "  - monitoring/prometheus/prometheus.yml"
echo "  - monitoring/alertmanager/alertmanager.yml"
echo "  - monitoring/grafana/dashboards/"
echo
echo "=============================================================="