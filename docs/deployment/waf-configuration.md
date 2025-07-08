# 🛡️ CONFIGURACIÓN WAF Y PROTECCIÓN DDOS - TuAppDeAccesorios

**Guía completa de configuración de Web Application Firewall y protección contra DDoS**

---

## 🎯 **RESUMEN EJECUTIVO**

### **Estado: Recomendaciones Listas para Implementar** 🚀
- ✅ **Configuración Cloudflare** - Reglas WAF definidas
- ✅ **Protección DDoS** - Múltiples capas de defensa
- ✅ **Bot Protection** - Detección y mitigación
- ✅ **Rate Limiting** - Protección a nivel CDN
- ⏳ **Implementación** - Pendiente activación

---

## 🌐 **CLOUDFLARE WAF CONFIGURACIÓN**

### **Configuración Inicial**

#### **1. Configuración Básica del Dominio**
```javascript
// Configuración DNS
// Tipo: A
// Nombre: tuapp (o tu subdominio)
// Contenido: [IP_DE_RENDER]
// Proxy: Activado (nube naranja)
// TTL: Automático

// Configuración SSL/TLS
// Modo: Full (strict)
// Certificado: Universal SSL habilitado
// HSTS: Habilitado
// Minimum TLS Version: 1.2
```

#### **2. Configuración de Seguridad**
```javascript
// Security Level: High
// DDoS Protection: Activado
// Bot Fight Mode: Activado
// Browser Integrity Check: Activado
// Challenge Passage: 30 minutos
```

---

## 🛡️ **REGLAS WAF PERSONALIZADAS**

### **Regla 1: Protección contra SQL Injection**
```javascript
// Nombre: Block SQL Injection Attempts
// Descripción: Bloquea intentos de inyección SQL
// Acción: Block
// Prioridad: 1

// Condiciones:
(
  http.request.uri.query contains "union select" or
  http.request.uri.query contains "drop table" or
  http.request.uri.query contains "insert into" or
  http.request.uri.query contains "delete from" or
  http.request.uri.query contains "' or 1=1" or
  http.request.uri.query contains "' or '1'='1" or
  http.request.body contains "union select" or
  http.request.body contains "drop table" or
  http.request.body contains "insert into" or
  http.request.body contains "delete from" or
  http.request.body contains "' or 1=1" or
  http.request.body contains "' or '1'='1"
)
```

### **Regla 2: Protección contra XSS**
```javascript
// Nombre: Block XSS Attempts
// Descripción: Bloquea intentos de Cross-Site Scripting
// Acción: Block
// Prioridad: 2

// Condiciones:
(
  http.request.uri.query contains "<script" or
  http.request.uri.query contains "javascript:" or
  http.request.uri.query contains "onload=" or
  http.request.uri.query contains "onerror=" or
  http.request.uri.query contains "onclick=" or
  http.request.uri.query contains "eval(" or
  http.request.body contains "<script" or
  http.request.body contains "javascript:" or
  http.request.body contains "onload=" or
  http.request.body contains "onerror=" or
  http.request.body contains "onclick=" or
  http.request.body contains "eval("
)
```

### **Regla 3: Protección de Endpoints Admin**
```javascript
// Nombre: Protect Admin Endpoints
// Descripción: Protege endpoints administrativos
// Acción: Challenge
// Prioridad: 3

// Condiciones:
(
  http.request.uri.path contains "/admin/" or
  http.request.uri.path contains "/api/admin/" or
  http.request.uri.path contains "/debug/" or
  http.request.uri.path contains "/internal/"
) and not (
  ip.src in {192.168.1.0/24 10.0.0.0/24}  // IPs de oficina
)
```

### **Regla 4: Protección contra Bots Maliciosos**
```javascript
// Nombre: Block Malicious Bots
// Descripción: Bloquea bots maliciosos conocidos
// Acción: Block
// Prioridad: 4

// Condiciones:
(
  http.user_agent contains "sqlmap" or
  http.user_agent contains "nikto" or
  http.user_agent contains "dirb" or
  http.user_agent contains "dirbuster" or
  http.user_agent contains "nmap" or
  http.user_agent contains "masscan" or
  http.user_agent contains "zgrab" or
  http.user_agent contains "python-requests/2.6.0" or
  http.user_agent contains "curl/7.12.1" or
  http.user_agent eq ""
)
```

### **Regla 5: Rate Limiting por IP**
```javascript
// Nombre: Rate Limit by IP
// Descripción: Límite de requests por IP
// Acción: Block
// Prioridad: 5

// Condiciones:
(
  rate(1m) > 100
) and not (
  ip.src in {192.168.1.0/24 10.0.0.0/24}  // IPs de oficina
)
```

