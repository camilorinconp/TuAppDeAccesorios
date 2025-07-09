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
    incoming = "incoming"                     # Ingreso de mercancía (recepción)
    transit = "transit"                       # En tránsito (entre ubicaciones)

class ProductCategory(str, enum.Enum):
    fundas = "fundas"                         # Fundas y carcasas
    cargadores = "cargadores"                 # Cargadores y cables de poder
    cables = "cables"                         # Cables USB, datos, etc.
    audifonos = "audifonos"                   # Audífonos y accesorios de audio
    vidrios = "vidrios_templados"             # Vidrios templados y protectores
    soportes = "soportes"                     # Soportes y bases
    baterias = "baterias_externas"            # Baterías portátiles y power banks
    memorias = "memorias"                     # Tarjetas de memoria y USB
    limpieza = "limpieza"                     # Kits de limpieza y mantenimiento
    vehiculos = "vehiculos"                   # Accesorios para vehículos
    otros = "otros"                           # Otros accesorios