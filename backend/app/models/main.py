# ==================================================================
# MODELOS PRINCIPALES - DEFINICIONES DE TABLAS
# ==================================================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Enum,
    DateTime,
    Date,
    Numeric,
    Index,
    Boolean
)
from sqlalchemy.orm import relationship
from ..database import Base
from .enums import UserRole, LoanStatus, LocationType, ProductCategory
from datetime import datetime


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)  # Índice para búsquedas por SKU
    name = Column(String, index=True, nullable=False)  # Ya tenía índice
    description = Column(String, index=True)  # Índice para búsquedas en descripción
    image_url = Column(String)
    cost_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False, index=True)  # Precio venta detal
    wholesale_price = Column(Numeric(10, 2), nullable=True, index=True)  # Precio venta mayorista
    stock_quantity = Column(Integer, nullable=False, default=0, index=True)  # Índice para filtros de stock
    
    # Código de barras
    barcode = Column(String, unique=True, nullable=True, index=True)  # Código de barras único
    internal_code = Column(String, nullable=True, index=True)  # Código interno (como el "21" de la etiqueta)
    
    # Campos de categorización
    category = Column(Enum(ProductCategory), nullable=False, default=ProductCategory.otros, index=True)  # Categoría principal
    subcategory = Column(String, index=True, nullable=True)  # Subcategoría específica
    brand = Column(String, index=True, nullable=True)  # Marca del producto
    tags = Column(String, nullable=True)  # Tags separados por comas para búsquedas adicionales
    
    # Metadatos adicionales
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    locations = relationship("ProductLocation", back_populates="product")


class ProductLocation(Base):
    """Modelo para rastrear ubicaciones de productos en el sistema"""
    __tablename__ = "product_locations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    location_type = Column(Enum(LocationType), nullable=False, index=True)  # warehouse, consignment, sold, returned
    location_id = Column(Integer, nullable=True, index=True)  # distributor_id para consignment, null para warehouse
    quantity = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Campos adicionales para trazabilidad
    reference_type = Column(String, nullable=True)  # 'loan', 'sale', 'return'
    reference_id = Column(Integer, nullable=True)  # ID del préstamo/venta relacionado
    notes = Column(String, nullable=True)  # Notas adicionales

    # Relaciones
    product = relationship("Product", back_populates="locations")


class Distributor(Base):
    __tablename__ = "distributors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # Índice para búsquedas por nombre
    contact_person = Column(String)
    phone_number = Column(String, index=True)  # Índice para búsquedas por teléfono
    access_code = Column(String, unique=True, nullable=False, index=True)  # Índice para autenticación


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)  # Índice para autenticación
    email = Column(String, unique=True, nullable=False, index=True)  # Índice para búsquedas por email
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Índice para ordenamiento por fecha


class PointOfSaleTransaction(Base):
    __tablename__ = "point_of_sale_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_time = Column(DateTime, nullable=False, index=True)  # Índice para filtros de fecha
    total_amount = Column(Numeric(10, 2), nullable=False, index=True)  # Índice para reportes de ventas
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Índice para filtros por usuario

    user = relationship("User")
    items = relationship("PointOfSaleItem", back_populates="transaction")


class PointOfSaleItem(Base):
    __tablename__ = "point_of_sale_items"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("point_of_sale_transactions.id"), nullable=False, index=True)  # Índice para JOIN
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)  # Índice para JOIN y búsquedas
    quantity_sold = Column(Integer, nullable=False, index=True)  # Índice para cálculos de ventas
    price_at_time_of_sale = Column(Numeric(10, 2), nullable=False)

    transaction = relationship("PointOfSaleTransaction", back_populates="items")
    product = relationship("Product")


class ConsignmentLoan(Base):
    __tablename__ = "consignment_loans"

    id = Column(Integer, primary_key=True, index=True)
    distributor_id = Column(Integer, ForeignKey("distributors.id"), nullable=False, index=True)  # Índice para JOIN
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)  # Índice para JOIN
    quantity_loaned = Column(Integer, nullable=False, index=True)  # Índice para cálculos de inventario
    loan_date = Column(Date, nullable=False, index=True)  # Índice para filtros de fecha
    return_due_date = Column(Date, nullable=False, index=True)  # Índice para detectar vencimientos
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.pendiente, index=True)  # Índice para filtros de estado
    
    # Campos adicionales para mejor tracking
    actual_return_date = Column(Date, nullable=True)  # Fecha real de devolución
    max_loan_days = Column(Integer, nullable=True, default=30)  # Días máximo de préstamo
    notes = Column(String, nullable=True)  # Notas del préstamo
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Campos para seguimiento de progreso
    quantity_reported = Column(Integer, nullable=False, default=0)  # Cantidad total reportada
    quantity_pending = Column(Integer, nullable=False, default=0)  # Cantidad pendiente por reportar

    distributor = relationship("Distributor")
    product = relationship("Product")
    reports = relationship("ConsignmentReport", back_populates="loan")


