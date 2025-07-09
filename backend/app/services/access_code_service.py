# ==================================================================
# SERVICIO DE CÓDIGOS DE ACCESO - GENERACIÓN AUTOMÁTICA
# ==================================================================

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import re

from ..models.main import Distributor
from ..logging_config import get_secure_logger
from ..exceptions import BusinessLogicError

logger = get_secure_logger(__name__)


class AccessCodeService:
    """Servicio para generar códigos de acceso únicos para distribuidores"""
    
    PREFIX = "BGA"
    MIN_NUMBER = 1
    MAX_NUMBER = 1000
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_next_access_code(self) -> str:
        """
        Genera el siguiente código de acceso disponible en formato BGAxxxx
        donde xxxx es un número consecutivo de 0001 a 1000
        """
        try:
            # Crear tabla auxiliar para tracking si no existe
            from sqlalchemy import text
            
            # Crear tabla para tracking de códigos si no existe
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS access_code_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT UNIQUE NOT NULL,
                    distributor_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (distributor_id) REFERENCES distributors (id)
                )
            """))
            
            # Obtener códigos ya utilizados
            result = self.db.execute(text("""
                SELECT access_code FROM access_code_tracking 
                WHERE access_code LIKE 'BGA%' 
                ORDER BY access_code
            """)).fetchall()
            
            existing_numbers = []
            for row in result:
                code = row[0]
                if code and len(code) == 7 and code.startswith(self.PREFIX):
                    try:
                        number = int(code[3:])  # Extraer los 4 dígitos después de BGA
                        existing_numbers.append(number)
                    except ValueError:
                        continue
            
            # Encontrar el primer número disponible
            existing_numbers.sort()
            next_number = self.MIN_NUMBER
            
            for num in existing_numbers:
                if num == next_number:
                    next_number += 1
                elif num > next_number:
                    break
            
            # Verificar que no exceda el máximo
            if next_number > self.MAX_NUMBER:
                raise BusinessLogicError(
                    f"Se ha alcanzado el límite máximo de distribuidores ({self.MAX_NUMBER}). "
                    "No se pueden generar más códigos de acceso."
                )
            
            # Generar código con formato BGA + 4 dígitos con ceros a la izquierda
            access_code = f"{self.PREFIX}{next_number:04d}"
            
            logger.info(f"Generado nuevo código de acceso: {access_code}")
            return access_code
            
        except Exception as e:
            logger.error(f"Error generando código de acceso: {str(e)}")
            raise
    
    def is_valid_access_code_format(self, access_code: str) -> bool:
        """
        Valida que el código de acceso tenga el formato correcto BGAxxxx
        """
        if not access_code:
            return False
        
        # Verificar formato con regex
        pattern = r'^BGA\d{4}$'
        if not re.match(pattern, access_code):
            return False
        
        # Verificar rango de números
        try:
            number = int(access_code[3:])
            return self.MIN_NUMBER <= number <= self.MAX_NUMBER
        except ValueError:
            return False
    
    def is_access_code_available(self, access_code: str) -> bool:
        """
        Verifica si un código de acceso está disponible
        """
        if not self.is_valid_access_code_format(access_code):
            return False
        
        # Verificar en la tabla de tracking
        from sqlalchemy import text
        
        # Crear tabla si no existe
        self.db.execute(text("""
            CREATE TABLE IF NOT EXISTS access_code_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_code TEXT UNIQUE NOT NULL,
                distributor_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (distributor_id) REFERENCES distributors (id)
            )
        """))
        
        result = self.db.execute(text("""
            SELECT id FROM access_code_tracking 
            WHERE access_code = :access_code
        """), {'access_code': access_code}).fetchone()
        
        return result is None
    
    def get_next_available_codes(self, limit: int = 10) -> List[str]:
        """
        Obtiene una lista de los próximos códigos disponibles
        """
        try:
            codes = []
            current_code = self.generate_next_access_code()
            
            # Generar códigos consecutivos disponibles
            number = int(current_code[3:])
            
            for i in range(limit):
                if number + i > self.MAX_NUMBER:
                    break
                    
                test_code = f"{self.PREFIX}{number + i:04d}"
                if self.is_access_code_available(test_code):
                    codes.append(test_code)
                    
                if len(codes) >= limit:
                    break
            
            return codes
            
        except Exception as e:
            logger.error(f"Error obteniendo códigos disponibles: {str(e)}")
            return []
    
    def get_usage_statistics(self) -> dict:
        """
        Obtiene estadísticas de uso de códigos de acceso
        """
        try:
            from sqlalchemy import text
            
            # Crear tabla si no existe
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS access_code_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT UNIQUE NOT NULL,
                    distributor_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (distributor_id) REFERENCES distributors (id)
                )
            """))
            
            # Contar códigos usados
            result = self.db.execute(text("""
                SELECT COUNT(*) FROM access_code_tracking 
                WHERE access_code LIKE 'BGA%'
            """)).fetchone()
            total_used = result[0] if result else 0
            
            # Obtener el código más alto usado
            result = self.db.execute(text("""
                SELECT access_code FROM access_code_tracking 
                WHERE access_code LIKE 'BGA%' 
                ORDER BY access_code DESC 
                LIMIT 1
            """)).fetchone()
            
            highest_number = 0
            if result and result[0]:
                try:
                    highest_number = int(result[0][3:])
                except ValueError:
                    pass
            
            # Calcular disponibles
            total_available = self.MAX_NUMBER - total_used
            
            return {
                "total_capacity": self.MAX_NUMBER,
                "total_used": total_used,
                "total_available": total_available,
                "usage_percentage": (total_used / self.MAX_NUMBER) * 100,
                "highest_number_used": highest_number,
                "next_available": self.generate_next_access_code(),
                "prefix": self.PREFIX
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {
                "total_capacity": self.MAX_NUMBER,
                "total_used": 0,
                "total_available": self.MAX_NUMBER,
                "usage_percentage": 0,
                "highest_number_used": 0,
                "next_available": f"{self.PREFIX}0001",
                "prefix": self.PREFIX,
                "error": str(e)
            }
    
    def register_access_code(self, access_code: str, distributor_id: int) -> bool:
        """
        Registra un código de acceso en la tabla de tracking
        """
        try:
            from sqlalchemy import text
            
            # Insertar en la tabla de tracking
            self.db.execute(text("""
                INSERT INTO access_code_tracking (access_code, distributor_id)
                VALUES (:access_code, :distributor_id)
            """), {
                'access_code': access_code,
                'distributor_id': distributor_id
            })
            
            self.db.commit()
            logger.info(f"Código de acceso registrado: {access_code} para distribuidor {distributor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registrando código de acceso: {str(e)}")
            self.db.rollback()
            return False
    
    def reserve_access_code(self, distributor_name: str, contact_person: str = None, phone_number: str = None) -> str:
        """
        Reserva el siguiente código de acceso disponible para un distribuidor
        """
        try:
            access_code = self.generate_next_access_code()
            
            # Verificar disponibilidad una vez más (por concurrencia)
            if not self.is_access_code_available(access_code):
                # Intentar generar un nuevo código si este fue tomado
                access_code = self.generate_next_access_code()
            
            logger.info(f"Código de acceso reservado: {access_code} para {distributor_name}")
            return access_code
            
        except Exception as e:
            logger.error(f"Error reservando código de acceso: {str(e)}")
            raise