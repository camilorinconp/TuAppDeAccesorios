#!/bin/bash
set -e

# Script de inicialización de PostgreSQL para TuAppDeAccesorios
# Este script se ejecuta automáticamente cuando el contenedor se crea por primera vez

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Crear extensiones necesarias
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsquedas de texto avanzadas
    
    -- Configurar timezone por defecto
    SET timezone = 'UTC';
    
    -- Crear esquemas si no existen
    CREATE SCHEMA IF NOT EXISTS public;
    
    -- Configurar permisos para el usuario de la aplicación
    GRANT ALL PRIVILEGES ON SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
    
    -- Crear función para actualizar timestamps automáticamente
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';
    
    -- Crear función para logging de cambios (audit trail)
    CREATE OR REPLACE FUNCTION log_changes()
    RETURNS TRIGGER AS \$\$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO audit_log (table_name, operation, new_data, timestamp)
            VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW), CURRENT_TIMESTAMP);
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO audit_log (table_name, operation, old_data, new_data, timestamp)
            VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), CURRENT_TIMESTAMP);
            RETURN NEW;
        ELSIF TG_OP = 'DELETE' THEN
            INSERT INTO audit_log (table_name, operation, old_data, timestamp)
            VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), CURRENT_TIMESTAMP);
            RETURN OLD;
        END IF;
        RETURN NULL;
    END;
    \$\$ language 'plpgsql';
    
    -- Crear tabla de auditoría
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        table_name VARCHAR(255) NOT NULL,
        operation VARCHAR(10) NOT NULL,
        old_data JSONB,
        new_data JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER
    );
    
    -- Crear índices para la tabla de auditoría
    CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit_log(operation);
    
    -- Configurar búsqueda de texto completo
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'spanish_config') THEN
            CREATE TEXT SEARCH CONFIGURATION spanish_config (COPY = spanish);
        END IF;
    END
    \$\$;
    
    -- Optimizaciones de rendimiento
    ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
    ALTER SYSTEM SET pg_stat_statements.track = 'all';
    ALTER SYSTEM SET log_min_duration_statement = 1000;
    
    -- Configuración de autovacuum optimizada
    ALTER SYSTEM SET autovacuum_naptime = '1min';
    ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;
    ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05;
    
    SELECT pg_reload_conf();
    
    \echo 'Database initialization completed successfully!'
EOSQL