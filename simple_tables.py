#!/usr/bin/env python3
"""
Script simple para crear tablas en PostgreSQL
"""
import psycopg2

def create_tables():
    """Crear tablas básicas"""
    
    # Conectar a PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="tuapp_db",
        user="tuapp_user",
        password="TjsgqypkqFJ1xS2024"
    )
    
    cursor = conn.cursor()
    
    # Crear tablas con SQL directo
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            sku VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            image_url VARCHAR(500),
            cost_price DECIMAL(10,2) NOT NULL,
            selling_price DECIMAL(10,2) NOT NULL,
            stock_quantity INTEGER DEFAULT 0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS point_of_sale_transactions (
            id SERIAL PRIMARY KEY,
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) NOT NULL,
            user_id INTEGER REFERENCES users(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS point_of_sale_items (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER REFERENCES point_of_sale_transactions(id),
            product_id INTEGER REFERENCES products(id),
            quantity_sold INTEGER NOT NULL,
            price_at_time_of_sale DECIMAL(10,2) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            action_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            username VARCHAR(50),
            user_role VARCHAR(20),
            session_id VARCHAR(100),
            ip_address VARCHAR(45),
            user_agent TEXT,
            table_name VARCHAR(50),
            record_id VARCHAR(50),
            description TEXT,
            old_values TEXT,
            new_values TEXT,
            additional_data TEXT,
            endpoint VARCHAR(200),
            request_method VARCHAR(10),
            response_code INTEGER,
            execution_time_ms INTEGER
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username VARCHAR(50) NOT NULL,
            success VARCHAR(10) NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            session_id VARCHAR(100),
            failure_reason VARCHAR(200),
            user_id INTEGER
        );
        """
    ]
    
    for sql in tables_sql:
        cursor.execute(sql)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tablas creadas exitosamente")

if __name__ == "__main__":
    create_tables()