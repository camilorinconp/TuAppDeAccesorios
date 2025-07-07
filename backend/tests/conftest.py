"""
Configuración común para tests
Contiene fixtures y utilidades compartidas entre todos los tests
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.dependencies import get_db
from app.models import UserRole
from app.schemas import UserCreate
from app.crud import create_user
from unittest.mock import patch


# Configuraciones de test
TEST_DATABASE_URL = "sqlite:///./test_database.db"


class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos en tests"""
    pass


class AuthenticationError(Exception):
    """Excepción personalizada para errores de autenticación en tests"""
    pass


class ValidationError(Exception):
    """Excepción personalizada para errores de validación en tests"""
    pass


@pytest.fixture(scope="session")
def temp_db():
    """Crear base de datos temporal para la sesión de tests"""
    db_fd, db_path = tempfile.mkstemp()
    yield f"sqlite:///{db_path}"
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_engine(temp_db):
    """Crear engine de base de datos para cada test"""
    engine = create_engine(
        temp_db,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        Base.metadata.create_all(bind=engine)
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Crear sesión de base de datos para cada test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise DatabaseError(f"Database error in test: {e}") from e
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """Crear cliente de test con override de base de datos"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # La sesión se cierra en el fixture db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session):
    """Crear usuario admin para tests"""
    try:
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: f"hashed_{x}"):
            admin_user_data = UserCreate(
                username="admin_test",
                password="admin123",
                role=UserRole.admin
            )
            user = create_user(db_session, admin_user_data)
            db_session.commit()
            return user
    except Exception as e:
        db_session.rollback()
        raise AuthenticationError(f"Failed to create admin user: {e}") from e


@pytest.fixture
def distributor_user(db_session: Session):
    """Crear usuario distribuidor para tests"""
    try:
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: f"hashed_{x}"):
            distributor_user_data = UserCreate(
                username="distributor_test",
                password="dist123",
                role=UserRole.distributor
            )
            user = create_user(db_session, distributor_user_data)
            db_session.commit()
            return user
    except Exception as e:
        db_session.rollback()
        raise AuthenticationError(f"Failed to create distributor user: {e}") from e


@pytest.fixture
def authenticated_headers(client: TestClient, admin_user):
    """Obtener headers de autenticación para tests"""
    try:
        with patch('app.utils.security.verify_password', return_value=True):
            login_data = {
                "username": "admin_test",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            
            if response.status_code != 200:
                raise AuthenticationError(f"Login failed: {response.text}")
            
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        raise AuthenticationError(f"Failed to get authentication headers: {e}") from e


# Funciones de utilidad para assertions
def assert_successful_response(response, expected_status: int = 200):
    """Verificar que la respuesta sea exitosa"""
    if response.status_code != expected_status:
        try:
            error_detail = response.json().get('detail', 'No detail provided')
        except:
            error_detail = response.text
        raise AssertionError(
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Error: {error_detail}"
        )


def assert_error_response(response, expected_status: int, expected_message: str = None):
    """Verificar que la respuesta sea un error con el formato esperado"""
    if response.status_code != expected_status:
        raise AssertionError(
            f"Expected error status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )
    
    try:
        response_data = response.json()
        if "detail" not in response_data:
            raise AssertionError(f"Error response should contain 'detail' field: {response_data}")
        
        if expected_message and expected_message not in response_data["detail"]:
            raise AssertionError(
                f"Expected '{expected_message}' in error message, "
                f"got: {response_data['detail']}"
            )
    except ValueError as e:
        raise ValidationError(f"Response is not valid JSON: {e}. Response text: {response.text}") from e


def assert_valid_token_response(response_data: dict, token_type: str = "bearer"):
    """Verificar que la respuesta contenga tokens válidos"""
    required_fields = ["access_token", "refresh_token", "token_type"]
    
    for field in required_fields:
        if field not in response_data:
            raise ValidationError(f"{field} not found in response: {response_data}")
    
    if response_data["token_type"] != token_type:
        raise ValidationError(
            f"Expected token_type '{token_type}', got {response_data.get('token_type')}"
        )
    
    # Verificar formato JWT
    access_token = response_data["access_token"]
    if not isinstance(access_token, str):
        raise ValidationError(f"access_token should be string, got {type(access_token)}")
    
    token_parts = access_token.split('.')
    if len(token_parts) != 3:
        raise ValidationError(
            f"access_token should be JWT format (3 parts), got {len(token_parts)} parts: {access_token[:50]}..."
        )


def assert_valid_user_data(user_data: dict, expected_username: str, expected_role: str):
    """Verificar que los datos de usuario sean válidos"""
    required_fields = ["username", "role"]
    
    for field in required_fields:
        if field not in user_data:
            raise ValidationError(f"{field} not found in user data: {user_data}")
    
    if user_data["username"] != expected_username:
        raise ValidationError(
            f"Expected username '{expected_username}', got '{user_data['username']}'"
        )
    
    if user_data["role"] != expected_role:
        raise ValidationError(
            f"Expected role '{expected_role}', got '{user_data['role']}'"
        )


# Marcadores personalizados para pytest
def pytest_configure(config):
    """Configuración personalizada de pytest"""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "db: mark test as database related"
    )


# Hook para manejo de fallos
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook para agregar información adicional en caso de fallo"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Agregar información adicional para debugging
        if hasattr(item, 'funcargs'):
            # Información sobre fixtures usados
            fixtures_info = []
            for fixture_name, fixture_value in item.funcargs.items():
                if hasattr(fixture_value, '__dict__'):
                    fixtures_info.append(f"{fixture_name}: {type(fixture_value).__name__}")
                else:
                    fixtures_info.append(f"{fixture_name}: {type(fixture_value)}")
            
            additional_info = f"\nFixtures used: {', '.join(fixtures_info)}"
            report.longrepr.reprtraceback.reprentries[-1].lines.append(additional_info)