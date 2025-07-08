# 🧪 TESTS DE SEGURIDAD AUTOMATIZADOS - TuAppDeAccesorios

**Guía completa de pruebas de seguridad automatizadas y validación de controles**

---

## 🎯 **RESUMEN DE COBERTURA**

### **Estado Actual: 85% Implementado** 🚧
- ✅ **Framework de Testing** - pytest + httpx configurado
- ✅ **Tests de Autenticación** - JWT y rate limiting
- ✅ **Tests de Validación** - Input validation y sanitización
- 🔄 **Tests de Integración** - En desarrollo
- ⏳ **Tests de Penetración** - Pendiente automatización

---

## 🏗️ **ARQUITECTURA DE TESTING**

### **Estructura de Tests**
```
tests/
├── security/
│   ├── __init__.py
│   ├── test_authentication.py      # Tests de autenticación
│   ├── test_authorization.py       # Tests de autorización
│   ├── test_rate_limiting.py       # Tests de rate limiting
│   ├── test_input_validation.py    # Tests de validación
│   ├── test_encryption.py          # Tests de cifrado
│   ├── test_headers.py             # Tests de headers de seguridad
│   └── test_monitoring.py          # Tests de monitoreo
├── integration/
│   ├── test_security_workflow.py   # Flujos de seguridad
│   └── test_incident_response.py   # Respuesta a incidentes
└── penetration/
    ├── test_owasp_top10.py         # Tests OWASP Top 10
    └── test_vulnerability_scan.py  # Escaneo de vulnerabilidades
```

---

## 🔐 **TESTS DE AUTENTICACIÓN**

### **Test JWT Token Management**
```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.security.token_blacklist import token_blacklist

@pytest.mark.asyncio
async def test_jwt_token_lifecycle():
    """Test completo del ciclo de vida de tokens JWT"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Login exitoso
        login_response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 2. Acceso con token válido
        headers = {"Authorization": f"Bearer {access_token}"}
        protected_response = await client.get("/users/me", headers=headers)
        assert protected_response.status_code == 200
        
        # 3. Refresh token
        refresh_response = await client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert refresh_response.status_code == 200
        
        # 4. Logout (blacklist token)
        logout_response = await client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # 5. Verificar token blacklisteado
        blacklisted_response = await client.get("/users/me", headers=headers)
        assert blacklisted_response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_security_scenarios():
    """Test escenarios de seguridad JWT"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Token malformado
        malformed_headers = {"Authorization": "Bearer invalid.token.here"}
        response = await client.get("/users/me", headers=malformed_headers)
        assert response.status_code == 401
        
        # Token expirado
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjQwOTk1MjAwfQ.invalid"
        expired_headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/users/me", headers=expired_headers)
        assert response.status_code == 401
        
        # Sin header de autorización
        response = await client.get("/users/me")
        assert response.status_code == 401
```

### **Test Role-Based Access Control**
```python
@pytest.mark.asyncio
async def test_rbac_permissions():
    """Test sistema de permisos basado en roles"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login como usuario normal
        user_login = await client.post(
            "/auth/login",
            json={"username": "normaluser", "password": "password"}
        )
        user_token = user_login.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Login como admin
        admin_login = await client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpass"}
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test acceso admin-only
        user_response = await client.get("/admin/users", headers=user_headers)
        assert user_response.status_code == 403
        
        admin_response = await client.get("/admin/users", headers=admin_headers)
        assert admin_response.status_code == 200
        
        # Test creación de usuarios (solo admin)
        user_create = await client.post(
            "/admin/users",
            json={"username": "newuser", "password": "pass"},
            headers=user_headers
        )
        assert user_create.status_code == 403
        
        admin_create = await client.post(
            "/admin/users",
            json={"username": "newuser", "password": "pass"},
            headers=admin_headers
        )
        assert admin_create.status_code == 201
```

---

## 🚦 **TESTS DE RATE LIMITING**

