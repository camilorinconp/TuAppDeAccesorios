import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.main import app
from app.database import Base, get_db_session_maker
from app.dependencies import get_db
from app.crud import create_user, get_user_by_username
from app.schemas import UserCreate
from app.models import UserRole
from app.auth import create_access_token, verify_token, create_refresh_token
from unittest.mock import patch
from jose import JWTError

# Configuración de la base de datos de prueba
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"

# Funciones de utilidad para tests
def assert_valid_token_response(response_data: dict, token_type: str = "bearer"):
    """Verifica que la respuesta contenga tokens válidos"""
    assert "access_token" in response_data, f"access_token not found in response: {response_data}"
    assert "refresh_token" in response_data, f"refresh_token not found in response: {response_data}"
    assert response_data["token_type"] == token_type, f"Expected token_type '{token_type}', got {response_data.get('token_type')}"
    
    # Verificar formato JWT
    access_token = response_data["access_token"]
    assert isinstance(access_token, str), f"access_token should be string, got {type(access_token)}"
    assert len(access_token.split('.')) == 3, f"access_token should be JWT format (3 parts), got: {access_token[:50]}..."

def assert_error_response(response, expected_status: int, expected_message: str = None):
    """Verifica que la respuesta sea un error con el formato esperado"""
    assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
    
    try:
        response_data = response.json()
        assert "detail" in response_data, f"Error response should contain 'detail' field: {response_data}"
        
        if expected_message:
            assert expected_message in response_data["detail"], f"Expected '{expected_message}' in error message, got: {response_data['detail']}"
    except ValueError as e:
        pytest.fail(f"Response is not valid JSON: {e}. Response text: {response.text}")

def assert_valid_user_data(user_data: dict, expected_username: str, expected_role: str):
    """Verifica que los datos de usuario sean válidos"""
    assert "username" in user_data, f"username not found in user data: {user_data}"
    assert "role" in user_data, f"role not found in user data: {user_data}"
    assert user_data["username"] == expected_username, f"Expected username '{expected_username}', got '{user_data['username']}'"
    assert user_data["role"] == expected_role, f"Expected role '{expected_role}', got '{user_data['role']}'"


@pytest.fixture(name="db_session", scope="function")
def db_session_fixture():
    TestingSessionLocal, test_engine = get_db_session_maker(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(name="client", scope="function")
def client_fixture(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="admin_user")
def admin_user_fixture(db_session: Session):
    """Crear usuario admin para pruebas"""
    with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
        admin_user_data = UserCreate(
            username="admin_test",
            password="admin123",
            role=UserRole.admin
        )
        user = create_user(db_session, admin_user_data)
        return user


@pytest.fixture(name="distributor_user")
def distributor_user_fixture(db_session: Session):
    """Crear usuario distribuidor para pruebas"""
    with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
        distributor_user_data = UserCreate(
            username="distributor_test",
            password="dist123",
            role=UserRole.distributor
        )
        user = create_user(db_session, distributor_user_data)
        return user


class TestAuthentication:
    """Tests para autenticación básica"""

    def test_login_admin_success(self, client: TestClient, admin_user):
        """Test login exitoso de admin"""
        with patch('app.utils.security.verify_password', return_value=True):
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
            data = response.json()
            assert "access_token" in data, f"access_token not found in response: {data}"
            assert "refresh_token" in data, f"refresh_token not found in response: {data}"
            assert data["token_type"] == "bearer", f"Expected token_type 'bearer', got {data.get('token_type')}"

    def test_login_distributor_success(self, client: TestClient, distributor_user):
        """Test login exitoso de distribuidor"""
        with patch('app.utils.security.verify_password', return_value=True):
            login_data = {
                "username": "distributor_test",
                "password": "dist123"
            }
            response = client.post("/distributor-token", data=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, admin_user):
        """Test login con contraseña incorrecta"""
        with patch('app.utils.security.verify_password', return_value=False):
            login_data = {
                "username": "admin_test",
                "password": "wrong_password"
            }
            response = client.post("/token", data=login_data)
            
            assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}. Response: {response.text}"
            response_data = response.json()
            assert "detail" in response_data, f"Error detail not found in response: {response_data}"
            assert "Invalid credentials" in response_data["detail"], f"Expected 'Invalid credentials' in error message, got: {response_data['detail']}"

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login con usuario inexistente"""
        login_data = {
            "username": "nonexistent_user",
            "password": "password123"
        }
        response = client.post("/token", data=login_data)
        
        assert response.status_code == 401

    def test_login_empty_credentials(self, client: TestClient):
        """Test login con credenciales vacías"""
        login_data = {
            "username": "",
            "password": ""
        }
        response = client.post("/token", data=login_data)
        
        assert response.status_code == 422  # Validation error


class TestTokenOperations:
    """Tests para operaciones con tokens"""

    def test_create_access_token(self):
        """Test creación de access token"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        assert isinstance(token, str), f"Expected string token, got {type(token)}"
        assert len(token) > 50, f"Token seems too short: {len(token)} characters. Token: {token[:50]}..."
        # Verificar que el token tiene formato JWT (3 partes separadas por puntos)
        parts = token.split('.')
        assert len(parts) == 3, f"JWT should have 3 parts, got {len(parts)}: {parts}"

    def test_create_refresh_token(self):
        """Test creación de refresh token"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verificación de token válido"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    def test_verify_invalid_token(self):
        """Test verificación de token inválido"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises((JWTError, ValueError), match="Invalid token format or signature"):
            verify_token(invalid_token)

    def test_verify_expired_token(self):
        """Test verificación de token expirado"""
        # Crear token que expire inmediatamente
        data = {"sub": "testuser", "role": "admin"}
        expired_time = datetime.utcnow() - timedelta(minutes=1)
        data["exp"] = expired_time
        
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(JWTError, match="Token has expired"):
            verify_token(token)


