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
)
from sqlalchemy.orm import relationship
from ..database import Base
from .enums import UserRole, LoanStatus


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
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, index=True)  # Índice para ordenamiento por fecha


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
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.en_prestamo, index=True)  # Índice para filtros de estado

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