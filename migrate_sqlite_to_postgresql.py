#!/usr/bin/env python3
"""
Script para migrar datos de SQLite a PostgreSQL
"""
import sqlite3
import psycopg2
import os
import sys
from datetime import datetime
import json

def connect_sqlite(db_path):
    """Conectar a SQLite"""
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos SQLite: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print(f"✅ Conectado a SQLite: {db_path}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a SQLite: {e}")
        return None

def connect_postgresql():
    """Conectar a PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database=os.getenv("POSTGRES_DB", "tuapp_db"),
            user=os.getenv("POSTGRES_USER", "tuapp_user"),
            password=os.getenv("POSTGRES_PASSWORD", "TjsgqypkqFJ1xS2024")
        )
        conn.autocommit = True
        print("✅ Conectado a PostgreSQL")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        print("Asegúrate de que los servicios Docker estén ejecutándose:")
        print("docker-compose ps")
        return None

def get_table_data(sqlite_conn, table_name):
    """Obtener datos de una tabla SQLite"""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            columns = [description[0] for description in cursor.description]
            print(f"📊 Tabla {table_name}: {len(rows)} registros")
            return rows, columns
        else:
            print(f"📋 Tabla {table_name}: vacía")
            return [], []
    except Exception as e:
        print(f"❌ Error leyendo tabla {table_name}: {e}")
        return [], []

def migrate_users(sqlite_conn, pg_conn):
    """Migrar tabla users"""
    print("\n🔄 Migrando usuarios...")
    
    rows, columns = get_table_data(sqlite_conn, "users")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row['id'],
                row['username'],
                row['email'],
                row['hashed_password'],
                row['role'],
                bool(row['is_active']),  # Convertir a boolean
                row['created_at']
            ))
        
        print(f"✅ Migrados {len(rows)} usuarios")
    except Exception as e:
        print(f"❌ Error migrando usuarios: {e}")

def migrate_products(sqlite_conn, pg_conn):
    """Migrar tabla products"""
    print("\n🔄 Migrando productos...")
    
    rows, columns = get_table_data(sqlite_conn, "products")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO products (id, sku, name, description, image_url, cost_price, selling_price, stock_quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['id'],
                row['sku'],
                row['name'],
                row['description'],
                row['image_url'],
                row['cost_price'],
                row['selling_price'],
                row['stock_quantity']
            ))
        
        print(f"✅ Migrados {len(rows)} productos")
    except Exception as e:
        print(f"❌ Error migrando productos: {e}")

def migrate_pos_transactions(sqlite_conn, pg_conn):
    """Migrar tabla point_of_sale_transactions"""
    print("\n🔄 Migrando transacciones POS...")
    
    rows, columns = get_table_data(sqlite_conn, "point_of_sale_transactions")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE point_of_sale_transactions RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO point_of_sale_transactions (id, transaction_time, total_amount, user_id)
                VALUES (%s, %s, %s, %s)
            """, (
                row['id'],
                row['transaction_time'],
                row['total_amount'],
                row['user_id']
            ))
        
        print(f"✅ Migradas {len(rows)} transacciones POS")
    except Exception as e:
        print(f"❌ Error migrando transacciones POS: {e}")

def migrate_pos_items(sqlite_conn, pg_conn):
    """Migrar tabla point_of_sale_items"""
    print("\n🔄 Migrando items POS...")
    
    rows, columns = get_table_data(sqlite_conn, "point_of_sale_items")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE point_of_sale_items RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO point_of_sale_items (id, transaction_id, product_id, quantity_sold, price_at_time_of_sale)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                row['id'],
                row['transaction_id'],
                row['product_id'],
                row['quantity_sold'],
                row['price_at_time_of_sale']
            ))
        
        print(f"✅ Migrados {len(rows)} items POS")
    except Exception as e:
        print(f"❌ Error migrando items POS: {e}")

def migrate_audit_logs(sqlite_conn, pg_conn):
    """Migrar tabla audit_logs"""
    print("\n🔄 Migrando logs de auditoría...")
    
    rows, columns = get_table_data(sqlite_conn, "audit_logs")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO audit_logs (id, action_type, severity, timestamp, user_id, username, user_role, 
                                      session_id, ip_address, user_agent, table_name, record_id, description, 
                                      old_values, new_values, additional_data, endpoint, request_method, 
                                      response_code, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['id'],
                row['action_type'],
                row['severity'],
                row['timestamp'],
                row['user_id'],
                row['username'],
                row['user_role'],
                row['session_id'],
                row['ip_address'],
                row['user_agent'],
                row['table_name'],
                row['record_id'],
                row['description'],
                row['old_values'],
                row['new_values'],
                row['additional_data'],
                row['endpoint'],
                row['request_method'],
                row['response_code'],
                row['execution_time_ms']
            ))
        
        print(f"✅ Migrados {len(rows)} logs de auditoría")
    except Exception as e:
        print(f"❌ Error migrando logs de auditoría: {e}")

def migrate_login_attempts(sqlite_conn, pg_conn):
    """Migrar tabla login_attempts"""
    print("\n🔄 Migrando intentos de login...")
    
    rows, columns = get_table_data(sqlite_conn, "login_attempts")
    if not rows:
        return
    
    try:
        cursor = pg_conn.cursor()
        
        # Limpiar tabla existente
        cursor.execute("TRUNCATE TABLE login_attempts RESTART IDENTITY CASCADE;")
        
        for row in rows:
            cursor.execute("""
                INSERT INTO login_attempts (id, timestamp, username, success, ip_address, user_agent, 
                                          session_id, failure_reason, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['id'],
                row['timestamp'],
                row['username'],
                str(row['success']),  # Convertir a string
                row['ip_address'],
                row['user_agent'],
                row['session_id'],
                row['failure_reason'],
                row['user_id']
            ))
        
        print(f"✅ Migrados {len(rows)} intentos de login")
    except Exception as e:
        print(f"❌ Error migrando intentos de login: {e}")

def verify_migration(pg_conn):
    """Verificar la migración"""
    print("\n🔍 Verificando migración...")
    
    tables = ['users', 'products', 'point_of_sale_transactions', 'point_of_sale_items', 
              'audit_logs', 'login_attempts']
    
    cursor = pg_conn.cursor()
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} registros")
        except Exception as e:
            print(f"❌ Error verificando {table}: {e}")

def main():
    """Función principal"""
    print("🚀 Iniciando migración de SQLite a PostgreSQL")
    print("=" * 50)
    
    # Conectar a ambas bases de datos
    sqlite_path = "backend/test.db"
    sqlite_conn = connect_sqlite(sqlite_path)
    if not sqlite_conn:
        sys.exit(1)
    
    pg_conn = connect_postgresql()
    if not pg_conn:
        sys.exit(1)
    
    try:
        # Migrar cada tabla
        migrate_users(sqlite_conn, pg_conn)
        migrate_products(sqlite_conn, pg_conn)
        migrate_pos_transactions(sqlite_conn, pg_conn)
        migrate_pos_items(sqlite_conn, pg_conn)
        migrate_audit_logs(sqlite_conn, pg_conn)
        migrate_login_attempts(sqlite_conn, pg_conn)
        
        # Verificar migración
        verify_migration(pg_conn)
        
        print("\n🎉 Migración completada exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        sys.exit(1)
    
    finally:
        # Cerrar conexiones
        if sqlite_conn:
            sqlite_conn.close()
        if pg_conn:
            pg_conn.close()

if __name__ == "__main__":
    main()