class ConsignmentReport(Base):
    __tablename__ = "consignment_reports"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("consignment_loans.id"), nullable=False, index=True)  # Índice para JOIN
    report_date = Column(Date, nullable=False, index=True)  # Índice para filtros de fecha
    quantity_sold = Column(Integer, nullable=False, default=0)
    quantity_returned = Column(Integer, nullable=False, default=0)
    
    # Campos adicionales para mejor tracking financiero
    selling_price_at_report = Column(Numeric(10, 2), nullable=True)  # Precio de venta reportado
    profit_margin = Column(Numeric(10, 2), nullable=True)  # Margen de ganancia
    distributor_commission = Column(Numeric(10, 2), nullable=True)  # Comisión del distribuidor
    
    # Tracking de reportes
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(String, nullable=True)  # Notas del reporte
    is_final_report = Column(Boolean, default=False)  # Si es el reporte final

    loan = relationship("ConsignmentLoan", back_populates="reports")


class InventoryMovement(Base):
    """Modelo para registrar todos los movimientos de inventario con pistola lectora"""
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    barcode_scanned = Column(String, nullable=False, index=True)  # Código escaneado
    movement_type = Column(String, nullable=False, index=True)  # 'in', 'out', 'transfer'
    
    # Ubicaciones
    from_location_type = Column(Enum(LocationType), nullable=True, index=True)
    from_location_id = Column(Integer, nullable=True, index=True)
    to_location_type = Column(Enum(LocationType), nullable=False, index=True)
    to_location_id = Column(Integer, nullable=True, index=True)
    
    # Cantidades
    quantity = Column(Integer, nullable=False, default=1)
    
    # Metadatos
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Referencias a transacciones
    reference_type = Column(String, nullable=True)  # 'sale', 'loan', 'return', 'incoming'
    reference_id = Column(Integer, nullable=True)
    
    # Información adicional
    notes = Column(String, nullable=True)
    device_info = Column(String, nullable=True)  # Info de la pistola/dispositivo
    
    # Relaciones
    product = relationship("Product")
    user = relationship("User")


class ScanSession(Base):
    """Modelo para sesiones de escaneo con pistola lectora"""
    __tablename__ = "scan_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_type = Column(String, nullable=False, index=True)  # 'inventory', 'consignment', 'sales', 'incoming'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Información de la sesión
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True, index=True)
    status = Column(String, default="active", index=True)  # 'active', 'completed', 'cancelled'
    
    # Contadores
    total_scans = Column(Integer, default=0)
    successful_scans = Column(Integer, default=0)
    failed_scans = Column(Integer, default=0)
    
    # Metadatos
    location_type = Column(Enum(LocationType), nullable=True)
    location_id = Column(Integer, nullable=True)
    reference_type = Column(String, nullable=True)
    reference_id = Column(Integer, nullable=True)
    
    # Información del dispositivo
    device_info = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    # Relaciones
    user = relationship("User")


# Índices compuestos para optimización de consultas específicas

# Índice compuesto para búsquedas de transacciones por usuario y fecha
Index('idx_transaction_user_date', PointOfSaleTransaction.user_id, PointOfSaleTransaction.transaction_time)

# Índice compuesto para búsquedas de items por transacción y producto
Index('idx_item_transaction_product', PointOfSaleItem.transaction_id, PointOfSaleItem.product_id)

# Índice compuesto para búsquedas de préstamos por estado y fecha de vencimiento
Index('idx_loan_due_date_status', ConsignmentLoan.return_due_date, ConsignmentLoan.status)

# Índice compuesto para reportes por préstamo y fecha
Index('idx_report_loan_date', ConsignmentReport.loan_id, ConsignmentReport.report_date)

# Índices compuestos para ProductLocation (nuevo modelo)
Index('idx_product_location_type', ProductLocation.product_id, ProductLocation.location_type)
Index('idx_location_type_id', ProductLocation.location_type, ProductLocation.location_id)
Index('idx_product_location_reference', ProductLocation.product_id, ProductLocation.reference_type, ProductLocation.reference_id)

# Índices compuestos para categorización de productos
Index('idx_product_category_brand', Product.category, Product.brand)
Index('idx_product_category_stock', Product.category, Product.stock_quantity)
Index('idx_product_category_price', Product.category, Product.selling_price)
Index('idx_product_brand_name', Product.brand, Product.name)

# Índices compuestos para movimientos de inventario
Index('idx_inventory_movement_product_timestamp', InventoryMovement.product_id, InventoryMovement.timestamp)
Index('idx_inventory_movement_barcode_timestamp', InventoryMovement.barcode_scanned, InventoryMovement.timestamp)
Index('idx_inventory_movement_type_timestamp', InventoryMovement.movement_type, InventoryMovement.timestamp)
Index('idx_inventory_movement_location', InventoryMovement.to_location_type, InventoryMovement.to_location_id)

# Índices compuestos para sesiones de escaneo
Index('idx_scan_session_user_started', ScanSession.user_id, ScanSession.started_at)
Index('idx_scan_session_type_status', ScanSession.session_type, ScanSession.status)