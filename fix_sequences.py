#!/usr/bin/env python3
"""
Script para arreglar las secuencias de PostgreSQL después de la migración
"""
import psycopg2

def fix_sequences():
    """Arreglar secuencias de PostgreSQL"""
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="tuapp_db",
        user="tuapp_user",
        password="TjsgqypkqFJ1xS2024"
    )
    
    cursor = conn.cursor()
    
    # Lista de tablas con secuencias
    tables = [
        'users',
        'products', 
        'point_of_sale_transactions',
        'point_of_sale_items',
        'audit_logs',
        'login_attempts'
    ]
    
    for table in tables:
        try:
            # Obtener el máximo ID actual
            cursor.execute(f"SELECT MAX(id) FROM {table}")
            max_id = cursor.fetchone()[0]
            
            if max_id is not None:
                # Ajustar la secuencia al siguiente valor
                next_id = max_id + 1
                cursor.execute(f"SELECT setval('{table}_id_seq', {next_id})")
                print(f"✅ {table}: secuencia actualizada a {next_id}")
            else:
                print(f"📋 {table}: tabla vacía")
                
        except Exception as e:
            print(f"❌ Error en tabla {table}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("🎉 Secuencias actualizadas exitosamente")

if __name__ == "__main__":
    fix_sequences()