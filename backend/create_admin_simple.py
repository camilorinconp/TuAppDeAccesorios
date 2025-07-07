#!/usr/bin/env python3
"""
Script simple para crear usuario admin
"""
import sys
import os
sys.path.append('/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Configuración
DATABASE_URL = "postgresql://tuappuser:tuapppassword@db:5432/tuappdb"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_admin():
    try:
        # Crear conexión a la base de datos
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Verificar si el usuario admin ya existe
        result = db.execute(text("SELECT id FROM users WHERE username = 'admin'"))
        existing_user = result.fetchone()
        
        if existing_user:
            print("Usuario admin ya existe")
            return
        
        # Crear hash de la contraseña
        hashed_password = hash_password("admin123")
        
        # Insertar usuario admin
        db.execute(text("""
            INSERT INTO users (username, email, hashed_password, role)
            VALUES ('admin', 'admin@tuapp.com', :password, 'admin')
        """), {"password": hashed_password})
        
        db.commit()
        print("Usuario admin creado exitosamente")
        print("Username: admin")
        print("Password: admin123")
        print("Email: admin@tuapp.com")
        
    except Exception as e:
        print(f"Error creando usuario admin: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    create_admin()