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
from .enums import UserRole, LoanStatus, LocationType
from datetime import datetime


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)  # Índice para búsquedas por SKU
    name = Column(String, index=True, nullable=False)  # Ya tenía índice
    description = Column(String, index=True)  # Índice para búsquedas en descripción
    image_url = Column(String)
    cost_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False, index=True)  # Índice para ordenamiento por precio
    stock_quantity = Column(Integer, nullable=False, default=0, index=True)  # Índice para filtros de stock

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