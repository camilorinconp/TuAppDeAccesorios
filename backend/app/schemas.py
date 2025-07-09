from pydantic import BaseModel, validator, Field
from datetime import datetime, date
from typing import List, Optional, Any
from decimal import Decimal

from .models import UserRole, LoanStatus
from .models.enums import ProductCategory, LocationType
from .security.input_validation import InputValidator
from .utils.security import get_password_hash
from fastapi import HTTPException # Import HTTPException for internal use

# Helper function for common input validation
def _validate_and_sanitize_input(v: Any, field_type: str, max_length: int) -> Any:
    if v is None:
        return v
    if not isinstance(v, str):
        return v # Let Pydantic handle type errors for non-strings

    try:
        return InputValidator.validate_and_sanitize(v, field_type, max_length)
    except HTTPException as e:
        # Re-raise as ValueError for Pydantic to catch
        raise ValueError(e.detail)

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
    selling_price: float = Field(..., ge=0, description="Precio de venta al detal (debe ser >= 0)")
    wholesale_price: Optional[float] = Field(None, ge=0, description="Precio de venta mayorista (debe ser >= 0)")
    stock_quantity: int = Field(..., ge=0, description="Cantidad en stock (debe ser >= 0)")
    
    # Código de barras
    barcode: Optional[str] = Field(None, max_length=50, description="Código de barras del producto")
    internal_code: Optional[str] = Field(None, max_length=20, description="Código interno del producto")
    
    # Campos de categorización (opcionales para compatibilidad)
    category: Optional[ProductCategory] = Field(None, description="Categoría del producto")
    subcategory: Optional[str] = Field(None, max_length=100, description="Subcategoría específica")
    brand: Optional[str] = Field(None, max_length=100, description="Marca del producto")
    tags: Optional[str] = Field(None, max_length=500, description="Tags separados por comas")
    
    @validator('sku')
    def validate_sku_with_input_validator(cls, v):
        # La validación de longitud y formato se delega a InputValidator
        # La conversión a mayúsculas y el strip se mantienen aquí para consistencia
        v = v.strip().upper()
        return _validate_and_sanitize_input(v, 'sku', 50)
    
    @validator('name')
    def validate_name_with_input_validator(cls, v):
        return _validate_and_sanitize_input(v, 'name', 200)
    
    @validator('description')
    def validate_description_with_input_validator(cls, v):
        return _validate_and_sanitize_input(v, 'description', 1000)
    
    @validator('selling_price')
    def validate_selling_price(cls, v, values):
        if 'cost_price' in values and v < values['cost_price']:
            raise ValueError('El precio de venta no puede ser menor al precio de costo')
        return v
    
    @validator('wholesale_price')
    def validate_wholesale_price(cls, v, values):
        if v is not None:
            if 'cost_price' in values and v < values['cost_price']:
                raise ValueError('El precio mayorista no puede ser menor al precio de costo')
            if 'selling_price' in values and v > values['selling_price']:
                raise ValueError('El precio mayorista debe ser menor o igual al precio de venta al detal')
        return v
    
    @validator('image_url')
    def validate_image_url_with_input_validator(cls, v):
        if v:
            # Validar formato de URL y sanitizar
            v = _validate_and_sanitize_input(v, 'url', 500) # Asumiendo que 'url' es un field_type válido en InputValidator
            if not v.startswith(('http://', 'https://')):
                raise ValueError('La URL de la imagen debe comenzar con http:// o https://')
        return v
    
    @validator('subcategory')
    def validate_subcategory(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'name', 100)
        return v
    
    @validator('brand') 
    def validate_brand(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'name', 100)
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is not None:
            # Validar y limpiar tags (separados por comas)
            tags = [tag.strip() for tag in v.split(',') if tag.strip()]
            if len(tags) > 10:  # Límite de 10 tags
                raise ValueError('Máximo 10 tags permitidos')
            return ', '.join(tags)
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
    wholesale_price: Optional[float] = Field(None, ge=0, description="Precio de venta mayorista")
    stock_quantity: Optional[int] = Field(None, ge=0)
    
    # Código de barras
    barcode: Optional[str] = Field(None, max_length=50, description="Código de barras del producto")
    internal_code: Optional[str] = Field(None, max_length=20, description="Código interno del producto")
    
    # Campos de categorización
    category: Optional[ProductCategory] = Field(None, description="Categoría del producto")
    subcategory: Optional[str] = Field(None, max_length=100, description="Subcategoría específica")
    brand: Optional[str] = Field(None, max_length=100, description="Marca del producto")
    tags: Optional[str] = Field(None, max_length=500, description="Tags separados por comas")
    
    @validator('sku')
    def validate_sku_update_with_input_validator(cls, v):
        if v is not None:
            v = v.strip().upper()
            return _validate_and_sanitize_input(v, 'sku', 50)
        return v
    
    @validator('name')
    def validate_name_update_with_input_validator(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'name', 200)
        return v
    
    @validator('description')
    def validate_description_update_with_input_validator(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'description', 1000)
        return v
    
    @validator('image_url')
    def validate_image_url_update_with_input_validator(cls, v):
        if v:
            v = _validate_and_sanitize_input(v, 'url', 500) # Asumiendo que 'url' es un field_type válido
            if not v.startswith(('http://', 'https://')):
                raise ValueError('La URL de la imagen debe comenzar con http:// o https://')
        return v
    
    @validator('subcategory')
    def validate_subcategory_update(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'name', 100)
        return v
    
    @validator('brand') 
    def validate_brand_update(cls, v):
        if v is not None:
            return _validate_and_sanitize_input(v, 'name', 100)
        return v
    
    @validator('tags')
    def validate_tags_update(cls, v):
        if v is not None:
            # Validar y limpiar tags (separados por comas)
            tags = [tag.strip() for tag in v.split(',') if tag.strip()]
            if len(tags) > 10:  # Límite de 10 tags
                raise ValueError('Máximo 10 tags permitidos')
            return ', '.join(tags)
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

