# ==================================================================
# ENUMS - DEFINICIONES DE TIPOS ENUMERADOS
# ==================================================================

import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    sales_staff = "sales_staff"

class LoanStatus(str, enum.Enum):
    en_prestamo = "en_prestamo"
    devuelto = "devuelto"