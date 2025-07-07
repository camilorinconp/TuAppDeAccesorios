import sys
import os

# Añadir el directorio de la app al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import crud, schemas, models
from app.utils import security

# Crear todas las tablas
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Comprobar si el usuario ya existe
admin_user = crud.get_user_by_username(db, username="admin")

if not admin_user:
    print("Creando usuario administrador...")
    user_in = schemas.UserCreate(
        username="admin",
        password="admin123",  # Cambia esto por una contraseña segura
        role=models.UserRole.admin
    )
    crud.create_user(db=db, user=user_in)
    print("Usuario 'admin' creado con éxito.")
else:
    print("El usuario 'admin' ya existe.")

db.close()