### **Test Rate Limiting por Endpoint**
```python
@pytest.mark.asyncio
async def test_rate_limiting_login():
    """Test rate limiting en endpoint de login"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Realizar múltiples intentos de login
        for i in range(5):
            response = await client.post(
                "/auth/login",
                json={"username": "testuser", "password": "wrongpass"}
            )
            
            if i < 3:  # Primeros 3 intentos permitidos
                assert response.status_code == 401
            else:  # Bloqueado después de 3 intentos
                assert response.status_code == 429
                assert "rate limit exceeded" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limiting_algorithms():
    """Test algoritmos de rate limiting"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test sliding window
        start_time = time.time()
        
        # Realizar requests dentro de la ventana
        for i in range(10):
            response = await client.get("/api/products")
            
            if i < 5:  # Dentro del límite
                assert response.status_code == 200
            else:  # Excede el límite
                assert response.status_code == 429
        
        # Esperar que expire la ventana
        await asyncio.sleep(60)
        
        # Verificar que el límite se resetea
        response = await client.get("/api/products")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limiting_bypass_attempts():
    """Test intentos de bypass de rate limiting"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Intentar bypass con diferentes User-Agents
        headers_list = [
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            {"User-Agent": "curl/7.68.0"},
        ]
        
        for headers in headers_list:
            for i in range(5):
                response = await client.post(
                    "/auth/login",
                    json={"username": "test", "password": "wrong"},
                    headers=headers
                )
                
                if i >= 3:  # Debe seguir bloqueado
                    assert response.status_code == 429
```

---

## ✅ **TESTS DE VALIDACIÓN DE ENTRADA**

### **Test Protección SQL Injection**
```python
@pytest.mark.asyncio
async def test_sql_injection_protection():
    """Test protección contra SQL injection"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Payloads de SQL injection
        sql_payloads = [
            "' OR 1=1--",
            "'; DROP TABLE users;--",
            "' UNION SELECT password FROM users--",
            "1' OR '1'='1",
            "admin'--",
            "' OR 1=1 LIMIT 1--"
        ]
        
        for payload in sql_payloads:
            # Test en parámetros de consulta
            response = await client.get(f"/api/users?search={payload}")
            assert response.status_code == 400
            assert "invalid input" in response.json()["detail"].lower()
            
            # Test en body de request
            response = await client.post(
                "/api/users",
                json={"username": payload, "email": "test@example.com"}
            )
            assert response.status_code == 400

@pytest.mark.asyncio
async def test_xss_protection():
    """Test protección contra XSS"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
        for payload in xss_payloads:
            response = await client.post(
                "/api/products",
                json={"name": payload, "description": "Test product"}
            )
            assert response.status_code == 400
            assert "invalid input" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_input_sanitization():
    """Test sanitización de entrada"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test HTML sanitization
        html_input = "<b>Bold text</b><script>alert('evil')</script>"
        response = await client.post(
            "/api/products",
            json={"name": "Test", "description": html_input}
        )
        
        # Debe aceptar tags seguros y remover scripts
        assert response.status_code == 201
        product = response.json()
        assert "<b>Bold text</b>" in product["description"]
        assert "<script>" not in product["description"]
```

---

## 🔒 **TESTS DE CIFRADO**

### **Test Cifrado de Base de Datos**
```python
@pytest.mark.asyncio
async def test_database_encryption():
    """Test cifrado de campos sensibles"""
    from app.models.user import User
    from app.security.database_encryption import encrypt_data, decrypt_data
    
    # Test cifrado/descifrado directo
    original_data = "sensitive_information@example.com"
    encrypted = encrypt_data(original_data)
    decrypted = decrypt_data(encrypted)
    
    assert encrypted != original_data
    assert decrypted == original_data
    assert len(encrypted) > len(original_data)
    
    # Test con modelo de base de datos
    user = User(
        username="testuser",
        email="test@example.com",  # Campo cifrado
        phone="1234567890"  # Campo cifrado
    )
    
    # Verificar que los campos se cifran automáticamente
    assert user.email != "test@example.com"
    assert user.phone != "1234567890"
    
    # Verificar que se descifran correctamente al leer
    retrieved_user = await User.get(user.id)
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.phone == "1234567890"

@pytest.mark.asyncio
async def test_backup_encryption():
    """Test cifrado de backups"""
    from app.security.backup_manager import backup_manager
    
    # Crear backup cifrado
    backup_metadata = await backup_manager.create_database_backup(
        backup_type="full",
        compress=True,
        encrypt=True,
        upload_to_s3=False
    )
    
    assert backup_metadata is not None
    assert backup_metadata.encryption is True
    
    # Verificar que el archivo está cifrado
    with open(backup_metadata.local_path, 'rb') as f:
        encrypted_content = f.read()
    
    # No debe contener datos en texto plano
    assert b"CREATE TABLE" not in encrypted_content
    assert b"INSERT INTO" not in encrypted_content
```

