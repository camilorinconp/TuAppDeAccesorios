#!/usr/bin/env python3
"""
Script para recrear la base de datos con el esquema actualizado
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import engine, Base, SessionLocal
from app.models import *  # Importar todos los modelos
from app.utils.security import get_password_hash
from sqlalchemy import text

def recreate_database():
    """Recrear toda la base de datos"""
    
    print("🗄️ Recreando base de datos...")
    
    # Eliminar todas las tablas
    print("🧹 Eliminando tablas existentes...")
    Base.metadata.drop_all(bind=engine)
    
    # Crear todas las tablas nuevamente
    print("🏗️ Creando tablas con esquema actualizado...")
    Base.metadata.create_all(bind=engine)
    
    # Crear usuario admin
    print("👤 Creando usuario administrador...")
    db = SessionLocal()
    try:
        from app.models import User, UserRole
        
        # Verificar si ya existe admin
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if not existing_admin:
            admin_user = User(
                username="admin",
                email="admin@tuappdeaccesorios.com",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.admin,
                is_active=1
            )
            db.add(admin_user)
            db.commit()
            print("✅ Usuario admin creado exitosamente")
        else:
            print("ℹ️ Usuario admin ya existe")
            
    except Exception as e:
        print(f"❌ Error creando usuario admin: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("🎉 Base de datos recreada exitosamente!")

if __name__ == "__main__":
    recreate_database()