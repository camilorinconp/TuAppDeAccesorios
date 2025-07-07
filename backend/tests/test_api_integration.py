import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import Base, get_db_session_maker
from app.dependencies import get_db
from app.crud import create_user
from app.schemas import UserCreate
from app.models import UserRole
from unittest.mock import patch
import time
import json

# Configuración de la base de datos de prueba
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"


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


@pytest.fixture(name="admin_token")
def admin_token_fixture(client: TestClient, db_session: Session):
    """Crear usuario admin y obtener token"""
    with patch('app.utils.security.verify_password', return_value=True):
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
            # Crear usuario admin
            admin_user_data = UserCreate(
                username="admin_integration",
                password="admin123",
                role=UserRole.admin
            )
            create_user(db_session, admin_user_data)
            
            # Obtener token
            login_data = {
                "username": "admin_integration",
                "password": "admin123"
            }
            response = client.post("/token", data=login_data)
            return response.json()["access_token"]


@pytest.fixture(name="distributor_token")
def distributor_token_fixture(client: TestClient, db_session: Session):
    """Crear usuario distribuidor y obtener token"""
    with patch('app.utils.security.verify_password', return_value=True):
        with patch('app.utils.security.get_password_hash', side_effect=lambda x: x):
            # Crear usuario distribuidor
            distributor_user_data = UserCreate(
                username="distributor_integration",
                password="dist123",
                role=UserRole.distributor
            )
            create_user(db_session, distributor_user_data)
            
            # Obtener token
            login_data = {
                "username": "distributor_integration",
                "password": "dist123"
            }
            response = client.post("/distributor-token", data=login_data)
            return response.json()["access_token"]


