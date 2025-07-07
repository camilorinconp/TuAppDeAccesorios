import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import Base, get_db_session_maker
from app.models import User, Product, Sale, UserRole
from app.crud import (
    create_user, get_user_by_username, get_user_by_id,
    create_product, get_product_by_sku, get_products, update_product, delete_product,
    create_sale, get_sales, get_sales_by_date_range,
    get_products_with_pagination, search_products,
    get_low_stock_products, get_sales_report, get_inventory_report
)
from app.schemas import UserCreate, ProductCreate, ProductUpdate, SaleCreate
from unittest.mock import patch

# Configuración de la base de datos de prueba
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_crud.db"


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


class TestUserCRUD:
    """Tests para operaciones CRUD de usuarios"""

    def test_create_user_success(self, db_session: Session):
        """Test creación exitosa de usuario"""
        with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            user_data = UserCreate(
                username="test_user",
                password="password123",
                role=UserRole.admin
            )
            
            user = create_user(db_session, user_data)
            
            assert user.username == "test_user"
            assert user.password_hash == "hashed_password"
            assert user.role == UserRole.admin
            assert user.id is not None
            assert user.created_at is not None

    def test_create_user_duplicate_username(self, db_session: Session):
        """Test creación de usuario con username duplicado"""
        with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            # Crear primer usuario
            user_data1 = UserCreate(
                username="duplicate_user",
                password="password123",
                role=UserRole.admin
            )
            create_user(db_session, user_data1)
            
            # Intentar crear segundo usuario con mismo username
            user_data2 = UserCreate(
                username="duplicate_user",
                password="password456",
                role=UserRole.distributor
            )
            
            with pytest.raises(Exception):
                create_user(db_session, user_data2)

    def test_get_user_by_username_exists(self, db_session: Session):
        """Test obtener usuario por username existente"""
        with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            # Crear usuario
            user_data = UserCreate(
                username="existing_user",
                password="password123",
                role=UserRole.admin
            )
            created_user = create_user(db_session, user_data)
            
            # Obtener usuario
            found_user = get_user_by_username(db_session, "existing_user")
            
            assert found_user is not None
            assert found_user.id == created_user.id
            assert found_user.username == "existing_user"

    def test_get_user_by_username_not_exists(self, db_session: Session):
        """Test obtener usuario por username inexistente"""
        user = get_user_by_username(db_session, "nonexistent_user")
        assert user is None

    def test_get_user_by_id_exists(self, db_session: Session):
        """Test obtener usuario por ID existente"""
        with patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            # Crear usuario
            user_data = UserCreate(
                username="id_test_user",
                password="password123",
                role=UserRole.admin
            )
            created_user = create_user(db_session, user_data)
            
            # Obtener usuario por ID
            found_user = get_user_by_id(db_session, created_user.id)
            
            assert found_user is not None
            assert found_user.id == created_user.id
            assert found_user.username == "id_test_user"

    def test_get_user_by_id_not_exists(self, db_session: Session):
        """Test obtener usuario por ID inexistente"""
        user = get_user_by_id(db_session, 99999)
        assert user is None


