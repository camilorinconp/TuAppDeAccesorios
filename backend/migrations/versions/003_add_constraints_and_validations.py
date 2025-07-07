"""add_constraints_and_validations

Revision ID: 003
Revises: 002
Create Date: 2025-07-05 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar constraints y validaciones para integridad de datos"""
    
    # CONSTRAINTS PARA PRODUCTOS
    # Verificar que los precios sean positivos
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_cost_price_positive 
    CHECK (cost_price > 0);
    """)
    
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_selling_price_positive 
    CHECK (selling_price > 0);
    """)
    
    # Verificar que el precio de venta sea mayor que el costo
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_selling_price_greater_than_cost 
    CHECK (selling_price >= cost_price);
    """)
    
    # Verificar que el stock no sea negativo
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_stock_quantity_non_negative 
    CHECK (stock_quantity >= 0);
    """)
    
    # Verificar formato del SKU (alfanumérico, 3-20 caracteres)
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_sku_format 
    CHECK (sku ~ '^[A-Z0-9]{3,20}$');
    """)
    
    # Verificar que el nombre del producto no esté vacío
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_name_not_empty 
    CHECK (length(trim(name)) > 0);
    """)
    
    # CONSTRAINTS PARA USUARIOS
    # Verificar que el username sea válido (alfanumérico + underscore, 3-50 caracteres)
    op.execute("""
    ALTER TABLE users ADD CONSTRAINT check_username_format 
    CHECK (username ~ '^[a-zA-Z0-9_]{3,50}$');
    """)
    
    # Verificar que el password hash no esté vacío
    op.execute("""
    ALTER TABLE users ADD CONSTRAINT check_password_hash_not_empty 
    CHECK (length(trim(hashed_password)) > 0);
    """)
    
    # CONSTRAINTS PARA DISTRIBUIDORES
    # Verificar que el nombre no esté vacío
    op.execute("""
    ALTER TABLE distributors ADD CONSTRAINT check_distributor_name_not_empty 
    CHECK (length(trim(name)) > 0);
    """)
    
    # Verificar formato del código de acceso (6-20 caracteres alfanuméricos)
    op.execute("""
    ALTER TABLE distributors ADD CONSTRAINT check_access_code_format 
    CHECK (access_code ~ '^[A-Z0-9]{6,20}$');
    """)
    
    # Verificar formato del teléfono (opcional, pero si está presente debe ser válido)
    op.execute("""
    ALTER TABLE distributors ADD CONSTRAINT check_phone_format 
    CHECK (phone_number IS NULL OR phone_number ~ '^[+]?[0-9\s\-\(\)]{10,20}$');
    """)
    
    # CONSTRAINTS PARA TRANSACCIONES POS
    # Verificar que el total sea positivo
    op.execute("""
    ALTER TABLE point_of_sale_transactions ADD CONSTRAINT check_total_amount_positive 
    CHECK (total_amount > 0);
    """)
    
    # Verificar que la fecha de transacción no sea futura
    op.execute("""
    ALTER TABLE point_of_sale_transactions ADD CONSTRAINT check_transaction_time_not_future 
    CHECK (transaction_time <= CURRENT_TIMESTAMP);
    """)
    
    # CONSTRAINTS PARA ÍTEMS DE VENTA
    # Verificar que la cantidad vendida sea positiva
    op.execute("""
    ALTER TABLE point_of_sale_items ADD CONSTRAINT check_quantity_sold_positive 
    CHECK (quantity_sold > 0);
    """)
    
    # Verificar que el precio al momento de venta sea positivo
    op.execute("""
    ALTER TABLE point_of_sale_items ADD CONSTRAINT check_price_at_sale_positive 
    CHECK (price_at_time_of_sale > 0);
    """)
    
    # CONSTRAINTS PARA PRÉSTAMOS DE CONSIGNACIÓN
    # Verificar que la cantidad prestada sea positiva
    op.execute("""
    ALTER TABLE consignment_loans ADD CONSTRAINT check_quantity_loaned_positive 
    CHECK (quantity_loaned > 0);
    """)
    
    # Verificar que la fecha de devolución sea posterior a la fecha de préstamo
    op.execute("""
    ALTER TABLE consignment_loans ADD CONSTRAINT check_return_date_after_loan_date 
    CHECK (return_due_date > loan_date);
    """)
    
    # Verificar que la fecha de préstamo no sea futura
    op.execute("""
    ALTER TABLE consignment_loans ADD CONSTRAINT check_loan_date_not_future 
    CHECK (loan_date <= CURRENT_DATE);
    """)
    
    # CONSTRAINTS PARA REPORTES DE CONSIGNACIÓN
    # Verificar que las cantidades sean no negativas
    op.execute("""
    ALTER TABLE consignment_reports ADD CONSTRAINT check_quantity_sold_non_negative 
    CHECK (quantity_sold >= 0);
    """)
    
    op.execute("""
    ALTER TABLE consignment_reports ADD CONSTRAINT check_quantity_returned_non_negative 
    CHECK (quantity_returned >= 0);
    """)
    
    # Verificar que al menos una cantidad sea mayor que 0
    op.execute("""
    ALTER TABLE consignment_reports ADD CONSTRAINT check_quantities_not_both_zero 
    CHECK (quantity_sold > 0 OR quantity_returned > 0);
    """)
    
    # Verificar que la fecha del reporte no sea futura
    op.execute("""
    ALTER TABLE consignment_reports ADD CONSTRAINT check_report_date_not_future 
    CHECK (report_date <= CURRENT_DATE);
    """)
    
    # AGREGAR FUNCIONES DE VALIDACIÓN AVANZADA
    
    # Función para validar email
    op.execute("""
    CREATE OR REPLACE FUNCTION is_valid_email(email TEXT) 
    RETURNS BOOLEAN AS $$
    BEGIN
        RETURN email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Función para validar URL de imagen
    op.execute("""
    CREATE OR REPLACE FUNCTION is_valid_image_url(url TEXT) 
    RETURNS BOOLEAN AS $$
    BEGIN
        RETURN url IS NULL OR url ~ '^https?://.*\.(jpg|jpeg|png|gif|webp)(\?.*)?$';
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Agregar constraint para URL de imagen en productos
    op.execute("""
    ALTER TABLE products ADD CONSTRAINT check_image_url_format 
    CHECK (is_valid_image_url(image_url));
    """)
    
    # CREAR ÍNDICES ÚNICOS COMPUESTOS ADICIONALES
    
    # Prevenir productos duplicados con mismo nombre y SKU por error
    op.create_index('idx_products_name_sku_unique', 'products', ['name', 'sku'], unique=True)
    
    # Prevenir transacciones duplicadas por usuario en el mismo timestamp
    op.create_index('idx_pos_transaction_user_time_unique', 'point_of_sale_transactions', 
                   ['user_id', 'transaction_time'], unique=True)
    
    # Prevenir múltiples préstamos del mismo producto al mismo distribuidor en la misma fecha
    op.create_index('idx_consignment_loan_unique', 'consignment_loans', 
                   ['distributor_id', 'product_id', 'loan_date'], unique=True)
    
    # CREAR FUNCIONES DE VALIDACIÓN DE NEGOCIO
    
    # Función para verificar stock suficiente antes de venta
    op.execute("""
    CREATE OR REPLACE FUNCTION check_sufficient_stock(product_id_param INTEGER, quantity_needed INTEGER) 
    RETURNS BOOLEAN AS $$
    DECLARE
        current_stock INTEGER;
    BEGIN
        SELECT stock_quantity INTO current_stock 
        FROM products 
        WHERE id = product_id_param;
        
        RETURN current_stock >= quantity_needed;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Función para calcular margen de ganancia
    op.execute("""
    CREATE OR REPLACE FUNCTION calculate_profit_margin(product_id_param INTEGER) 
    RETURNS DECIMAL(5,2) AS $$
    DECLARE
        cost DECIMAL(10,2);
        selling DECIMAL(10,2);
    BEGIN
        SELECT cost_price, selling_price INTO cost, selling
        FROM products 
        WHERE id = product_id_param;
        
        IF cost = 0 THEN
            RETURN 0;
        END IF;
        
        RETURN ((selling - cost) / cost) * 100;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Función para obtener productos con bajo stock
    op.execute("""
    CREATE OR REPLACE FUNCTION get_low_stock_products(threshold INTEGER DEFAULT 10) 
    RETURNS TABLE(
        product_id INTEGER,
        product_name TEXT,
        current_stock INTEGER,
        sku TEXT
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT id, name::TEXT, stock_quantity, products.sku
        FROM products
        WHERE stock_quantity <= threshold
        ORDER BY stock_quantity ASC;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # CREAR VISTA PARA REPORTES COMUNES
    
    # Vista para resumen de ventas por producto
    op.execute("""
    CREATE OR REPLACE VIEW v_product_sales_summary AS
    SELECT 
        p.id as product_id,
        p.name as product_name,
        p.sku,
        p.cost_price,
        p.selling_price,
        p.stock_quantity,
        COALESCE(SUM(psi.quantity_sold), 0) as total_sold,
        COALESCE(SUM(psi.quantity_sold * psi.price_at_time_of_sale), 0) as total_revenue,
        COALESCE(SUM(psi.quantity_sold * p.cost_price), 0) as total_cost,
        COALESCE(SUM(psi.quantity_sold * (psi.price_at_time_of_sale - p.cost_price)), 0) as total_profit,
        calculate_profit_margin(p.id) as profit_margin_percent
    FROM products p
    LEFT JOIN point_of_sale_items psi ON p.id = psi.product_id
    GROUP BY p.id, p.name, p.sku, p.cost_price, p.selling_price, p.stock_quantity;
    """)
    
    # Vista para distribuidores con préstamos activos
    op.execute("""
    CREATE OR REPLACE VIEW v_active_consignments AS
    SELECT 
        d.id as distributor_id,
        d.name as distributor_name,
        d.contact_person,
        d.phone_number,
        COUNT(cl.id) as active_loans,
        SUM(cl.quantity_loaned) as total_quantity_loaned,
        MIN(cl.return_due_date) as earliest_due_date,
        COUNT(CASE WHEN cl.return_due_date < CURRENT_DATE THEN 1 END) as overdue_loans
    FROM distributors d
    LEFT JOIN consignment_loans cl ON d.id = cl.distributor_id 
        AND cl.status = 'en_prestamo'
    GROUP BY d.id, d.name, d.contact_person, d.phone_number
    HAVING COUNT(cl.id) > 0;
    """)


def downgrade():
    """Eliminar constraints y validaciones"""
    
    # Eliminar vistas
    op.execute("DROP VIEW IF EXISTS v_active_consignments;")
    op.execute("DROP VIEW IF EXISTS v_product_sales_summary;")
    
    # Eliminar funciones
    op.execute("DROP FUNCTION IF EXISTS get_low_stock_products(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS calculate_profit_margin(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS check_sufficient_stock(INTEGER, INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS is_valid_image_url(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS is_valid_email(TEXT);")
    
    # Eliminar índices únicos compuestos
    op.drop_index('idx_consignment_loan_unique', table_name='consignment_loans')
    op.drop_index('idx_pos_transaction_user_time_unique', table_name='point_of_sale_transactions')
    op.drop_index('idx_products_name_sku_unique', table_name='products')
    
    # Eliminar constraints de productos
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_image_url_format;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_name_not_empty;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_sku_format;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_stock_quantity_non_negative;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_selling_price_greater_than_cost;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_selling_price_positive;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_cost_price_positive;")
    
    # Eliminar constraints de usuarios
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_password_hash_not_empty;")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_username_format;")
    
    # Eliminar constraints de distribuidores
    op.execute("ALTER TABLE distributors DROP CONSTRAINT IF EXISTS check_phone_format;")
    op.execute("ALTER TABLE distributors DROP CONSTRAINT IF EXISTS check_access_code_format;")
    op.execute("ALTER TABLE distributors DROP CONSTRAINT IF EXISTS check_distributor_name_not_empty;")
    
    # Eliminar constraints de transacciones
    op.execute("ALTER TABLE point_of_sale_transactions DROP CONSTRAINT IF EXISTS check_transaction_time_not_future;")
    op.execute("ALTER TABLE point_of_sale_transactions DROP CONSTRAINT IF EXISTS check_total_amount_positive;")
    
    # Eliminar constraints de items de venta
    op.execute("ALTER TABLE point_of_sale_items DROP CONSTRAINT IF EXISTS check_price_at_sale_positive;")
    op.execute("ALTER TABLE point_of_sale_items DROP CONSTRAINT IF EXISTS check_quantity_sold_positive;")
    
    # Eliminar constraints de préstamos
    op.execute("ALTER TABLE consignment_loans DROP CONSTRAINT IF EXISTS check_loan_date_not_future;")
    op.execute("ALTER TABLE consignment_loans DROP CONSTRAINT IF EXISTS check_return_date_after_loan_date;")
    op.execute("ALTER TABLE consignment_loans DROP CONSTRAINT IF EXISTS check_quantity_loaned_positive;")
    
    # Eliminar constraints de reportes
    op.execute("ALTER TABLE consignment_reports DROP CONSTRAINT IF EXISTS check_report_date_not_future;")
    op.execute("ALTER TABLE consignment_reports DROP CONSTRAINT IF EXISTS check_quantities_not_both_zero;")
    op.execute("ALTER TABLE consignment_reports DROP CONSTRAINT IF EXISTS check_quantity_returned_non_negative;")
    op.execute("ALTER TABLE consignment_reports DROP CONSTRAINT IF EXISTS check_quantity_sold_non_negative;")