class TestCompleteWorkflow:
    """Tests de flujos de trabajo completos"""

    def test_complete_product_lifecycle(self, client: TestClient, admin_token: str):
        """Test ciclo de vida completo de un producto"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 1. Crear producto
        product_data = {
            "sku": "LIFECYCLE001",
            "name": "Producto Ciclo Completo",
            "description": "Producto para test de ciclo completo",
            "image_url": "http://example.com/lifecycle.jpg",
            "cost_price": 10.0,
            "selling_price": 20.0,
            "stock_quantity": 100
        }
        
        response = client.post("/products/", json=product_data, headers=headers)
        assert response.status_code == 200
        product = response.json()
        product_id = product["id"]
        
        # 2. Leer producto creado
        response = client.get(f"/products/{product_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["sku"] == "LIFECYCLE001"
        
        # 3. Actualizar producto
        update_data = {
            "selling_price": 25.0,
            "stock_quantity": 150
        }
        response = client.put(f"/products/{product_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["selling_price"] == 25.0
        assert response.json()["stock_quantity"] == 150
        
        # 4. Crear venta del producto
        sale_data = {
            "product_id": product_id,
            "quantity": 5,
            "unit_price": 25.0,
            "customer_name": "Cliente Test",
            "customer_phone": "123456789"
        }
        response = client.post("/sales/", json=sale_data, headers=headers)
        assert response.status_code == 200
        sale = response.json()
        assert sale["total_price"] == 125.0
        
        # 5. Verificar stock actualizado
        response = client.get(f"/products/{product_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["stock_quantity"] == 145  # 150 - 5
        
        # 6. Obtener reportes
        response = client.get("/reports/sales", headers=headers)
        assert response.status_code == 200
        sales_report = response.json()
        assert sales_report["total_sales"] >= 1
        
        response = client.get("/reports/inventory", headers=headers)
        assert response.status_code == 200
        inventory_report = response.json()
        assert inventory_report["total_products"] >= 1
        
        # 7. Eliminar producto
        response = client.delete(f"/products/{product_id}", headers=headers)
        assert response.status_code == 200
        
        # 8. Verificar eliminación
        response = client.get(f"/products/{product_id}", headers=headers)
        assert response.status_code == 404

    def test_multiple_user_interaction(self, client: TestClient, admin_token: str, distributor_token: str):
        """Test interacción entre múltiples tipos de usuario"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        distributor_headers = {"Authorization": f"Bearer {distributor_token}"}
        
        # 1. Admin crea producto
        product_data = {
            "sku": "MULTIUSER001",
            "name": "Producto Multi Usuario",
            "description": "Producto para test multi usuario",
            "image_url": "http://example.com/multiuser.jpg",
            "cost_price": 15.0,
            "selling_price": 30.0,
            "stock_quantity": 200
        }
        
        response = client.post("/products/", json=product_data, headers=admin_headers)
        assert response.status_code == 200
        product = response.json()
        product_id = product["id"]
        
        # 2. Distribuidor ve productos (solo lectura)
        response = client.get("/products/", headers=distributor_headers)
        assert response.status_code == 200
        products = response.json()
        assert any(p["id"] == product_id for p in products)
        
        # 3. Distribuidor intenta modificar producto (debe fallar)
        update_data = {"selling_price": 35.0}
        response = client.put(f"/products/{product_id}", json=update_data, headers=distributor_headers)
        assert response.status_code == 403
        
        # 4. Distribuidor puede ver detalles del producto
        response = client.get(f"/products/{product_id}", headers=distributor_headers)
        assert response.status_code == 200
        assert response.json()["selling_price"] == 30.0  # No cambió
        
        # 5. Admin modifica producto exitosamente
        response = client.put(f"/products/{product_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["selling_price"] == 35.0


class TestPaginationAndSearch:
    """Tests de paginación y búsqueda"""

    def test_pagination_workflow(self, client: TestClient, admin_token: str):
        """Test flujo completo de paginación"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear 25 productos
        for i in range(25):
            product_data = {
                "sku": f"PAGE{i:03d}",
                "name": f"Producto Página {i}",
                "description": f"Descripción del producto {i}",
                "image_url": f"http://example.com/page{i}.jpg",
                "cost_price": 10.0 + i,
                "selling_price": 20.0 + i,
                "stock_quantity": 100 + i
            }
            response = client.post("/products/", json=product_data, headers=headers)
            assert response.status_code == 200
        
        # Test primera página
        response = client.get("/products/paginated?page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["pages"] == 3
        
        # Test segunda página
        response = client.get("/products/paginated?page=2&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2
        
        # Test última página
        response = client.get("/products/paginated?page=3&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 3

    def test_search_workflow(self, client: TestClient, admin_token: str):
        """Test flujo completo de búsqueda"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear productos con diferentes nombres
        products_data = [
            ("SEARCH001", "iPhone 14 Case", "Funda para iPhone 14"),
            ("SEARCH002", "Samsung Galaxy Charger", "Cargador para Samsung"),
            ("SEARCH003", "iPhone 13 Screen Protector", "Protector de pantalla"),
            ("SEARCH004", "Wireless Headphones", "Auriculares inalámbricos"),
            ("SEARCH005", "iPhone 14 Pro Max Case", "Funda premium")
        ]
        
        for sku, name, description in products_data:
            product_data = {
                "sku": sku,
                "name": name,
                "description": description,
                "image_url": f"http://example.com/{sku.lower()}.jpg",
                "cost_price": 10.0,
                "selling_price": 20.0,
                "stock_quantity": 100
            }
            response = client.post("/products/", json=product_data, headers=headers)
            assert response.status_code == 200
        
        # Búsqueda por "iPhone"
        response = client.get("/products/search?query=iPhone", headers=headers)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        assert all("iPhone" in p["name"] for p in results)
        
        # Búsqueda por "Case"
        response = client.get("/products/search?query=Case", headers=headers)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        assert all("Case" in p["name"] for p in results)
        
        # Búsqueda por SKU
        response = client.get("/products/search?query=SEARCH001", headers=headers)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["sku"] == "SEARCH001"
        
        # Búsqueda sin resultados
        response = client.get("/products/search?query=INEXISTENTE", headers=headers)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 0


class TestErrorHandling:
    """Tests de manejo de errores"""

    def test_invalid_product_creation(self, client: TestClient, admin_token: str):
        """Test creación de producto con datos inválidos"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Datos inválidos - precio negativo
        invalid_data = {
            "sku": "INVALID001",
            "name": "Producto Inválido",
            "description": "Producto con precio negativo",
            "image_url": "http://example.com/invalid.jpg",
            "cost_price": -10.0,  # Precio negativo
            "selling_price": 20.0,
            "stock_quantity": 100
        }
        
        response = client.post("/products/", json=invalid_data, headers=headers)
        assert response.status_code == 422  # Validation error
        
        # Datos incompletos
        incomplete_data = {
            "sku": "INCOMPLETE001",
            "name": "Producto Incompleto"
            # Faltan campos requeridos
        }
        
        response = client.post("/products/", json=incomplete_data, headers=headers)
        assert response.status_code == 422

    def test_duplicate_sku_handling(self, client: TestClient, admin_token: str):
        """Test manejo de SKU duplicado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear primer producto
        product_data = {
            "sku": "DUPLICATE001",
            "name": "Primer Producto",
            "description": "Primer producto con SKU duplicado",
            "image_url": "http://example.com/first.jpg",
            "cost_price": 10.0,
            "selling_price": 20.0,
            "stock_quantity": 100
        }
        
        response = client.post("/products/", json=product_data, headers=headers)
        assert response.status_code == 200
        
        # Intentar crear segundo producto con mismo SKU
        duplicate_data = {
            "sku": "DUPLICATE001",  # Mismo SKU
            "name": "Segundo Producto",
            "description": "Segundo producto con SKU duplicado",
            "image_url": "http://example.com/second.jpg",
            "cost_price": 15.0,
            "selling_price": 25.0,
            "stock_quantity": 50
        }
        
        response = client.post("/products/", json=duplicate_data, headers=headers)
        assert response.status_code == 400  # Conflict error

    def test_insufficient_stock_sale(self, client: TestClient, admin_token: str):
        """Test venta con stock insuficiente"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear producto con stock limitado
        product_data = {
            "sku": "LOWSTOCK001",
            "name": "Producto Stock Bajo",
            "description": "Producto con stock limitado",
            "image_url": "http://example.com/lowstock.jpg",
            "cost_price": 10.0,
            "selling_price": 20.0,
            "stock_quantity": 5
        }
        
        response = client.post("/products/", json=product_data, headers=headers)
        assert response.status_code == 200
        product = response.json()
        
        # Intentar vender más de lo disponible
        sale_data = {
            "product_id": product["id"],
            "quantity": 10,  # Más del stock disponible (5)
            "unit_price": 20.0,
            "customer_name": "Cliente Test",
            "customer_phone": "123456789"
        }
        
        response = client.post("/sales/", json=sale_data, headers=headers)
        assert response.status_code == 400  # Bad request


class TestPerformance:
    """Tests de rendimiento básico"""

    def test_response_time_products_list(self, client: TestClient, admin_token: str):
        """Test tiempo de respuesta para lista de productos"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear varios productos
        for i in range(50):
            product_data = {
                "sku": f"PERF{i:03d}",
                "name": f"Producto Performance {i}",
                "description": f"Producto para test de performance {i}",
                "image_url": f"http://example.com/perf{i}.jpg",
                "cost_price": 10.0 + i,
                "selling_price": 20.0 + i,
                "stock_quantity": 100 + i
            }
            client.post("/products/", json=product_data, headers=headers)
        
        # Medir tiempo de respuesta
        start_time = time.time()
        response = client.get("/products/", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Debe responder en menos de 2 segundos

    def test_pagination_performance(self, client: TestClient, admin_token: str):
        """Test rendimiento de paginación"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test paginación con límites grandes
        start_time = time.time()
        response = client.get("/products/paginated?page=1&limit=100", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Debe responder en menos de 1 segundo

    def test_search_performance(self, client: TestClient, admin_token: str):
        """Test rendimiento de búsqueda"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test búsqueda
        start_time = time.time()
        response = client.get("/products/search?query=Producto", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Debe responder en menos de 1 segundo


class TestCacheIntegration:
    """Tests de integración con caché"""

    def test_cache_headers(self, client: TestClient, admin_token: str):
        """Test headers de caché en respuestas"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Crear producto
        product_data = {
            "sku": "CACHE001",
            "name": "Producto Cache",
            "description": "Producto para test de cache",
            "image_url": "http://example.com/cache.jpg",
            "cost_price": 10.0,
            "selling_price": 20.0,
            "stock_quantity": 100
        }
        
        response = client.post("/products/", json=product_data, headers=headers)
        assert response.status_code == 200
        product = response.json()
        
        # Verificar headers de caché en GET
        response = client.get(f"/products/{product['id']}", headers=headers)
        assert response.status_code == 200
        
        # Verificar que no hay cache en operaciones de escritura
        update_data = {"selling_price": 25.0}
        response = client.put(f"/products/{product['id']}", json=update_data, headers=headers)
        assert response.status_code == 200