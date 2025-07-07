"""add_audit_and_timestamps

Revision ID: 002
Revises: 001
Create Date: 2025-07-05 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar campos de auditoría y timestamps a todas las tablas"""
    
    # Lista de tablas que necesitan campos de auditoría
    tables_to_audit = [
        'products',
        'distributors', 
        'users',
        'point_of_sale_transactions',
        'point_of_sale_items',
        'consignment_loans',
        'consignment_reports'
    ]
    
    # Agregar campos de timestamp a todas las tablas
    for table_name in tables_to_audit:
        # Agregar created_at
        op.add_column(table_name, sa.Column('created_at', sa.DateTime(timezone=True), 
                                           server_default=sa.text('CURRENT_TIMESTAMP'), 
                                           nullable=False))
        
        # Agregar updated_at
        op.add_column(table_name, sa.Column('updated_at', sa.DateTime(timezone=True), 
                                           server_default=sa.text('CURRENT_TIMESTAMP'), 
                                           nullable=False))
        
        # Agregar versión para optimistic locking
        op.add_column(table_name, sa.Column('version', sa.Integer, 
                                           server_default='1', 
                                           nullable=False))
    
    # Crear tabla de auditoría global
    op.create_table('audit_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column('record_id', sa.BigInteger, nullable=False),
        sa.Column('operation', sa.String(10), nullable=False),  # INSERT, UPDATE, DELETE
        sa.Column('old_data', postgresql.JSONB, nullable=True),
        sa.Column('new_data', postgresql.JSONB, nullable=True),
        sa.Column('changed_fields', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('user_ip', sa.String(45), nullable=True),  # IPv6 compatible
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), 
                 server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True)
    )
    
    # Índices para tabla de auditoría
    op.create_index('idx_audit_log_table_record', 'audit_log', ['table_name', 'record_id'])
    op.create_index('idx_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_log_operation', 'audit_log', ['operation'])
    op.create_index('idx_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_table_name', 'audit_log', ['table_name'])
    
    # Crear función de trigger para updated_at
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        NEW.version = NEW.version + 1;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)
    
    # Crear triggers para cada tabla
    for table_name in tables_to_audit:
        op.execute(f"""
        CREATE TRIGGER update_{table_name}_updated_at 
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    
    # Crear función de auditoría
    op.execute("""
    CREATE OR REPLACE FUNCTION log_table_changes()
    RETURNS TRIGGER AS $$
    DECLARE
        old_data JSONB;
        new_data JSONB;
        changed_fields TEXT[];
        field_name TEXT;
    BEGIN
        -- Convertir registros a JSONB
        IF TG_OP = 'DELETE' THEN
            old_data = to_jsonb(OLD);
            new_data = NULL;
        ELSIF TG_OP = 'INSERT' THEN
            old_data = NULL;
            new_data = to_jsonb(NEW);
        ELSIF TG_OP = 'UPDATE' THEN
            old_data = to_jsonb(OLD);
            new_data = to_jsonb(NEW);
            
            -- Detectar campos cambiados
            changed_fields = ARRAY[]::TEXT[];
            FOR field_name IN SELECT jsonb_object_keys(new_data) LOOP
                IF old_data->field_name IS DISTINCT FROM new_data->field_name THEN
                    changed_fields = array_append(changed_fields, field_name);
                END IF;
            END LOOP;
        END IF;
        
        -- Insertar en audit_log
        INSERT INTO audit_log (
            table_name, 
            record_id, 
            operation, 
            old_data, 
            new_data, 
            changed_fields,
            timestamp
        ) VALUES (
            TG_TABLE_NAME,
            COALESCE((NEW.id)::BIGINT, (OLD.id)::BIGINT),
            TG_OP,
            old_data,
            new_data,
            changed_fields,
            CURRENT_TIMESTAMP
        );
        
        RETURN COALESCE(NEW, OLD);
    END;
    $$ language 'plpgsql';
    """)
    
    # Crear triggers de auditoría para cada tabla
    for table_name in tables_to_audit:
        op.execute(f"""
        CREATE TRIGGER audit_{table_name}_changes
        AFTER INSERT OR UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION log_table_changes();
        """)
    
    # Crear tabla para configuración de la aplicación
    op.create_table('app_config',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(255), unique=True, nullable=False),
        sa.Column('value', sa.Text, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('value_type', sa.String(50), nullable=False, server_default='string'),  # string, integer, boolean, json
        sa.Column('is_encrypted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('version', sa.Integer, server_default='1', nullable=False)
    )
    
    # Índices para configuración
    op.create_index('idx_app_config_key', 'app_config', ['key'])
    op.create_index('idx_app_config_type', 'app_config', ['value_type'])
    
    # Trigger para app_config
    op.execute("""
    CREATE TRIGGER update_app_config_updated_at 
    BEFORE UPDATE ON app_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Insertar configuraciones por defecto
    op.execute("""
    INSERT INTO app_config (key, value, description, value_type) VALUES
    ('app_version', '1.0.0', 'Versión actual de la aplicación', 'string'),
    ('maintenance_mode', 'false', 'Modo de mantenimiento activado', 'boolean'),
    ('max_file_upload_size', '10485760', 'Tamaño máximo de archivo en bytes (10MB)', 'integer'),
    ('session_timeout', '3600', 'Timeout de sesión en segundos', 'integer'),
    ('backup_retention_days', '30', 'Días de retención de backups', 'integer'),
    ('audit_retention_days', '365', 'Días de retención de logs de auditoría', 'integer');
    """)


def downgrade():
    """Eliminar campos de auditoría y timestamps"""
    
    # Lista de tablas para revertir
    tables_to_audit = [
        'products',
        'distributors', 
        'users',
        'point_of_sale_transactions',
        'point_of_sale_items',
        'consignment_loans',
        'consignment_reports'
    ]
    
    # Eliminar triggers de auditoría
    for table_name in tables_to_audit:
        op.execute(f"DROP TRIGGER IF EXISTS audit_{table_name}_changes ON {table_name};")
        op.execute(f"DROP TRIGGER IF EXISTS update_{table_name}_updated_at ON {table_name};")
    
    # Eliminar funciones
    op.execute("DROP FUNCTION IF EXISTS log_table_changes();")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Eliminar tabla de configuración
    op.drop_table('app_config')
    
    # Eliminar tabla de auditoría
    op.drop_table('audit_log')
    
    # Eliminar campos de timestamp de todas las tablas
    for table_name in tables_to_audit:
        op.drop_column(table_name, 'version')
        op.drop_column(table_name, 'updated_at')
        op.drop_column(table_name, 'created_at')