# ==================================================================
# MODELS PACKAGE - IMPORTACIONES DE MODELOS
# ==================================================================

"""
Paquete de modelos para TuAppDeAccesorios
Incluye modelos de base de datos y auditoría
"""

from .audit import AuditLog, SecurityAlert, LoginAttempt, AuditActionType, AuditSeverity
from .enums import UserRole, LoanStatus
from .main import (
    Product,
    Distributor,
    User,
    PointOfSaleTransaction,
    PointOfSaleItem,
    ConsignmentLoan,
    ConsignmentReport
)

__all__ = [
    # Auditoría
    'AuditLog',
    'SecurityAlert', 
    'LoginAttempt',
    'AuditActionType',
    'AuditSeverity',
    
    # Enums
    'UserRole',
    'LoanStatus',
    
    # Modelos principales
    'Product',
    'Distributor', 
    'User',
    'PointOfSaleTransaction',
    'PointOfSaleItem',
    'ConsignmentLoan',
    'ConsignmentReport'
]