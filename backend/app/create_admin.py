# backend/app/create_admin.py

import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionLocal
from .models import User
from .utils.security import get_password_hash

async def create_admin_user(db: AsyncSession, username: str, email: str, password: str):
    """Crea un usuario administrador en la base de datos."""
    # Verificar si el usuario ya existe
    user = await db.get(User, (User.username == username) | (User.email == email))
    if user:
        print(f"El usuario '{username}' o el email '{email}' ya existen.")
        return

    hashed_password = get_password_hash(password)
    admin_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    await db.commit()
    print(f"Usuario administrador '{username}' creado exitosamente.")

async def main():
    parser = argparse.ArgumentParser(description="Crear un usuario administrador.")
    parser.add_argument("--username", required=True, help="Nombre de usuario del administrador.")
    parser.add_argument("--email", required=True, help="Email del administrador.")
    parser.add_argument("--password", required=True, help="Contraseña del administrador.")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Error: La contraseña debe tener al menos 8 caracteres.")
        return

    db = SessionLocal()
    try:
        await create_admin_user(db, args.username, args.email, args.password)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