class TestRefreshToken:
    """Tests para refresh tokens"""

    def test_refresh_token_success(self, client: TestClient, admin_user):
        """Test refresh token exitoso"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Primero hacer login
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            login_response = client.post("/token", data=login_data)
            refresh_token = login_response.json()["refresh_token"]
            
            # Usar refresh token
            response = client.post("/refresh", json={"refresh_token": refresh_token})
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh token inválido"""
        invalid_token = "invalid.refresh.token"
        
        response = client.post("/refresh", json={"refresh_token": invalid_token})
        
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests para endpoints protegidos"""

    def test_protected_endpoint_no_token(self, client: TestClient):
        """Test endpoint protegido sin token"""
        response = client.get("/verify")
        
        assert response.status_code == 401

    def test_protected_endpoint_invalid_token(self, client: TestClient):
        """Test endpoint protegido con token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/verify", headers=headers)
        
        assert response.status_code == 401

    def test_protected_endpoint_valid_token(self, client: TestClient, admin_user):
        """Test endpoint protegido con token válido"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Obtener token válido
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            login_response = client.post("/token", data=login_data)
            token = login_response.json()["access_token"]
            
            # Usar token en endpoint protegido
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/verify", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "admin_test"
            assert data["role"] == "admin"


class TestAuthorizationRoles:
    """Tests para autorización por roles"""

    def test_admin_access_to_admin_endpoint(self, client: TestClient, admin_user):
        """Test acceso de admin a endpoint de admin"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Login como admin
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            login_response = client.post("/token", data=login_data)
            token = login_response.json()["access_token"]
            
            # Acceder a endpoint que requiere admin
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/products/", headers=headers)
            
            assert response.status_code == 200

    def test_distributor_access_to_distributor_endpoint(self, client: TestClient, distributor_user):
        """Test acceso de distribuidor a endpoint de distribuidor"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Login como distribuidor
            login_data = {
                "username": "distributor_test",
                "password": "dist123"
            }
            login_response = client.post("/distributor-token", data=login_data)
            token = login_response.json()["access_token"]
            
            # Acceder a endpoint permitido para distribuidor
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/products/", headers=headers)
            
            assert response.status_code == 200

    def test_distributor_denied_admin_endpoint(self, client: TestClient, distributor_user):
        """Test denegación de acceso de distribuidor a endpoint de admin"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Login como distribuidor
            login_data = {
                "username": "distributor_test",
                "password": "dist123"
            }
            login_response = client.post("/distributor-token", data=login_data)
            token = login_response.json()["access_token"]
            
            # Intentar crear producto (requiere admin)
            headers = {"Authorization": f"Bearer {token}"}
            product_data = {
                "sku": "SKU001",
                "name": "Test Product",
                "description": "Test Description",
                "image_url": "http://example.com/image.jpg",
                "cost_price": 10.0,
                "selling_price": 20.0,
                "stock_quantity": 100
            }
            response = client.post("/products/", json=product_data, headers=headers)
            
            assert response.status_code == 403


class TestLogout:
    """Tests para logout"""

    def test_logout_success(self, client: TestClient, admin_user):
        """Test logout exitoso"""
        with patch('app.utils.security.verify_password', return_value=True):
            # Login primero
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            login_response = client.post("/token", data=login_data)
            token = login_response.json()["access_token"]
            
            # Logout
            headers = {"Authorization": f"Bearer {token}"}
            response = client.post("/logout", headers=headers)
            
            assert response.status_code == 200
            assert response.json()["message"] == "Successfully logged out"

    def test_logout_no_token(self, client: TestClient):
        """Test logout sin token"""
        response = client.post("/logout")
        
        assert response.status_code == 401


class TestSecurityFeatures:
    """Tests para características de seguridad"""

    def test_password_hashing(self, db_session: Session):
        """Test que las contraseñas se hashean correctamente"""
        # El mock ya está configurado para devolver la contraseña tal como es
        # En producción, esto debería ser diferente
        with patch('app.utils.security.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password123"
            
            user_data = UserCreate(
                username="security_test",
                password="plain_password",
                role=UserRole.admin
            )
            
            user = create_user(db_session, user_data)
            
            # Verificar que se llamó la función de hash
            mock_hash.assert_called_once_with("plain_password")
            # Verificar que la contraseña no se almacena en texto plano
            assert user.password_hash != "plain_password"

    def test_token_contains_user_info(self, client: TestClient, admin_user):
        """Test que el token contiene información del usuario"""
        with patch('app.utils.security.verify_password', return_value=True):
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            token = response.json()["access_token"]
            
            # Verificar token
            payload = verify_token(token)
            assert payload["sub"] == "admin_test"
            assert payload["role"] == "admin"
            assert "exp" in payload  # Expiration time
            assert "iat" in payload  # Issued at time