# Esquemas para filtros y categorización
class ProductFilters(BaseModel):
    """Esquema para filtros avanzados de productos"""
    search: Optional[str] = Field(None, max_length=200, description="Búsqueda por nombre, SKU o descripción")
    category: Optional[ProductCategory] = Field(None, description="Filtrar por categoría")
    brand: Optional[str] = Field(None, max_length=100, description="Filtrar por marca")
    min_price: Optional[float] = Field(None, ge=0, description="Precio mínimo")
    max_price: Optional[float] = Field(None, ge=0, description="Precio máximo")
    in_stock: Optional[bool] = Field(None, description="Solo productos con stock")
    tags: Optional[str] = Field(None, max_length=200, description="Filtrar por tags")

class CategoryInfo(BaseModel):
    """Información de una categoría"""
    category: ProductCategory
    name: str
    count: int
    description: str

class BrandInfo(BaseModel):
    """Información de una marca"""
    brand: str
    count: int
    categories: List[str]

class ProductFiltersResponse(BaseModel):
    """Respuesta con filtros disponibles"""
    categories: List[CategoryInfo]
    brands: List[BrandInfo]
    price_range: dict
    total_products: int

# Esquemas para Distributor
class DistributorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del distribuidor")
    contact_person: Optional[str] = Field(None, max_length=100, description="Persona de contacto")
    phone_number: Optional[str] = Field(None, max_length=20, description="Número de teléfono")
    access_code: str = Field(..., min_length=4, max_length=200, description="Código de acceso")
    
    @validator('name')
    def validate_name_with_input_validator(cls, v):
        return _validate_and_sanitize_input(v, 'name', 200)
    
    @validator('phone_number')
    def validate_phone_number_with_input_validator(cls, v):
        if v:
            # Asumiendo que 'phone' es un field_type válido en InputValidator
            return _validate_and_sanitize_input(v, 'phone', 20)
        return v
    
    @validator('access_code')
    def validate_access_code_with_input_validator(cls, v):
        # Asumiendo que 'access_code' es un field_type válido en InputValidator
        return _validate_and_sanitize_input(v, 'access_code', 200)

class DistributorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del distribuidor")
    contact_person: Optional[str] = Field(None, max_length=100, description="Persona de contacto")
    phone_number: Optional[str] = Field(None, max_length=20, description="Número de teléfono")
    access_code: Optional[str] = Field(None, min_length=7, max_length=7, description="Código de acceso (opcional, se genera automáticamente)")
    
    @validator('name')
    def validate_name_with_input_validator(cls, v):
        return _validate_and_sanitize_input(v, 'name', 200)
    
    @validator('phone_number')
    def validate_phone_number_with_input_validator(cls, v):
        if v:
            return _validate_and_sanitize_input(v, 'phone', 20)
        return v
    
    @validator('access_code')
    def validate_access_code_with_input_validator(cls, v):
        if v:
            # Validar formato BGAxxxx si se proporciona
            import re
            if not re.match(r'^BGA\d{4}$', v):
                raise ValueError('El código de acceso debe tener el formato BGA + 4 dígitos (ej: BGA0001)')
            return _validate_and_sanitize_input(v, 'access_code', 7)
        return v

class DistributorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Nombre del distribuidor")
    contact_person: Optional[str] = Field(None, max_length=100, description="Persona de contacto")
    phone_number: Optional[str] = Field(None, max_length=20, description="Número de teléfono")
    access_code: Optional[str] = Field(None, min_length=7, max_length=7, description="Código de acceso")
    
    @validator('name')
    def validate_name_with_input_validator(cls, v):
        if v:
            return _validate_and_sanitize_input(v, 'name', 200)
        return v
    
    @validator('phone_number')
    def validate_phone_number_with_input_validator(cls, v):
        if v:
            return _validate_and_sanitize_input(v, 'phone', 20)
        return v
    
    @validator('access_code')
    def validate_access_code_with_input_validator(cls, v):
        if v:
            # Validar formato BGAxxxx si se proporciona
            import re
            if not re.match(r'^BGA\d{4}$', v):
                raise ValueError('El código de acceso debe tener el formato BGA + 4 dígitos (ej: BGA0001)')
            return _validate_and_sanitize_input(v, 'access_code', 7)
        return v

