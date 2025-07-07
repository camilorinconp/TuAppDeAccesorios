"""
Configuración compartida para pytest
"""
import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importaciones
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configurar variables de entorno para tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-very-secure"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # DB diferente para tests
os.environ["REDIS_CACHE_ENABLED"] = "false"  # Desactivar cache en tests

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.models import User, Product, Sale
from app.crud import create_user
from app.schemas import UserCreate
from app.models import UserRole
from unittest.mock import patch

# Engine de base de datos para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Engine de base de datos para la sesión de tests"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Sesión de base de datos para cada test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de test de FastAPI"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Usuario administrador para tests"""
    with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
        user_data = UserCreate(
            username="test_admin",
            password="admin123",
            role=UserRole.admin
        )
        return create_user(db_session, user_data)


@pytest.fixture(scope="function")
def distributor_user(db_session):
    """Usuario distribuidor para tests"""
    with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
        user_data = UserCreate(
            username="test_distributor",
            password="dist123",
            role=UserRole.distributor
        )
        return create_user(db_session, user_data)


@pytest.fixture(scope="function")
def admin_token(client, admin_user):
    """Token de autenticación para admin"""
    with patch('app.utils.security.verify_password', return_value=True):
        login_data = {
            "username": "test_admin",
            "password": "admin123"
        }
        response = client.post("/token", data=login_data)
        return response.json()["access_token"]


@pytest.fixture(scope="function")
def distributor_token(client, distributor_user):
    """Token de autenticación para distribuidor"""
    with patch('app.utils.security.verify_password', return_value=True):
        login_data = {
            "username": "test_distributor",
            "password": "dist123"
        }
        response = client.post("/distributor-token", data=login_data)
        return response.json()["access_token"]


@pytest.fixture(scope="function")
def sample_product(db_session):
    """Producto de ejemplo para tests"""
    from app.crud import create_product
    from app.schemas import ProductCreate
    
    product_data = ProductCreate(
        sku="TEST001",
        name="Producto de Prueba",
        description="Descripción de prueba",
        image_url="http://example.com/test.jpg",
        cost_price=10.0,
        selling_price=20.0,
        stock_quantity=100
    )
    return create_product(db_session, product_data)


@pytest.fixture(scope="function")
def sample_products(db_session):
    """Lista de productos de ejemplo para tests"""
    from app.crud import create_product
    from app.schemas import ProductCreate
    
    products = []
    for i in range(5):
        product_data = ProductCreate(
            sku=f"TEST{i:03d}",
            name=f"Producto {i}",
            description=f"Descripción del producto {i}",
            image_url=f"http://example.com/test{i}.jpg",
            cost_price=10.0 + i,
            selling_price=20.0 + i,
            stock_quantity=100 + i
        )
        products.append(create_product(db_session, product_data))
    
    return products


@pytest.fixture(scope="function")
def sample_sale(db_session, sample_product):
    """Venta de ejemplo para tests"""
    from app.crud import create_sale
    from app.schemas import SaleCreate
    
    sale_data = SaleCreate(
        product_id=sample_product.id,
        quantity=5,
        unit_price=20.0,
        customer_name="Cliente Test",
        customer_phone="123456789"
    )
    return create_sale(db_session, sale_data)


# Configuración de pytest
def pytest_configure(config):
    """Configuración global de pytest"""
    # Agregar marcadores personalizados
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "slow: marca tests lentos"
    )
    config.addinivalue_line(
        "markers", "auth: marca tests de autenticación"
    )
    config.addinivalue_line(
        "markers", "crud: marca tests de operaciones CRUD"
    )
    config.addinivalue_line(
        "markers", "api: marca tests de API"
    )


def pytest_collection_modifyitems(config, items):
    """Modificar la colección de tests"""
    # Marcar automáticamente tests por su ubicación
    for item in items:
        # Marcar tests de autenticación
        if "auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        
        # Marcar tests CRUD
        if "crud" in item.nodeid:
            item.add_marker(pytest.mark.crud)
        
        # Marcar tests de API
        if "api" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.api)
            item.add_marker(pytest.mark.integration)


# Hooks para manejo de errores
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Configuración automática para cada test"""
    # Limpiar caché si está habilitado
    if os.getenv("REDIS_CACHE_ENABLED") == "true":
        # Código para limpiar Redis cache
        pass
    
    yield
    
    # Cleanup después de cada test
    pass


# Fixtures para mocking
@pytest.fixture
def mock_redis():
    """Mock de Redis para tests"""
    with patch('app.cache.redis_client') as mock_redis:
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        yield mock_redis


@pytest.fixture
def mock_email():
    """Mock de servicio de email para tests"""
    with patch('app.utils.email.send_email') as mock_send:
        mock_send.return_value = True
        yield mock_send


@pytest.fixture
def mock_file_upload():
    """Mock de upload de archivos para tests"""
    with patch('app.utils.files.upload_file') as mock_upload:
        mock_upload.return_value = "http://example.com/uploaded_file.jpg"
        yield mock_upload


# Utilidades para tests
class TestHelpers:
    """Clase con métodos helper para tests"""
    
    @staticmethod
    def create_test_user(db_session, username="testuser", role=UserRole.admin):
        """Crear usuario de prueba"""
        with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            user_data = UserCreate(
                username=username,
                password="testpass123",
                role=role
            )
            return create_user(db_session, user_data)
    
    @staticmethod
    def create_test_product(db_session, sku="TESTSKU", name="Test Product"):
        """Crear producto de prueba"""
        from app.crud import create_product
        from app.schemas import ProductCreate
        
        product_data = ProductCreate(
            sku=sku,
            name=name,
            description="Test description",
            image_url="http://example.com/test.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        return create_product(db_session, product_data)
    
    @staticmethod
    def get_auth_headers(token):
        """Obtener headers de autenticación"""
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_helpers():
    """Fixture para acceder a métodos helper"""
    return TestHelpers()


# Configuración para coverage
pytest_plugins = [
    "pytest_cov",
]