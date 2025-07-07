"""add_database_indexes_optimization

Revision ID: 001
Revises: 
Create Date: 2025-07-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Agrega índices para optimización de consultas frecuentes"""
    
    # Índices simples en campos específicos
    op.create_index('ix_products_sku', 'products', ['sku'])
    op.create_index('ix_products_description', 'products', ['description'])
    op.create_index('ix_products_selling_price', 'products', ['selling_price'])
    op.create_index('ix_products_stock_quantity', 'products', ['stock_quantity'])
    
    op.create_index('ix_distributors_name', 'distributors', ['name'])
    op.create_index('ix_distributors_phone_number', 'distributors', ['phone_number'])
    op.create_index('ix_distributors_access_code', 'distributors', ['access_code'])
    
    op.create_index('ix_point_of_sale_transactions_user_id', 'point_of_sale_transactions', ['user_id'])
    op.create_index('ix_point_of_sale_transactions_transaction_time', 'point_of_sale_transactions', ['transaction_time'])
    op.create_index('ix_point_of_sale_transactions_total_amount', 'point_of_sale_transactions', ['total_amount'])
    
    op.create_index('ix_point_of_sale_items_transaction_id', 'point_of_sale_items', ['transaction_id'])
    op.create_index('ix_point_of_sale_items_product_id', 'point_of_sale_items', ['product_id'])
    
    op.create_index('ix_consignment_loans_distributor_id', 'consignment_loans', ['distributor_id'])
    op.create_index('ix_consignment_loans_product_id', 'consignment_loans', ['product_id'])
    op.create_index('ix_consignment_loans_loan_date', 'consignment_loans', ['loan_date'])
    op.create_index('ix_consignment_loans_return_due_date', 'consignment_loans', ['return_due_date'])
    op.create_index('ix_consignment_loans_status', 'consignment_loans', ['status'])
    
    op.create_index('ix_consignment_reports_loan_id', 'consignment_reports', ['loan_id'])
    op.create_index('ix_consignment_reports_report_date', 'consignment_reports', ['report_date'])
    
    # Índices compuestos para consultas frecuentes
    op.create_index('idx_product_name_stock', 'products', ['name', 'stock_quantity'])
    op.create_index('idx_transaction_user_date', 'point_of_sale_transactions', ['user_id', 'transaction_time'])
    op.create_index('idx_sale_item_transaction_product', 'point_of_sale_items', ['transaction_id', 'product_id'])
    op.create_index('idx_loan_distributor_status', 'consignment_loans', ['distributor_id', 'status'])
    op.create_index('idx_loan_due_date_status', 'consignment_loans', ['return_due_date', 'status'])
    op.create_index('idx_report_loan_date', 'consignment_reports', ['loan_id', 'report_date'])


def downgrade():
    """Elimina los índices agregados en upgrade()"""
    
    # Eliminar índices compuestos
    op.drop_index('idx_report_loan_date', table_name='consignment_reports')
    op.drop_index('idx_loan_due_date_status', table_name='consignment_loans')
    op.drop_index('idx_loan_distributor_status', table_name='consignment_loans')
    op.drop_index('idx_sale_item_transaction_product', table_name='point_of_sale_items')
    op.drop_index('idx_transaction_user_date', table_name='point_of_sale_transactions')
    op.drop_index('idx_product_name_stock', table_name='products')
    
    # Eliminar índices simples
    op.drop_index('ix_consignment_reports_report_date', table_name='consignment_reports')
    op.drop_index('ix_consignment_reports_loan_id', table_name='consignment_reports')
    
    op.drop_index('ix_consignment_loans_status', table_name='consignment_loans')
    op.drop_index('ix_consignment_loans_return_due_date', table_name='consignment_loans')
    op.drop_index('ix_consignment_loans_loan_date', table_name='consignment_loans')
    op.drop_index('ix_consignment_loans_product_id', table_name='consignment_loans')
    op.drop_index('ix_consignment_loans_distributor_id', table_name='consignment_loans')
    
    op.drop_index('ix_point_of_sale_items_product_id', table_name='point_of_sale_items')
    op.drop_index('ix_point_of_sale_items_transaction_id', table_name='point_of_sale_items')
    
    op.drop_index('ix_point_of_sale_transactions_total_amount', table_name='point_of_sale_transactions')
    op.drop_index('ix_point_of_sale_transactions_transaction_time', table_name='point_of_sale_transactions')
    op.drop_index('ix_point_of_sale_transactions_user_id', table_name='point_of_sale_transactions')
    
    op.drop_index('ix_distributors_access_code', table_name='distributors')
    op.drop_index('ix_distributors_phone_number', table_name='distributors')
    op.drop_index('ix_distributors_name', table_name='distributors')
    
    op.drop_index('ix_products_stock_quantity', table_name='products')
    op.drop_index('ix_products_selling_price', table_name='products')
    op.drop_index('ix_products_description', table_name='products')
    op.drop_index('ix_products_sku', table_name='products')