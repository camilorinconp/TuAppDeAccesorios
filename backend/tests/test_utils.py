"""
Utilidades específicas para tests
Contiene helpers y decoradores para mejorar el manejo de errores
"""
import functools
import time
import pytest
from typing import Callable, Any, Dict, List, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import AuthenticationError, ValidationError, DatabaseError


def retry_on_failure(max_retries: int = 3, delay: float = 0.1):
    """
    Decorador para reintentar tests que fallen por razones transitorias
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, DatabaseError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    raise
                except Exception:
                    # No reintentar otros tipos de errores
                    raise
            
            # Si llegamos aquí, todos los intentos fallaron
            raise last_exception
        
        return wrapper
    return decorator


def expect_http_error(status_code: int, message: Optional[str] = None):
    """
    Decorador para tests que esperan un error HTTP específico
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                # Si llegamos aquí, no se lanzó la excepción esperada
                pytest.fail(f"Expected HTTP {status_code} error, but test completed successfully")
            except AssertionError as e:
                # Verificar si es el error HTTP esperado
                if f"Expected status {status_code}" in str(e):
                    if message and message not in str(e):
                        pytest.fail(f"Expected error message '{message}' not found in: {str(e)}")
                    return  # Test pasó correctamente
                raise  # Re-lanzar si es otro tipo de AssertionError
            except Exception as e:
                pytest.fail(f"Unexpected exception type {type(e).__name__}: {str(e)}")
        
        return wrapper
    return decorator


class TestDataBuilder:
    """
    Builder para crear datos de test consistentes
    """
    
    @staticmethod
    def create_product_data(
        sku: str = "TEST001",
        name: str = "Test Product",
        description: str = "Test Description",
        cost_price: float = 10.0,
        selling_price: float = 20.0,
        stock_quantity: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Crear datos de producto para tests"""
        base_data = {
            "sku": sku,
            "name": name,
            "description": description,
            "image_url": "http://example.com/image.jpg",
            "cost_price": cost_price,
            "selling_price": selling_price,
            "stock_quantity": stock_quantity
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def create_user_data(
        username: str = "testuser",
        password: str = "testpass123",
        role: str = "admin",
        **kwargs
    ) -> Dict[str, Any]:
        """Crear datos de usuario para tests"""
        base_data = {
            "username": username,
            "password": password,
            "role": role
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def create_distributor_data(
        name: str = "Test Distributor",
        contact_person: str = "John Doe",
        phone: str = "1234567890",
        email: str = "test@distributor.com",
        access_code: str = "TEST123",
        **kwargs
    ) -> Dict[str, Any]:
        """Crear datos de distribuidor para tests"""
        base_data = {
            "name": name,
            "contact_person": contact_person,
            "phone": phone,
            "email": email,
            "access_code": access_code
        }
        base_data.update(kwargs)
        return base_data


class APITestHelper:
    """
    Helper para tests de API con métodos de conveniencia
    """
    
    def __init__(self, client: TestClient):
        self.client = client
        self._auth_headers = None
    
    def authenticate(self, username: str = "admin_test", password: str = "admin123") -> Dict[str, str]:
        """Autenticar y obtener headers"""
        try:
            login_data = {"username": username, "password": password}
            response = self.client.post("/token", data=login_data)
            
            if response.status_code != 200:
                raise AuthenticationError(f"Authentication failed: {response.text}")
            
            token = response.json()["access_token"]
            self._auth_headers = {"Authorization": f"Bearer {token}"}
            return self._auth_headers
        except Exception as e:
            raise AuthenticationError(f"Failed to authenticate: {e}") from e
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Obtener headers de autenticación"""
        if not self._auth_headers:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")
        return self._auth_headers
    
    def post_json(self, url: str, data: Dict[str, Any], authenticated: bool = True) -> Any:
        """POST con datos JSON y manejo de errores"""
        headers = self.get_auth_headers() if authenticated else {}
        response = self.client.post(url, json=data, headers=headers)
        self._check_response_format(response)
        return response
    
    def get(self, url: str, authenticated: bool = True, params: Dict[str, Any] = None) -> Any:
        """GET con manejo de errores"""
        headers = self.get_auth_headers() if authenticated else {}
        response = self.client.get(url, headers=headers, params=params)
        self._check_response_format(response)
        return response
    
    def put_json(self, url: str, data: Dict[str, Any], authenticated: bool = True) -> Any:
        """PUT con datos JSON y manejo de errores"""
        headers = self.get_auth_headers() if authenticated else {}
        response = self.client.put(url, json=data, headers=headers)
        self._check_response_format(response)
        return response
    
    def delete(self, url: str, authenticated: bool = True) -> Any:
        """DELETE con manejo de errores"""
        headers = self.get_auth_headers() if authenticated else {}
        response = self.client.delete(url, headers=headers)
        self._check_response_format(response)
        return response
    
    def _check_response_format(self, response) -> None:
        """Verificar que la respuesta tenga formato válido"""
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                response.json()
            except ValueError as e:
                raise ValidationError(f"Invalid JSON response: {e}. Response text: {response.text}") from e


class DatabaseTestHelper:
    """
    Helper para operaciones de base de datos en tests
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_test_user(self, username: str = "testuser", role: str = "admin") -> Any:
        """Crear usuario de test"""
        try:
            from app.schemas import UserCreate
            from app.crud import create_user
            from app.models import UserRole
            from unittest.mock import patch
            
            with patch('app.utils.security.get_password_hash', side_effect=lambda x: f"hashed_{x}"):
                user_data = UserCreate(
                    username=username,
                    password="testpass123",
                    role=UserRole(role)
                )
                user = create_user(self.db, user_data)
                self.db.commit()
                return user
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create test user: {e}") from e
    
    def create_test_product(self, sku: str = "TEST001", **kwargs) -> Any:
        """Crear producto de test"""
        try:
            from app.schemas import ProductCreate
            from app.crud import create_product
            
            product_data = TestDataBuilder.create_product_data(sku=sku, **kwargs)
            product_create = ProductCreate(**product_data)
            product = create_product(self.db, product_create)
            self.db.commit()
            return product
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create test product: {e}") from e
    
    def cleanup_test_data(self, model_classes: List[Any]) -> None:
        """Limpiar datos de test"""
        try:
            for model_class in model_classes:
                self.db.query(model_class).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to cleanup test data: {e}") from e


def parametrize_with_error_cases(*test_cases):
    """
    Decorador para parametrizar tests con casos de error esperados
    """
    def decorator(func: Callable) -> Callable:
        return pytest.mark.parametrize(
            "test_data,expected_status,expected_message",
            test_cases
        )(func)
    return decorator


# Fixtures específicas para diferentes tipos de tests
@pytest.fixture
def api_helper(client: TestClient) -> APITestHelper:
    """Fixture para helper de API"""
    return APITestHelper(client)


@pytest.fixture
def db_helper(db_session: Session) -> DatabaseTestHelper:
    """Fixture para helper de base de datos"""
    return DatabaseTestHelper(db_session)


# Marcadores para diferentes tipos de tests
auth_test = pytest.mark.auth
db_test = pytest.mark.db
integration_test = pytest.mark.integration
slow_test = pytest.mark.slow