### **Regla 6: Protección de Login**
```javascript
// Nombre: Protect Login Endpoints
// Descripción: Protección especial para endpoints de login
// Acción: Challenge
// Prioridad: 6

// Condiciones:
(
  http.request.uri.path eq "/auth/login" or
  http.request.uri.path eq "/api/auth/login"
) and (
  rate(5m) > 10
)
```

---

## 🚨 **PROTECCIÓN DDOS MULTICAPA**

### **Capa 1: Cloudflare DDoS Protection**
```javascript
// Configuración DDoS
{
  "ddos_protection": {
    "enabled": true,
    "sensitivity": "high",
    "advanced_rate_limiting": true,
    "volumetric_protection": true,
    "protocol_protection": true,
    "application_layer_protection": true
  }
}
```

### **Capa 2: Rate Limiting Avanzado**
```javascript
// Rate Limiting Rules
[
  {
    "name": "Global Rate Limit",
    "match": "all",
    "threshold": 1000,
    "period": 60,
    "action": "simulate"  // Cambiar a "block" en producción
  },
  {
    "name": "API Rate Limit",
    "match": "http.request.uri.path matches \"^/api/.*\"",
    "threshold": 100,
    "period": 60,
    "action": "challenge"
  },
  {
    "name": "Auth Rate Limit",
    "match": "http.request.uri.path matches \"^/auth/.*\"",
    "threshold": 5,
    "period": 300,
    "action": "block"
  }
]
```

### **Capa 3: Bot Management**
```javascript
// Bot Management Configuration
{
  "bot_management": {
    "enabled": true,
    "fight_mode": true,
    "challenge_bad_bots": true,
    "allow_verified_bots": true,
    "static_resource_protection": false,
    "javascript_detections": true,
    "machine_learning": true
  }
}
```

---

## 🔧 **CONFIGURACIÓN AVANZADA**

### **Geo-blocking**
```javascript
// Regla: Geo-blocking
// Descripción: Bloquear países de alto riesgo
// Acción: Block
// Prioridad: 10

// Condiciones:
(
  ip.geoip.country in {"CN" "RU" "KP" "IR"}
) and not (
  http.request.uri.path contains "/api/public/"
)
```

### **Protección contra Scraping**
```javascript
// Regla: Anti-Scraping
// Descripción: Detectar y bloquear scraping
// Acción: Challenge
// Prioridad: 11

// Condiciones:
(
  http.request.uri.path contains "/api/products" and
  rate(1m) > 50
) or (
  http.user_agent contains "bot" and
  not cf.bot_management.verified_bot
)
```

### **Protección de Archivos Sensibles**
```javascript
// Regla: Protect Sensitive Files
// Descripción: Proteger archivos sensibles
// Acción: Block
// Prioridad: 12

// Condiciones:
(
  http.request.uri.path contains ".env" or
  http.request.uri.path contains ".git" or
  http.request.uri.path contains ".sql" or
  http.request.uri.path contains ".bak" or
  http.request.uri.path contains "backup" or
  http.request.uri.path contains "config.json" or
  http.request.uri.path contains "database.yml"
)
```

---

## 📊 **CONFIGURACIÓN DE MONITOREO**

### **Alertas de Seguridad**
```javascript
// Configuración de Alertas
{
  "security_alerts": {
    "enabled": true,
    "email_notifications": ["admin@tuapp.com"],
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "alert_triggers": [
      {
        "type": "ddos_attack",
        "threshold": 10000,
        "period": 300
      },
      {
        "type": "waf_blocks",
        "threshold": 100,
        "period": 60
      },
      {
        "type": "bot_activity",
        "threshold": 500,
        "period": 300
      }
    ]
  }
}
```

### **Dashboard de Seguridad**
```javascript
// Métricas a Monitorear
{
  "security_metrics": {
    "total_requests": "rate(1h)",
    "blocked_requests": "rate(1h)",
    "challenged_requests": "rate(1h)",
    "bot_requests": "rate(1h)",
    "top_blocked_countries": "count(24h)",
    "top_attack_patterns": "count(24h)",
    "bandwidth_usage": "sum(1h)",
    "threat_score_distribution": "histogram(1h)"
  }
}
```

---

## 🛠️ **CONFIGURACIÓN TERRAFORM**

