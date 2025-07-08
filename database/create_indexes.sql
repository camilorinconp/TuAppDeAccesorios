-- ============================================
-- ÍNDICES OPTIMIZADOS PARA TUAPPDEACCESORIOS
-- ============================================
-- Ejecutar después de migration inicial para mejorar performance

-- ============================================
-- ÍNDICES PARA USUARIOS
-- ============================================
-- Login frecuente por email
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Compound index para autenticación
CREATE INDEX IF NOT EXISTS idx_users_auth ON users(email, is_active) WHERE is_active = true;

-- ============================================
-- ÍNDICES PARA PRODUCTOS
-- ============================================
-- Búsquedas más frecuentes
CREATE INDEX IF NOT EXISTS idx_products_name ON products USING gin(to_tsvector('spanish', name));
CREATE INDEX IF NOT EXISTS idx_products_name_simple ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_code ON products(code);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active) WHERE is_active = true;

-- Búsquedas por categoría y marca
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);

-- Compound indexes para filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_products_active_category ON products(is_active, category) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_products_active_stock ON products(is_active, stock_quantity) WHERE is_active = true;

-- Índice para búsqueda de texto completo
CREATE INDEX IF NOT EXISTS idx_products_search ON products USING gin(
    to_tsvector('spanish', name || ' ' || COALESCE(description, '') || ' ' || COALESCE(brand, ''))
);

-- ============================================
-- ÍNDICES PARA DISTRIBUIDORES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_distributors_name ON distributors(name);
CREATE INDEX IF NOT EXISTS idx_distributors_active ON distributors(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_distributors_email ON distributors(email);

-- ============================================
-- ÍNDICES PARA TRANSACCIONES DE VENTAS
-- ============================================
-- Búsquedas por fecha (muy frecuentes en reportes)
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_date_desc ON sales_transactions(sale_date DESC);

-- Búsquedas por usuario vendedor
CREATE INDEX IF NOT EXISTS idx_sales_user ON sales_transactions(user_id);

-- Compound index para reportes por período
CREATE INDEX IF NOT EXISTS idx_sales_date_user ON sales_transactions(sale_date, user_id);
CREATE INDEX IF NOT EXISTS idx_sales_date_total ON sales_transactions(sale_date, total_amount);

-- Índice para búsquedas recientes
CREATE INDEX IF NOT EXISTS idx_sales_recent ON sales_transactions(sale_date DESC, id DESC) 
WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days';

-- ============================================
-- ÍNDICES PARA ÍTEMS DE VENTA
-- ============================================
-- Relaciones frecuentes
CREATE INDEX IF NOT EXISTS idx_sale_items_transaction ON sale_items(transaction_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);

-- Compound index para análisis de productos vendidos
CREATE INDEX IF NOT EXISTS idx_sale_items_product_date ON sale_items(product_id, created_at);

-- ============================================
-- ÍNDICES PARA CONSIGNACIONES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_consignments_distributor ON consignments(distributor_id);
CREATE INDEX IF NOT EXISTS idx_consignments_status ON consignments(status);
CREATE INDEX IF NOT EXISTS idx_consignments_date ON consignments(created_at);

-- Compound index para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_consignments_status_date ON consignments(status, created_at);

-- ============================================
-- ÍNDICES PARA PRODUCTOS EN CONSIGNACIÓN
-- ============================================
CREATE INDEX IF NOT EXISTS idx_consignment_products_consignment ON consignment_products(consignment_id);
CREATE INDEX IF NOT EXISTS idx_consignment_products_product ON consignment_products(product_id);

-- ============================================
-- ÍNDICES PARA AUDITORÍA (SI EXISTE)
-- ============================================
-- Nota: Estos índices son opcionales y dependen de si tienes tabla de auditoría
-- CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
-- CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
-- CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
-- CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_logs(table_name);

-- ============================================
-- ESTADÍSTICAS Y MANTENIMIENTO
-- ============================================
-- Actualizar estadísticas después de crear índices
ANALYZE;

-- ============================================
-- VERIFICACIÓN DE ÍNDICES
-- ============================================
-- Query para verificar que los índices se crearon correctamente
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;