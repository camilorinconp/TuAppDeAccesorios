from pydantic import BaseModel, validator, Field
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal

from .models import UserRole, LoanStatus

# Esquemas de respuesta genérica
class GenericResponse(BaseModel):
    message: str
    success: bool = True

# Esquemas para Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# Esquemas para Product
class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50, description="Código único del producto")
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del producto")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción del producto")
    image_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen")
    cost_price: float = Field(..., ge=0, description="Precio de costo (debe ser >= 0)")
    selling_price: float = Field(..., ge=0, description="Precio de venta (debe ser >= 0)")
    stock_quantity: int = Field(..., ge=0, description="Cantidad en stock (debe ser >= 0)")
    
    @validator('sku')
    def validate_sku(cls, v):
        if not v or not v.strip():
            raise ValueError('❌ El SKU es obligatorio y no puede estar vacío')
        # Remover espacios extra y convertir a mayúsculas
        v = v.strip().upper()
        # Validar formato (solo alfanumérico y guiones)
        if not all(c.isalnum() or c in '-_' for c in v):
            raise ValueError('❌ Formato de SKU inválido: Solo se permiten letras, números, guiones (-) y guiones bajos (_)')
        if len(v) < 3:
            raise ValueError('❌ El SKU debe tener al menos 3 caracteres')
        if len(v) > 20:
            raise ValueError('❌ El SKU no puede tener más de 20 caracteres')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()
    
    @validator('selling_price')
    def validate_selling_price(cls, v, values):
        if 'cost_price' in values and v < values['cost_price']:
            raise ValueError('El precio de venta no puede ser menor al precio de costo')
        return v
    
    @validator('image_url')
    def validate_image_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('La URL de la imagen debe comenzar con http:// o https://')
        return v


class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    cost_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    
    @validator('sku')
    def validate_sku(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('❌ El SKU no puede estar vacío')
            v = v.strip().upper()
            if not all(c.isalnum() or c in '-_' for c in v):
                raise ValueError('❌ Formato de SKU inválido: Solo se permiten letras, números, guiones (-) y guiones bajos (_)')
            if len(v) < 3:
                raise ValueError('❌ El SKU debe tener al menos 3 caracteres')
            if len(v) > 20:
                raise ValueError('❌ El SKU no puede tener más de 20 caracteres')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else v
    
    @validator('image_url')
    def validate_image_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('La URL de la imagen debe comenzar con http:// o https://')
        return v


class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

# Esquema para lista paginada de productos
class ProductList(BaseModel):
    products: List[Product]
    total: int
    skip: int
    limit: int
    has_next: bool


# Esquemas para Distributor
class DistributorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del distribuidor")
    contact_person: Optional[str] = Field(None, max_length=100, description="Persona de contacto")
    phone_number: Optional[str] = Field(None, max_length=20, description="Número de teléfono")
    access_code: str = Field(..., min_length=4, max_length=20, description="Código de acceso")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del distribuidor no puede estar vacío')
        return v.strip()
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('El número de teléfono debe contener solo números y caracteres permitidos (+, -, espacios, paréntesis)')
        return v
    
    @validator('access_code')
    def validate_access_code(cls, v):
        if not v or not v.strip():
            raise ValueError('El código de acceso no puede estar vacío')
        return v.strip()


class DistributorCreate(DistributorBase):
    pass


class Distributor(DistributorBase):
    id: int

    class Config:
        from_attributes = True


# Esquemas para User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre de usuario no puede estar vacío')
        v = v.strip().lower()
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('El nombre de usuario solo puede contener letras, números, guiones y guiones bajos')
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not any(c.isalpha() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra')
        return v


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


# Esquemas para PointOfSaleItem
class PointOfSaleItemBase(BaseModel):
    product_id: int = Field(..., gt=0, description="ID del producto")
    quantity_sold: int = Field(..., gt=0, description="Cantidad vendida (debe ser > 0)")
    price_at_time_of_sale: float = Field(..., ge=0, description="Precio al momento de la venta")


class PointOfSaleItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID del producto")
    quantity_sold: int = Field(..., gt=0, description="Cantidad vendida (debe ser > 0)")
    price_at_time_of_sale: Optional[float] = Field(None, ge=0, description="Precio al momento de la venta (se calcula automáticamente si no se proporciona)")


class PointOfSaleItem(PointOfSaleItemBase):
    id: int
    transaction_id: int

    class Config:
        from_attributes = True


# Esquemas para PointOfSaleTransaction
class PointOfSaleTransactionBase(BaseModel):
    user_id: int = Field(..., gt=0, description="ID del usuario")
    total_amount: float = Field(..., ge=0, description="Monto total de la transacción")


class PointOfSaleTransactionCreate(BaseModel):
    items: List[PointOfSaleItemCreate] = Field(..., min_items=1, description="Lista de productos vendidos")
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('La venta debe tener al menos un producto')
        
        # Verificar que no haya productos duplicados
        product_ids = [item.product_id for item in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError('No se pueden vender productos duplicados en la misma transacción')
        
        return v


class PointOfSaleTransaction(PointOfSaleTransactionBase):
    id: int
    transaction_time: datetime
    items: List[PointOfSaleItem] = []

    class Config:
        from_attributes = True


# Esquemas para ConsignmentLoan
class ConsignmentLoanBase(BaseModel):
    distributor_id: int
    product_id: int
    quantity_loaned: int
    loan_date: date
    return_due_date: date
    status: LoanStatus


class ConsignmentLoanCreate(ConsignmentLoanBase):
    pass


class ConsignmentLoan(ConsignmentLoanBase):
    id: int

    class Config:
        from_attributes = True


# Esquemas para ConsignmentReport
class ConsignmentReportBase(BaseModel):
    loan_id: int
    quantity_sold: int
    quantity_returned: int
    report_date: date


class ConsignmentReportCreate(ConsignmentReportBase):
    pass


class ConsignmentReport(ConsignmentReportBase):
    id: int

    class Config:
        from_attributes = True