### **Archivo de Configuración**
```hcl
# cloudflare_waf.tf

terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Zone configuration
resource "cloudflare_zone" "tuapp" {
  zone = var.domain_name
  plan = "free"  # o "pro" para características avanzadas
}

# DNS record
resource "cloudflare_record" "tuapp" {
  zone_id = cloudflare_zone.tuapp.id
  name    = var.subdomain
  value   = var.render_ip
  type    = "A"
  proxied = true
}

# WAF Rule: SQL Injection Protection
resource "cloudflare_ruleset" "sql_injection_protection" {
  zone_id = cloudflare_zone.tuapp.id
  name    = "SQL Injection Protection"
  kind    = "zone"
  phase   = "http_request_firewall_custom"

  rules {
    action = "block"
    expression = <<-EOT
      (
        http.request.uri.query contains "union select" or
        http.request.uri.query contains "drop table" or
        http.request.uri.query contains "' or 1=1" or
        http.request.body contains "union select" or
        http.request.body contains "drop table" or
        http.request.body contains "' or 1=1"
      )
    EOT
    description = "Block SQL injection attempts"
    enabled     = true
  }
}

# WAF Rule: XSS Protection
resource "cloudflare_ruleset" "xss_protection" {
  zone_id = cloudflare_zone.tuapp.id
  name    = "XSS Protection"
  kind    = "zone"
  phase   = "http_request_firewall_custom"

  rules {
    action = "block"
    expression = <<-EOT
      (
        http.request.uri.query contains "<script" or
        http.request.uri.query contains "javascript:" or
        http.request.uri.query contains "onload=" or
        http.request.body contains "<script" or
        http.request.body contains "javascript:" or
        http.request.body contains "onload="
      )
    EOT
    description = "Block XSS attempts"
    enabled     = true
  }
}

# Rate Limiting Rules
resource "cloudflare_rate_limit" "api_rate_limit" {
  zone_id = cloudflare_zone.tuapp.id
  
  threshold = 100
  period    = 60
  
  match {
    request {
      url_pattern = "${var.domain_name}/api/*"
      schemes     = ["HTTP", "HTTPS"]
      methods     = ["GET", "POST", "PUT", "DELETE"]
    }
  }
  
  action {
    mode    = "challenge"
    timeout = 300
  }
}

# Bot Management
resource "cloudflare_bot_management" "tuapp" {
  zone_id                   = cloudflare_zone.tuapp.id
  enable_js                 = true
  fight_mode                = true
  using_latest_model        = true
  optimize_wordpress        = false
  suppress_session_score    = false
  auto_update_model         = true
}

# Security Level
resource "cloudflare_zone_settings_override" "tuapp" {
  zone_id = cloudflare_zone.tuapp.id
  
  settings {
    security_level         = "high"
    browser_check          = "on"
    challenge_ttl          = 1800
    ssl                    = "strict"
    min_tls_version        = "1.2"
    opportunistic_onion    = "on"
    automatic_https_rewrites = "on"
  }
}

# DDoS Protection (Enterprise feature)
resource "cloudflare_spectrum_application" "ddos_protection" {
  count = var.cloudflare_plan == "enterprise" ? 1 : 0
  
  zone_id = cloudflare_zone.tuapp.id
  protocol = "tcp/22"
  dns {
    name = "ssh.${var.domain_name}"
    type = "CNAME"
  }
  
  origin_direct = [var.render_ip]
  origin_port   = 22
  
  traffic_type = "direct"
  tls          = "off"
}
```

### **Variables Configuration**
```hcl
# variables.tf

variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "tuapp.com"
}

variable "subdomain" {
  description = "Subdomain for the application"
  type        = string
  default     = "api"
}

variable "render_ip" {
  description = "Render application IP address"
  type        = string
}

variable "cloudflare_plan" {
  description = "Cloudflare plan (free, pro, business, enterprise)"
  type        = string
  default     = "free"
}
```

---

## 🔍 **TESTING Y VALIDACIÓN**

### **Tests de WAF**
```bash
#!/bin/bash
# waf_test.sh

DOMAIN="https://tuapp.com"
echo "🧪 Testing WAF Configuration..."

# Test 1: SQL Injection
echo "Testing SQL Injection protection..."
curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/api/users?id=1' OR 1=1--"
# Expected: 403 (Blocked)

# Test 2: XSS Protection
echo "Testing XSS protection..."
curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/api/products?name=<script>alert('xss')</script>"
# Expected: 403 (Blocked)

# Test 3: Rate Limiting
echo "Testing rate limiting..."
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/api/products"
done
# Expected: 429 después de ciertos intentos

# Test 4: Bot Detection
echo "Testing bot detection..."
curl -s -o /dev/null -w "%{http_code}" -H "User-Agent: sqlmap/1.0" "$DOMAIN/"
# Expected: 403 (Blocked)

# Test 5: Geo-blocking
echo "Testing geo-blocking..."
curl -s -o /dev/null -w "%{http_code}" -H "CF-IPCountry: CN" "$DOMAIN/"
# Expected: 403 (Blocked)

echo "✅ WAF tests completed"
```