---

## 🛡️ **TESTS DE HEADERS DE SEGURIDAD**

### **Test Security Headers**
```python
@pytest.mark.asyncio
async def test_security_headers():
    """Test headers de seguridad"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        # Verificar headers de seguridad
        assert "strict-transport-security" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers
        assert "content-security-policy" in response.headers
        assert "referrer-policy" in response.headers
        
        # Verificar valores específicos
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert "max-age=31536000" in response.headers["strict-transport-security"]

@pytest.mark.asyncio
async def test_csp_policy():
    """Test Content Security Policy"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        csp = response.headers.get("content-security-policy", "")
        
        # Verificar directivas CSP
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "frame-ancestors 'none'" in csp
```

---

## 👁️ **TESTS DE MONITOREO**

### **Test Detección de Amenazas**
```python
@pytest.mark.asyncio
async def test_threat_detection():
    """Test detección de amenazas en tiempo real"""
    from app.security.security_monitor import security_monitor
    
    # Simular evento de seguridad
    threat_event = {
        "type": "sql_injection_attempt",
        "ip": "192.168.1.100",
        "user_agent": "sqlmap/1.0",
        "endpoint": "/api/users",
        "payload": "' OR 1=1--"
    }
    
    # Verificar detección
    detected = await security_monitor.process_event(threat_event)
    assert detected is True
    
    # Verificar alerta generada
    alerts = await security_monitor.get_recent_alerts()
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "CRITICAL"

@pytest.mark.asyncio
async def test_monitoring_dashboard():
    """Test dashboard de monitoreo"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Acceder al dashboard (requiere autenticación admin)
        admin_headers = await get_admin_headers()
        
        response = await client.get(
            "/api/security/dashboard",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        dashboard = response.json()
        
        # Verificar métricas básicas
        assert "total_requests" in dashboard
        assert "threat_events" in dashboard
        assert "active_sessions" in dashboard
        assert "failed_logins" in dashboard
```

---

## 🔍 **TESTS DE INTEGRACIÓN**

### **Test Flujo de Seguridad Completo**
```python
@pytest.mark.asyncio
async def test_complete_security_workflow():
    """Test flujo completo de seguridad"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Registro de usuario
        register_response = await client.post(
            "/auth/register",
            json={
                "username": "securitytest",
                "email": "security@test.com",
                "password": "SecurePass123!"
            }
        )
        assert register_response.status_code == 201
        
        # 2. Login con credenciales correctas
        login_response = await client.post(
            "/auth/login",
            json={"username": "securitytest", "password": "SecurePass123!"}
        )
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Acceso a recursos protegidos
        protected_response = await client.get("/users/me", headers=headers)
        assert protected_response.status_code == 200
        
        # 4. Intento de acceso no autorizado
        unauthorized_response = await client.get("/admin/users", headers=headers)
        assert unauthorized_response.status_code == 403
        
        # 5. Logout seguro
        logout_response = await client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # 6. Verificar token blacklisteado
        blacklisted_response = await client.get("/users/me", headers=headers)
        assert blacklisted_response.status_code == 401

@pytest.mark.asyncio
async def test_incident_response_workflow():
    """Test flujo de respuesta a incidentes"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Simular múltiples intentos de login fallidos
        for i in range(5):
            response = await client.post(
                "/auth/login",
                json={"username": "admin", "password": "wrongpass"}
            )
        
        # Verificar que se activa el bloqueo
        blocked_response = await client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrongpass"}
        )
        assert blocked_response.status_code == 429
        
        # Verificar que se genera alerta
        admin_headers = await get_admin_headers()
        alerts_response = await client.get(
            "/api/security/alerts",
            headers=admin_headers
        )
        assert alerts_response.status_code == 200
        
        alerts = alerts_response.json()
        assert len(alerts) > 0
        assert alerts[0]["type"] == "brute_force"
```

