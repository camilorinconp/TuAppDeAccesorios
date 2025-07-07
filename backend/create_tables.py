#!/usr/bin/env python3
"""
Script para crear todas las tablas desde los modelos
"""
import sys
import os
sys.path.append('/app')

from sqlalchemy import create_engine
from app.database import Base
from app.models import main, audit  # Importar todos los modelos

# Configuración
DATABASE_URL = "postgresql://tuappuser:tuapppassword@db:5432/tuappdb"

def create_tables():
    try:
        # Crear conexión a la base de datos
        engine = create_engine(DATABASE_URL)
        
        print("Creando todas las tablas...")
        
        # Crear todas las tablas desde los modelos
        Base.metadata.create_all(bind=engine)
        
        print("✅ Todas las tablas creadas exitosamente")
        
        # Verificar tablas creadas
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"\n📋 Tablas creadas ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)