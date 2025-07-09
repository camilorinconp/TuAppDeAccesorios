#!/usr/bin/env python3
"""
Script para actualizar datos de consignación con la nueva lógica de negocio.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date

# Configuración de base de datos
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_consignment_data():
    """Actualiza los datos de consignación con la nueva lógica"""
    
    db = SessionLocal()
    
    try:
        print("🔄 Actualizando datos de consignación...")
        
        # 1. Actualizar campos nuevos en consignment_loans
        print("1. Actualizando campos nuevos en consignment_loans...")
        
        # Actualizar quantity_reported y quantity_pending para préstamos existentes
        db.execute(text("""
            UPDATE consignment_loans 
            SET quantity_reported = 0,
                quantity_pending = quantity_loaned,
                created_at = datetime('now'),
                updated_at = datetime('now')
            WHERE quantity_reported IS NULL
        """))
        
        # Actualizar quantity_reported basado en reportes existentes
        db.execute(text("""
            UPDATE consignment_loans 
            SET quantity_reported = (
                SELECT COALESCE(SUM(quantity_sold + quantity_returned), 0)
                FROM consignment_reports 
                WHERE consignment_reports.loan_id = consignment_loans.id
            )
        """))
        
        # Actualizar quantity_pending
        db.execute(text("""
            UPDATE consignment_loans 
            SET quantity_pending = quantity_loaned - quantity_reported
        """))
        
        # Actualizar status basado en quantity_pending
        db.execute(text("""
            UPDATE consignment_loans 
            SET status = CASE 
                WHEN quantity_pending = 0 THEN 'devuelto'
                WHEN quantity_pending < quantity_loaned THEN 'parcialmente_devuelto'
                WHEN return_due_date < date('now') THEN 'vencido'
                ELSE 'en_prestamo'
            END
        """))
        
        # 2. Actualizar campos nuevos en consignment_reports
        print("2. Actualizando campos nuevos en consignment_reports...")
        
        db.execute(text("""
            UPDATE consignment_reports 
            SET created_at = datetime('now'),
                is_final_report = 0
            WHERE created_at IS NULL
        """))
        
        # 3. Inicializar product_locations para productos existentes
        print("3. Inicializando product_locations para productos existentes...")
        
        # Crear ubicaciones de bodega para todos los productos
        db.execute(text("""
            INSERT INTO product_locations (product_id, location_type, location_id, quantity, created_at, updated_at, reference_type, notes)
            SELECT 
                id,
                'warehouse',
                NULL,
                stock_quantity,
                datetime('now'),
                datetime('now'),
                'initial_stock',
                'Stock inicial del producto'
            FROM products
            WHERE id NOT IN (
                SELECT DISTINCT product_id 
                FROM product_locations 
                WHERE location_type = 'warehouse'
            )
        """))
        
        # 4. Mostrar estadísticas
        print("4. Mostrando estadísticas de actualización...")
        
        # Contar préstamos por estado
        result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM consignment_loans
            GROUP BY status
        """)).fetchall()
        
        print("📊 Préstamos por estado:")
        for row in result:
            print(f"   {row[0]}: {row[1]} préstamos")
        
        # Contar ubicaciones de productos
        result = db.execute(text("""
            SELECT location_type, COUNT(*) as count, SUM(quantity) as total_quantity
            FROM product_locations
            GROUP BY location_type
        """)).fetchall()
        
        print("📦 Productos por ubicación:")
        for row in result:
            print(f"   {row[0]}: {row[1]} registros, {row[2]} unidades")
        
        # 5. Verificar integridad
        print("5. Verificando integridad de datos...")
        
        # Verificar que todos los préstamos tengan quantity_reported y quantity_pending
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM consignment_loans 
            WHERE quantity_reported IS NULL OR quantity_pending IS NULL
        """)).fetchone()
        
        if result[0] == 0:
            print("✅ Todos los préstamos tienen quantity_reported y quantity_pending")
        else:
            print(f"❌ {result[0]} préstamos no tienen quantity_reported o quantity_pending")
        
        # Verificar que todos los productos tengan ubicación de bodega
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM products p
            LEFT JOIN product_locations pl ON p.id = pl.product_id AND pl.location_type = 'warehouse'
            WHERE pl.id IS NULL
        """)).fetchone()
        
        if result[0] == 0:
            print("✅ Todos los productos tienen ubicación de bodega")
        else:
            print(f"❌ {result[0]} productos no tienen ubicación de bodega")
        
        db.commit()
        print("✅ Actualización de datos completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error durante la actualización: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_consignment_data()