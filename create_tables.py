#!/usr/bin/env python3
"""
Script para crear las tablas básicas en PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey, text
from datetime import datetime

def create_tables():
    """Crear todas las tablas en PostgreSQL"""
    # URL de conexión a PostgreSQL
    database_url = "postgresql://tuapp_user:TjsgqypkqFJ1xS2024@localhost:5432/tuapp_db"
    
    try:
        # Crear engine
        engine = create_engine(database_url)
        metadata = MetaData()
        
        print("🔄 Creando tablas en PostgreSQL...")
        
        # Tabla users
        users = Table('users', metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String(50), unique=True, nullable=False),
            Column('email', String(100), unique=True, nullable=False),
            Column('hashed_password', String(255), nullable=False),
            Column('role', String(20), nullable=False, default='user'),
            Column('is_active', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Tabla products
        products = Table('products', metadata,
            Column('id', Integer, primary_key=True),
            Column('sku', String(50), unique=True, nullable=False),
            Column('name', String(200), nullable=False),
            Column('description', Text),
            Column('image_url', String(500)),
            Column('cost_price', Float, nullable=False),
            Column('selling_price', Float, nullable=False),
            Column('stock_quantity', Integer, default=0)
        )
        
        # Tabla point_of_sale_transactions
        pos_transactions = Table('point_of_sale_transactions', metadata,
            Column('id', Integer, primary_key=True),
            Column('transaction_time', DateTime, default=datetime.utcnow),
            Column('total_amount', Float, nullable=False),
            Column('user_id', Integer, ForeignKey('users.id'))
        )
        
        # Tabla point_of_sale_items
        pos_items = Table('point_of_sale_items', metadata,
            Column('id', Integer, primary_key=True),
            Column('transaction_id', Integer, ForeignKey('point_of_sale_transactions.id')),
            Column('product_id', Integer, ForeignKey('products.id')),
            Column('quantity_sold', Integer, nullable=False),
            Column('price_at_time_of_sale', Float, nullable=False)
        )
        
        # Tabla audit_logs
        audit_logs = Table('audit_logs', metadata,
            Column('id', Integer, primary_key=True),
            Column('action_type', String(50), nullable=False),
            Column('severity', String(20), nullable=False),
            Column('timestamp', DateTime, default=datetime.utcnow),
            Column('user_id', Integer),
            Column('username', String(50)),
            Column('user_role', String(20)),
            Column('session_id', String(100)),
            Column('ip_address', String(45)),
            Column('user_agent', Text),
            Column('table_name', String(50)),
            Column('record_id', String(50)),
            Column('description', Text),
            Column('old_values', Text),
            Column('new_values', Text),
            Column('additional_data', Text),
            Column('endpoint', String(200)),
            Column('request_method', String(10)),
            Column('response_code', Integer),
            Column('execution_time_ms', Integer)
        )
        
        # Tabla login_attempts
        login_attempts = Table('login_attempts', metadata,
            Column('id', Integer, primary_key=True),
            Column('timestamp', DateTime, default=datetime.utcnow),
            Column('username', String(50), nullable=False),
            Column('success', String(10), nullable=False),
            Column('ip_address', String(45)),
            Column('user_agent', Text),
            Column('session_id', String(100)),
            Column('failure_reason', String(200)),
            Column('user_id', Integer)
        )
        
        # Crear todas las tablas
        metadata.create_all(engine)
        print("✅ Tablas creadas exitosamente!")
        
        # Verificar tablas creadas
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
        
        print(f"📊 Tablas creadas:")
        for table in sorted(tables):
            print(f"  - {table}")
            
        return True
            
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False

if __name__ == "__main__":
    if create_tables():
        sys.exit(0)
    else:
        sys.exit(1)