#!/usr/bin/env python3
"""
Script para agregar campos de código de barras a la tabla products
"""
import sqlite3
import sys

def apply_barcode_migration():
    """Aplica la migración para agregar campos de código de barras"""
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        
        print("Aplicando migración de código de barras...")
        
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Agregar columna barcode si no existe
        if 'barcode' not in columns:
            cursor.execute('ALTER TABLE products ADD COLUMN barcode TEXT')
            print("✓ Columna 'barcode' agregada")
        else:
            print("ℹ Columna 'barcode' ya existe")
            
        # Agregar columna internal_code si no existe
        if 'internal_code' not in columns:
            cursor.execute('ALTER TABLE products ADD COLUMN internal_code TEXT')
            print("✓ Columna 'internal_code' agregada")
        else:
            print("ℹ Columna 'internal_code' ya existe")
        
        # Crear índices para optimizar búsquedas
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)')
            print("✓ Índice de barcode creado")
        except Exception as e:
            print(f"ℹ Índice de barcode: {e}")
            
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_internal_code ON products(internal_code)')
            print("✓ Índice de internal_code creado")
        except Exception as e:
            print(f"ℹ Índice de internal_code: {e}")
        
        # Confirmar cambios
        conn.commit()
        print("✓ Migración de código de barras completada exitosamente")
        
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
    success = apply_barcode_migration()
    sys.exit(0 if success else 1)