class TestProductCRUD:
    """Tests para operaciones CRUD de productos"""

    def test_create_product_success(self, db_session: Session):
        """Test creación exitosa de producto"""
        product_data = ProductCreate(
            sku="TEST001",
            name="Producto de Prueba",
            description="Descripción del producto de prueba",
            image_url="http://example.com/image.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        
        product = create_product(db_session, product_data)
        
        assert product.sku == "TEST001"
        assert product.name == "Producto de Prueba"
        assert product.cost_price == 10.0
        assert product.selling_price == 20.0
        assert product.stock_quantity == 100
        assert product.id is not None

    def test_create_product_duplicate_sku(self, db_session: Session):
        """Test creación de producto con SKU duplicado"""
        # Crear primer producto
        product_data1 = ProductCreate(
            sku="DUPLICATE001",
            name="Producto 1",
            description="Primer producto",
            image_url="http://example.com/image1.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=50
        )
        create_product(db_session, product_data1)
        
        # Intentar crear segundo producto con mismo SKU
        product_data2 = ProductCreate(
            sku="DUPLICATE001",
            name="Producto 2",
            description="Segundo producto",
            image_url="http://example.com/image2.jpg",
            cost_price=15.0,
            selling_price=25.0,
            stock_quantity=75
        )
        
        with pytest.raises(Exception):
            create_product(db_session, product_data2)

    def test_get_product_by_sku_exists(self, db_session: Session):
        """Test obtener producto por SKU existente"""
        # Crear producto
        product_data = ProductCreate(
            sku="FIND001",
            name="Producto Encontrable",
            description="Producto para encontrar",
            image_url="http://example.com/findable.jpg",
            cost_price=5.0,
            selling_price=15.0,
            stock_quantity=200
        )
        created_product = create_product(db_session, product_data)
        
        # Obtener producto
        found_product = get_product_by_sku(db_session, "FIND001")
        
        assert found_product is not None
        assert found_product.id == created_product.id
        assert found_product.sku == "FIND001"

    def test_get_product_by_sku_not_exists(self, db_session: Session):
        """Test obtener producto por SKU inexistente"""
        product = get_product_by_sku(db_session, "NONEXISTENT001")
        assert product is None

    def test_get_products_empty(self, db_session: Session):
        """Test obtener productos cuando no hay ninguno"""
        products = get_products(db_session)
        assert len(products) == 0

    def test_get_products_with_data(self, db_session: Session):
        """Test obtener productos cuando hay datos"""
        # Crear varios productos
        for i in range(3):
            product_data = ProductCreate(
                sku=f"MULTI{i:03d}",
                name=f"Producto {i}",
                description=f"Descripción del producto {i}",
                image_url=f"http://example.com/image{i}.jpg",
                cost_price=10.0 + i,
                selling_price=20.0 + i,
                stock_quantity=100 + i
            )
            create_product(db_session, product_data)
        
        products = get_products(db_session)
        assert len(products) == 3
        assert all(p.sku.startswith("MULTI") for p in products)

    def test_update_product_success(self, db_session: Session):
        """Test actualización exitosa de producto"""
        # Crear producto
        product_data = ProductCreate(
            sku="UPDATE001",
            name="Producto Original",
            description="Descripción original",
            image_url="http://example.com/original.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        created_product = create_product(db_session, product_data)
        
        # Actualizar producto
        update_data = ProductUpdate(
            name="Producto Actualizado",
            selling_price=25.0,
            stock_quantity=150
        )
        updated_product = update_product(db_session, created_product.id, update_data)
        
        assert updated_product.name == "Producto Actualizado"
        assert updated_product.selling_price == 25.0
        assert updated_product.stock_quantity == 150
        assert updated_product.sku == "UPDATE001"  # No cambió
        assert updated_product.cost_price == 10.0  # No cambió

    def test_update_product_not_exists(self, db_session: Session):
        """Test actualización de producto inexistente"""
        update_data = ProductUpdate(name="Producto Inexistente")
        
        result = update_product(db_session, 99999, update_data)
        assert result is None

    def test_delete_product_success(self, db_session: Session):
        """Test eliminación exitosa de producto"""
        # Crear producto
        product_data = ProductCreate(
            sku="DELETE001",
            name="Producto a Eliminar",
            description="Este producto será eliminado",
            image_url="http://example.com/delete.jpg",
            cost_price=5.0,
            selling_price=10.0,
            stock_quantity=50
        )
        created_product = create_product(db_session, product_data)
        
        # Eliminar producto
        result = delete_product(db_session, created_product.id)
        assert result is True
        
        # Verificar que fue eliminado
        deleted_product = get_product_by_sku(db_session, "DELETE001")
        assert deleted_product is None

    def test_delete_product_not_exists(self, db_session: Session):
        """Test eliminación de producto inexistente"""
        result = delete_product(db_session, 99999)
        assert result is False


class TestProductSearch:
    """Tests para búsqueda de productos"""

    def test_get_products_with_pagination(self, db_session: Session):
        """Test paginación de productos"""
        # Crear 10 productos
        for i in range(10):
            product_data = ProductCreate(
                sku=f"PAGE{i:03d}",
                name=f"Producto Página {i}",
                description=f"Descripción {i}",
                image_url=f"http://example.com/page{i}.jpg",
                cost_price=10.0,
                selling_price=20.0,
                stock_quantity=100
            )
            create_product(db_session, product_data)
        
        # Test primera página
        result = get_products_with_pagination(db_session, skip=0, limit=5)
        assert len(result.items) == 5
        assert result.total == 10
        assert result.page == 1
        assert result.pages == 2
        
        # Test segunda página
        result = get_products_with_pagination(db_session, skip=5, limit=5)
        assert len(result.items) == 5
        assert result.total == 10
        assert result.page == 2
        assert result.pages == 2

    def test_search_products_by_name(self, db_session: Session):
        """Test búsqueda de productos por nombre"""
        # Crear productos con diferentes nombres
        products_data = [
            ("SEARCH001", "Auriculares Bluetooth", "Auriculares inalámbricos"),
            ("SEARCH002", "Cargador USB", "Cargador rápido"),
            ("SEARCH003", "Funda iPhone", "Funda protectora"),
            ("SEARCH004", "Auriculares Cable", "Auriculares con cable")
        ]
        
        for sku, name, description in products_data:
            product_data = ProductCreate(
                sku=sku,
                name=name,
                description=description,
                image_url=f"http://example.com/{sku.lower()}.jpg",
                cost_price=10.0,
                selling_price=20.0,
                stock_quantity=100
            )
            create_product(db_session, product_data)
        
        # Buscar por "Auriculares"
        results = search_products(db_session, "Auriculares")
        assert len(results) == 2
        assert all("Auriculares" in p.name for p in results)

    def test_search_products_by_sku(self, db_session: Session):
        """Test búsqueda de productos por SKU"""
        # Crear productos
        product_data = ProductCreate(
            sku="SEARCH_SKU001",
            name="Producto Búsqueda SKU",
            description="Producto para buscar por SKU",
            image_url="http://example.com/search_sku.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        create_product(db_session, product_data)
        
        # Buscar por parte del SKU
        results = search_products(db_session, "SEARCH_SKU")
        assert len(results) == 1
        assert results[0].sku == "SEARCH_SKU001"

    def test_search_products_no_results(self, db_session: Session):
        """Test búsqueda sin resultados"""
        results = search_products(db_session, "PRODUCTO_INEXISTENTE")
        assert len(results) == 0

    def test_get_low_stock_products(self, db_session: Session):
        """Test obtener productos con stock bajo"""
        # Crear productos con diferentes stocks
        products_data = [
            ("LOW001", 5),   # Stock bajo
            ("LOW002", 25),  # Stock normal
            ("LOW003", 2),   # Stock muy bajo
            ("LOW004", 50)   # Stock alto
        ]
        
        for sku, stock in products_data:
            product_data = ProductCreate(
                sku=sku,
                name=f"Producto {sku}",
                description=f"Producto con stock {stock}",
                image_url=f"http://example.com/{sku.lower()}.jpg",
                cost_price=10.0,
                selling_price=20.0,
                stock_quantity=stock
            )
            create_product(db_session, product_data)
        
        # Obtener productos con stock bajo (threshold=10)
        low_stock_products = get_low_stock_products(db_session, threshold=10)
        assert len(low_stock_products) == 2
        assert all(p.stock_quantity <= 10 for p in low_stock_products)


class TestSaleCRUD:
    """Tests para operaciones CRUD de ventas"""

    def test_create_sale_success(self, db_session: Session):
        """Test creación exitosa de venta"""
        # Crear producto primero
        product_data = ProductCreate(
            sku="SALE001",
            name="Producto para Venta",
            description="Producto que se venderá",
            image_url="http://example.com/sale.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        product = create_product(db_session, product_data)
        
        # Crear venta
        sale_data = SaleCreate(
            product_id=product.id,
            quantity=5,
            unit_price=20.0,
            customer_name="Cliente Test",
            customer_phone="123456789"
        )
        
        sale = create_sale(db_session, sale_data)
        
        assert sale.product_id == product.id
        assert sale.quantity == 5
        assert sale.unit_price == 20.0
        assert sale.total_price == 100.0  # 5 * 20.0
        assert sale.customer_name == "Cliente Test"
        assert sale.customer_phone == "123456789"
        assert sale.id is not None
        assert sale.sale_date is not None

    def test_create_sale_insufficient_stock(self, db_session: Session):
        """Test creación de venta con stock insuficiente"""
        # Crear producto con poco stock
        product_data = ProductCreate(
            sku="LOWSTOCK001",
            name="Producto Stock Bajo",
            description="Producto con stock limitado",
            image_url="http://example.com/lowstock.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=3
        )
        product = create_product(db_session, product_data)
        
        # Intentar vender más de lo que hay en stock
        sale_data = SaleCreate(
            product_id=product.id,
            quantity=5,  # Más de lo disponible
            unit_price=20.0,
            customer_name="Cliente Test",
            customer_phone="123456789"
        )
        
        with pytest.raises(Exception):
            create_sale(db_session, sale_data)

    def test_get_sales_empty(self, db_session: Session):
        """Test obtener ventas cuando no hay ninguna"""
        sales = get_sales(db_session)
        assert len(sales) == 0

    def test_get_sales_with_data(self, db_session: Session):
        """Test obtener ventas cuando hay datos"""
        # Crear producto
        product_data = ProductCreate(
            sku="SALES001",
            name="Producto Ventas",
            description="Producto para múltiples ventas",
            image_url="http://example.com/sales.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        product = create_product(db_session, product_data)
        
        # Crear varias ventas
        for i in range(3):
            sale_data = SaleCreate(
                product_id=product.id,
                quantity=i + 1,
                unit_price=20.0,
                customer_name=f"Cliente {i}",
                customer_phone=f"12345678{i}"
            )
            create_sale(db_session, sale_data)
        
        sales = get_sales(db_session)
        assert len(sales) == 3

    def test_get_sales_by_date_range(self, db_session: Session):
        """Test obtener ventas por rango de fechas"""
        # Crear producto
        product_data = ProductCreate(
            sku="DATERANGE001",
            name="Producto Fecha",
            description="Producto para ventas por fecha",
            image_url="http://example.com/daterange.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        product = create_product(db_session, product_data)
        
        # Crear venta
        sale_data = SaleCreate(
            product_id=product.id,
            quantity=1,
            unit_price=20.0,
            customer_name="Cliente Fecha",
            customer_phone="123456789"
        )
        create_sale(db_session, sale_data)
        
        # Obtener ventas del día actual
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        sales = get_sales_by_date_range(db_session, today, tomorrow)
        assert len(sales) == 1


class TestReports:
    """Tests para reportes"""

    def test_get_sales_report(self, db_session: Session):
        """Test reporte de ventas"""
        # Crear productos
        product1_data = ProductCreate(
            sku="REPORT001",
            name="Producto Reporte 1",
            description="Primer producto para reporte",
            image_url="http://example.com/report1.jpg",
            cost_price=10.0,
            selling_price=20.0,
            stock_quantity=100
        )
        product1 = create_product(db_session, product1_data)
        
        product2_data = ProductCreate(
            sku="REPORT002",
            name="Producto Reporte 2",
            description="Segundo producto para reporte",
            image_url="http://example.com/report2.jpg",
            cost_price=15.0,
            selling_price=25.0,
            stock_quantity=100
        )
        product2 = create_product(db_session, product2_data)
        
        # Crear ventas
        sale1_data = SaleCreate(
            product_id=product1.id,
            quantity=2,
            unit_price=20.0,
            customer_name="Cliente Reporte 1",
            customer_phone="123456789"
        )
        create_sale(db_session, sale1_data)
        
        sale2_data = SaleCreate(
            product_id=product2.id,
            quantity=1,
            unit_price=25.0,
            customer_name="Cliente Reporte 2",
            customer_phone="987654321"
        )
        create_sale(db_session, sale2_data)
        
        # Generar reporte
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        report = get_sales_report(db_session, today, tomorrow)
        
        assert report.total_sales == 2
        assert report.total_revenue == 65.0  # 40.0 + 25.0
        assert report.total_profit == 35.0   # (20-10)*2 + (25-15)*1
        assert len(report.top_products) >= 1

    def test_get_inventory_report(self, db_session: Session):
        """Test reporte de inventario"""
        # Crear productos con diferentes características
        products_data = [
            ("INV001", 50, 10.0, 20.0),   # Stock normal
            ("INV002", 5, 15.0, 25.0),    # Stock bajo
            ("INV003", 100, 5.0, 15.0),   # Stock alto
            ("INV004", 0, 20.0, 30.0)     # Sin stock
        ]
        
        for sku, stock, cost, selling in products_data:
            product_data = ProductCreate(
                sku=sku,
                name=f"Producto {sku}",
                description=f"Producto para inventario {sku}",
                image_url=f"http://example.com/{sku.lower()}.jpg",
                cost_price=cost,
                selling_price=selling,
                stock_quantity=stock
            )
            create_product(db_session, product_data)
        
        # Generar reporte de inventario
        report = get_inventory_report(db_session)
        
        assert report.total_products == 4
        assert report.total_stock_value > 0
        assert report.low_stock_products >= 2  # INV002 y INV004
        assert report.out_of_stock_products == 1  # INV004
        assert len(report.products_by_category) >= 0