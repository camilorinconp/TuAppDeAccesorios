# ==================================================================
# ENUMS - DEFINICIONES DE TIPOS ENUMERADOS
# ==================================================================

import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    sales_staff = "sales_staff"

class LoanStatus(str, enum.Enum):
    pendiente = "pendiente"                    # Creado pero no enviado
    en_prestamo = "en_prestamo"                # Enviado al distribuidor
    parcialmente_devuelto = "parcialmente_devuelto"  # Algunos reportes recibidos
    vencido = "vencido"                        # Pasó fecha límite
    devuelto = "devuelto"                      # Completamente reportado
    cancelado = "cancelado"                    # Cancelado antes de envío

class LocationType(str, enum.Enum):
    warehouse = "warehouse"                    # En bodega principal
    consignment = "consignment"                # En consignación con distribuidor
    sold = "sold"                             # Vendido
    returned = "returned"                     # Devuelto por distribuidor