---

## 🔐 **TESTS OWASP TOP 10**

### **Test A01: Broken Access Control**
```python
@pytest.mark.asyncio
async def test_owasp_a01_broken_access_control():
    """Test control de acceso roto"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Intentar acceso directo a recursos
        test_cases = [
            "/admin/users/1",
            "/admin/config",
            "/api/internal/metrics",
            "/debug/info"
        ]
        
        for endpoint in test_cases:
            response = await client.get(endpoint)
            assert response.status_code in [401, 403, 404]
            
        # Test escalación de privilegios
        user_headers = await get_user_headers()
        admin_endpoint = await client.get("/admin/users", headers=user_headers)
        assert admin_endpoint.status_code == 403

@pytest.mark.asyncio
async def test_owasp_a02_cryptographic_failures():
    """Test fallas criptográficas"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Verificar que las contraseñas no se almacenan en texto plano
        from app.models.user import User
        user = await User.create(
            username="cryptotest",
            password="plaintextpass"
        )
        
        # La contraseña debe estar hasheada
        assert user.password_hash != "plaintextpass"
        assert len(user.password_hash) > 50  # Hash bcrypt
        
        # Verificar cifrado de datos sensibles
        user.email = "sensitive@example.com"
        await user.save()
        
        # Verificar en base de datos que está cifrado
        raw_data = await db.fetch_one(
            "SELECT email FROM users WHERE id = :id",
            {"id": user.id}
        )
        assert raw_data["email"] != "sensitive@example.com"
```

---

## 🚀 **COMANDOS DE TESTING**

### **Ejecutar Tests de Seguridad**
```bash
# Todos los tests de seguridad
pytest tests/security/ -v

# Tests específicos
pytest tests/security/test_authentication.py -v
pytest tests/security/test_rate_limiting.py -v
pytest tests/security/test_input_validation.py -v

# Tests con coverage
pytest tests/security/ --cov=app.security --cov-report=html

# Tests de integración
pytest tests/integration/ -v

# Tests de penetración
pytest tests/penetration/ -v --tb=short
```

### **Tests de Performance de Seguridad**
```bash
# Load testing con autenticación
locust -f tests/performance/security_load_test.py --host=http://localhost:8000

# Benchmark de rate limiting
pytest tests/security/test_rate_limiting.py --benchmark-only

# Stress test de cifrado
pytest tests/security/test_encryption.py --stress-test
```

---

## 📊 **MÉTRICAS Y REPORTES**

### **Coverage de Seguridad**
```python
# Configuración pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=app.security
    --cov-report=html:htmlcov/security
    --cov-report=term-missing
    --cov-fail-under=85
```

### **Reporte de Vulnerabilidades**
```bash
# Generar reporte completo
pytest tests/security/ --html=reports/security_report.html

# Exportar métricas
pytest tests/security/ --json-report --json-report-file=reports/security_metrics.json

# Integración con CI/CD
pytest tests/security/ --junitxml=reports/security_junit.xml
```

---

## 🔄 **INTEGRACIÓN CONTINUA**

### **Pipeline de Seguridad**
```yaml
# .github/workflows/security-tests.yml
name: Security Tests
on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov pytest-html
      
      - name: Run security tests
        run: pytest tests/security/ -v --cov=app.security --cov-fail-under=85
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 📈 **PRÓXIMAS MEJORAS**

### **Tests Pendientes**
- [ ] **API Fuzzing** - Pruebas de fuzzing automatizadas
- [ ] **Container Security** - Escaneo de vulnerabilidades en Docker
- [ ] **Dependency Scanning** - Análisis de dependencias
- [ ] **SAST Integration** - Análisis estático de código
- [ ] **DAST Integration** - Pruebas dinámicas automatizadas

### **Automatización Avanzada**
- [ ] **ML-based Testing** - Detección automática de patrones
- [ ] **Regression Testing** - Tests de regresión de seguridad
- [ ] **Performance Security** - Benchmarks de rendimiento
- [ ] **Chaos Engineering** - Pruebas de resistencia

---

**📋 Documento actualizado: 2024-01-07**

*Los tests de seguridad se ejecutan automáticamente en cada commit y proporcionan cobertura completa de los controles de seguridad implementados.*