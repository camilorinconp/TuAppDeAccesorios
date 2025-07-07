import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker # Import Session
from app.main import app
from app.database import Base, get_db_session_maker
from app.dependencies import get_db
from app.crud import create_user
from app.schemas import UserCreate
from app.models import UserRole
from unittest.mock import patch

from .test_utils import (
    APITestHelper, DatabaseTestHelper, TestDataBuilder,
    retry_on_failure, expect_http_error, parametrize_with_error_cases,
    auth_test, db_test
)
from .conftest import (
    assert_successful_response, assert_error_response, 
    ValidationError, DatabaseError
)

# Configuración de la base de datos de prueba
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


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
def client_fixture(db_session: Session): # Corrected type hint here
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_create_product(client: TestClient, db_session: Session): # Corrected type hint here
    with patch('app.utils.security.verify_password', return_value=True):
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
            # Create admin user for testing
            admin_user_data = UserCreate(username="admin", password="admin123", role=UserRole.admin)
            create_user(db_session, admin_user_data)

            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            assert response.status_code == 200
            token = response.json()["access_token"]

            product_data = {
                "sku": "SKU001",
                "name": "Audífonos Bluetooth",
                "description": "Audífonos inalámbricos de alta calidad",
                "image_url": "http://example.com/image.jpg",
                "cost_price": 15.00,
                "selling_price": 25.00,
                "stock_quantity": 100
            }
            response = client.post(
                "/products/",
                json=product_data,
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Audífonos Bluetooth"
            assert response.json()["sku"] == "SKU001"

def test_read_products(client: TestClient, db_session: Session): # Corrected type hint here
    with patch('app.utils.security.verify_password', return_value=True):
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
            # Create admin user for testing
            admin_user_data = UserCreate(username="admin_read", password="admin123", role=UserRole.admin)
            create_user(db_session, admin_user_data)

            login_data = {
                "username": "admin_read",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            assert response.status_code == 200
            token = response.json()["access_token"]

            # Create a product to ensure there's something to read
            product_data = {
                "sku": "SKU002",
                "name": "Cargador Rápido",
                "description": "Cargador USB-C de 20W",
                "image_url": "http://example.com/charger.jpg",
                "cost_price": 5.00,
                "selling_price": 10.00,
                "stock_quantity": 50
            }
            client.post(
                "/products/",
                json=product_data,
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )

            response = client.get("/products/")
            assert response.status_code == 200
            assert len(response.json()) > 0
            assert any(p["name"] == "Cargador Rápido" for p in response.json())

def test_update_product(client: TestClient, db_session: Session): # Corrected type hint here
    with patch('app.utils.security.verify_password', return_value=True):
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
            # Create admin user for testing
            admin_user_data = UserCreate(username="admin_update", password="admin123", role=UserRole.admin)
            create_user(db_session, admin_user_data)

            login_data = {
                "username": "admin_update",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            assert response.status_code == 200
            token = response.json()["access_token"]

            # Create a product to update
            product_data = {
                "sku": "SKU003",
                "name": "Funda Protectora",
                "description": "Funda de silicona para iPhone",
                "image_url": "http://example.com/case.jpg",
                "cost_price": 3.00,
                "selling_price": 8.00,
                "stock_quantity": 200
            }
            create_response = client.post(
                "/products/",
                json=product_data,
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            product_id = create_response.json()["id"]

            update_data = {
                "selling_price": 9.50,
                "stock_quantity": 150
            }
            response = client.put(
                f"/products/{product_id}",
                json=update_data,
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            assert response.status_code == 200
            assert response.json()["selling_price"] == 9.50
            assert response.json()["stock_quantity"] == 150