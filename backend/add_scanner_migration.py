#!/usr/bin/env python3
"""
Script para agregar tablas de sistema de scanner a la base de datos
"""
import sqlite3
import sys

def apply_scanner_migration():
    """Aplica la migración para agregar sistema de scanner"""
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        
        print("Aplicando migración del sistema de scanner...")
        
        # Crear tabla inventory_movements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                barcode_scanned TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                from_location_type TEXT,
                from_location_id INTEGER,
                to_location_type TEXT NOT NULL,
                to_location_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                user_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reference_type TEXT,
                reference_id INTEGER,
                notes TEXT,
                device_info TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✓ Tabla 'inventory_movements' creada")
        
        # Crear tabla scan_sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                status TEXT NOT NULL DEFAULT 'active',
                total_scans INTEGER DEFAULT 0,
                successful_scans INTEGER DEFAULT 0,
                failed_scans INTEGER DEFAULT 0,
                location_type TEXT,
                location_id INTEGER,
                reference_type TEXT,
                reference_id INTEGER,
                device_info TEXT,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✓ Tabla 'scan_sessions' creada")
        
        # Crear índices para inventory_movements
        indices_inventory = [
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_product_id ON inventory_movements(product_id)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_barcode ON inventory_movements(barcode_scanned)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_type ON inventory_movements(movement_type)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_timestamp ON inventory_movements(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_user ON inventory_movements(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_location_type ON inventory_movements(to_location_type)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_product_timestamp ON inventory_movements(product_id, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_barcode_timestamp ON inventory_movements(barcode_scanned, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_type_timestamp ON inventory_movements(movement_type, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_inventory_movement_location ON inventory_movements(to_location_type, to_location_id)'
        ]
        
        for index_sql in indices_inventory:
            cursor.execute(index_sql)
        print("✓ Índices de inventory_movements creados")
        
        # Crear índices para scan_sessions
        indices_sessions = [
            'CREATE INDEX IF NOT EXISTS idx_scan_session_user ON scan_sessions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_scan_session_type ON scan_sessions(session_type)',
            'CREATE INDEX IF NOT EXISTS idx_scan_session_status ON scan_sessions(status)',
            'CREATE INDEX IF NOT EXISTS idx_scan_session_started ON scan_sessions(started_at)',
            'CREATE INDEX IF NOT EXISTS idx_scan_session_user_started ON scan_sessions(user_id, started_at)',
            'CREATE INDEX IF NOT EXISTS idx_scan_session_type_status ON scan_sessions(session_type, status)'
        ]
        
        for index_sql in indices_sessions:
            cursor.execute(index_sql)
        print("✓ Índices de scan_sessions creados")
        
        # Confirmar cambios
        conn.commit()
        print("✓ Migración del sistema de scanner completada exitosamente")
        
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
    success = apply_scanner_migration()
    sys.exit(0 if success else 1)