### **Monitoring Script**
```bash
#!/bin/bash
# waf_monitor.sh

# Cloudflare Analytics API
API_TOKEN="your_cloudflare_api_token"
ZONE_ID="your_zone_id"

# Get security events
curl -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/security/events" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json"

# Get firewall events
curl -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/firewall/events" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json"

# Get rate limiting events
curl -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rate_limits" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 📱 **CONFIGURACIÓN MÓVIL**

### **Protección de API Móvil**
```javascript
// Regla: Mobile API Protection
// Descripción: Protección especial para APIs móviles
// Acción: Challenge
// Prioridad: 15

// Condiciones:
(
  http.request.uri.path contains "/api/mobile/" and
  not http.request.headers["X-Mobile-App-Version"] exists
) or (
  http.request.uri.path contains "/api/mobile/" and
  not http.request.headers["X-API-Key"] exists
)
```

### **Validación de Certificados**
```javascript
// Regla: Mobile Certificate Validation
// Descripción: Validar certificados de aplicaciones móviles
// Acción: Block
// Prioridad: 16

// Condiciones:
(
  http.request.uri.path contains "/api/mobile/" and
  not http.request.headers["X-App-Signature"] matches "^[a-f0-9]{64}$"
)
```

---

## 🚀 **IMPLEMENTACIÓN PASO A PASO**

### **Fase 1: Configuración Básica (Día 1)**
1. **Crear cuenta Cloudflare**
2. **Agregar dominio a Cloudflare**
3. **Configurar DNS con proxy activado**
4. **Activar SSL/TLS Full (Strict)**
5. **Configurar Security Level: High**

### **Fase 2: Reglas WAF (Día 2-3)**
1. **Implementar reglas básicas de WAF**
2. **Configurar rate limiting**
3. **Activar Bot Fight Mode**
4. **Configurar geo-blocking si es necesario**

### **Fase 3: Monitoreo y Ajustes (Día 4-7)**
1. **Configurar alertas de seguridad**
2. **Monitorear falsos positivos**
3. **Ajustar reglas según patrones de tráfico**
4. **Implementar reglas personalizadas**

### **Fase 4: Optimización (Semana 2)**
1. **Análisis de logs y métricas**
2. **Optimización de reglas**
3. **Configuración de cache**
4. **Tests de rendimiento**

---

## 💰 **CONSIDERACIONES DE COSTOS**

### **Plan Free (Cloudflare)**
- ✅ WAF básico
- ✅ DDoS protection básico
- ✅ SSL/TLS gratuito
- ✅ 5 reglas de firewall
- ❌ Bot Management avanzado
- ❌ Rate limiting avanzado

### **Plan Pro ($20/mes)**
- ✅ Todo lo del plan Free
- ✅ 20 reglas de firewall
- ✅ Rate limiting avanzado
- ✅ Image optimization
- ✅ Analytics avanzados
- ❌ Bot Management completo

### **Plan Business ($200/mes)**
- ✅ Todo lo del plan Pro
- ✅ 100 reglas de firewall
- ✅ Bot Management completo
- ✅ Load balancing
- ✅ Advanced DDoS protection
- ✅ Priority support

---

## 📋 **CHECKLIST DE IMPLEMENTACIÓN**

### **Pre-implementación**
- [ ] Backup de configuración DNS actual
- [ ] Documentar IPs de oficina para whitelist
- [ ] Preparar plan de rollback
- [ ] Configurar monitoreo de uptime

### **Durante la implementación**
- [ ] Configurar Cloudflare paso a paso
- [ ] Probar cada regla individualmente
- [ ] Monitorear logs en tiempo real
- [ ] Verificar funcionalidad de la aplicación

### **Post-implementación**
- [ ] Verificar métricas de seguridad
- [ ] Documentar cambios realizados
- [ ] Entrenar equipo en nueva configuración
- [ ] Programar revisiones periódicas

---

## 🔮 **ROADMAP DE MEJORAS**

### **Próximas mejoras**
- [ ] **Machine Learning Rules** - Reglas basadas en ML
- [ ] **Advanced Bot Protection** - Protección avanzada contra bots
- [ ] **API Security** - Protección específica para APIs
- [ ] **Zero Trust Architecture** - Implementación de Zero Trust
- [ ] **Custom Certificates** - Certificados personalizados
- [ ] **Load Balancing** - Balanceador de carga
- [ ] **Origin Shield** - Protección adicional del origen

---

**📋 Documento actualizado: 2024-01-07**

*Esta configuración WAF proporciona protección enterprise-level contra las amenazas más comunes y se puede implementar gradualmente según las necesidades del proyecto.*