class Distributor(DistributorBase):
    id: int

    class Config:
        from_attributes = True

# Esquemas para User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario")
    email: str = Field(..., description="Correo electrónico del usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    
    @validator('username')
    def validate_username_with_input_validator(cls, v):
        v = v.strip().lower()
        return _validate_and_sanitize_input(v, 'username', 50)
    
    @validator('email')
    def validate_email_with_input_validator(cls, v):
        return _validate_and_sanitize_input(v, 'email', 255) # Asumiendo max_length para email

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

class ConsignmentLoanCreate(BaseModel):
    distributor_id: int
    product_id: int
    quantity_loaned: int
    loan_date: date
    return_due_date: date
    status: Optional[LoanStatus] = LoanStatus.en_prestamo

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

# Esquemas para Scanner y Movimientos de Inventario
class ScanSessionCreate(BaseModel):
    session_type: str = Field(..., description="Tipo de sesión: inventory, consignment, sales, incoming")
    location_type: Optional[LocationType] = Field(None, description="Tipo de ubicación")
    location_id: Optional[int] = Field(None, description="ID de ubicación específica")
    reference_type: Optional[str] = Field(None, description="Tipo de referencia")
    reference_id: Optional[int] = Field(None, description="ID de referencia")
    device_info: Optional[str] = Field(None, max_length=200, description="Información del dispositivo")
    notes: Optional[str] = Field(None, max_length=500, description="Notas de la sesión")

class ScanSession(BaseModel):
    id: int
    session_type: str
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    total_scans: int
    successful_scans: int
    failed_scans: int
    location_type: Optional[LocationType]
    location_id: Optional[int]
    reference_type: Optional[str]
    reference_id: Optional[int]
    device_info: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True

class InventoryMovementCreate(BaseModel):
    barcode_scanned: str = Field(..., description="Código de barras escaneado")
    movement_type: str = Field(..., description="Tipo de movimiento: in, out, transfer")
    from_location_type: Optional[LocationType] = Field(None, description="Tipo de ubicación origen")
    from_location_id: Optional[int] = Field(None, description="ID de ubicación origen")
    to_location_type: LocationType = Field(..., description="Tipo de ubicación destino")
    to_location_id: Optional[int] = Field(None, description="ID de ubicación destino")
    quantity: int = Field(1, gt=0, description="Cantidad a mover")
    reference_type: Optional[str] = Field(None, description="Tipo de referencia")
    reference_id: Optional[int] = Field(None, description="ID de referencia")
    notes: Optional[str] = Field(None, max_length=500, description="Notas del movimiento")
    device_info: Optional[str] = Field(None, max_length=200, description="Información del dispositivo")

class InventoryMovement(BaseModel):
    id: int
    product_id: int
    barcode_scanned: str
    movement_type: str
    from_location_type: Optional[LocationType]
    from_location_id: Optional[int]
    to_location_type: LocationType
    to_location_id: Optional[int]
    quantity: int
    user_id: int
    timestamp: datetime
    reference_type: Optional[str]
    reference_id: Optional[int]
    notes: Optional[str]
    device_info: Optional[str]

    class Config:
        from_attributes = True

# Esquemas para operaciones de scanner
class ScanRequest(BaseModel):
    barcode: str = Field(..., description="Código de barras escaneado")
    session_id: Optional[int] = Field(None, description="ID de sesión de escaneo")
    quantity: int = Field(1, gt=0, description="Cantidad por defecto")
    device_info: Optional[str] = Field(None, max_length=200, description="Información del dispositivo")

class ScanResponse(BaseModel):
    success: bool
    message: str
    product: Optional[Product] = None
    movement: Optional[InventoryMovement] = None
    session: Optional[ScanSession] = None

class BulkScanRequest(BaseModel):
    barcodes: List[str] = Field(..., description="Lista de códigos de barras")
    session_id: Optional[int] = Field(None, description="ID de sesión de escaneo")
    movement_type: str = Field(..., description="Tipo de movimiento")
    location_type: LocationType = Field(..., description="Tipo de ubicación")
    location_id: Optional[int] = Field(None, description="ID de ubicación")
    device_info: Optional[str] = Field(None, max_length=200, description="Información del dispositivo")

class BulkScanResponse(BaseModel):
    total_scanned: int
    successful_scans: int
    failed_scans: int
    results: List[ScanResponse]
    session: Optional[ScanSession] = None