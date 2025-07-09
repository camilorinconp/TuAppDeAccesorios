#!/usr/bin/env python3
"""
Script para agregar campo wholesale_price a la tabla products
"""
import sqlite3
import sys

def apply_wholesale_price_migration():
    """Aplica la migración para agregar campo wholesale_price"""
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        
        print("Aplicando migración de precio mayorista...")
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Agregar columna wholesale_price si no existe
        if 'wholesale_price' not in columns:
            cursor.execute('ALTER TABLE products ADD COLUMN wholesale_price NUMERIC(10, 2)')
            print("✓ Columna 'wholesale_price' agregada")
        else:
            print("ℹ Columna 'wholesale_price' ya existe")
        
        # Crear índice para optimizar consultas por precio mayorista
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_wholesale_price ON products(wholesale_price)')
            print("✓ Índice de wholesale_price creado")
        except Exception as e:
            print(f"ℹ Índice de wholesale_price: {e}")
        
        # Confirmar cambios
        conn.commit()
        print("✓ Migración de precio mayorista completada exitosamente")
        
    except sqlite3.Error as e:
        print(f"❌ Error en la migración: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    success = apply_wholesale_price_migration()
    sys.exit(0 if success else 1)