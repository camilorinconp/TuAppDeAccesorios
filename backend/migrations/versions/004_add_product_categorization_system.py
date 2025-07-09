"""add_product_categorization_system

Revision ID: 004
Revises: 893df3c2c41b
Create Date: 2025-07-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '893df3c2c41b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add product categorization system with categories, brands, and metadata."""
    
    # 1. Add categorization columns to products table
    with op.batch_alter_table('products', schema=None) as batch_op:
        # Add category column with default value
        batch_op.add_column(sa.Column('category', sa.String(), nullable=False, server_default='otros'))
        
        # Add subcategory for more specific classification
        batch_op.add_column(sa.Column('subcategory', sa.String(), nullable=True))
        
        # Add brand information
        batch_op.add_column(sa.Column('brand', sa.String(), nullable=True))
        
        # Add tags for additional search capabilities (comma-separated)
        batch_op.add_column(sa.Column('tags', sa.String(), nullable=True))
        
        # Add timestamp metadata
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # 2. Create indexes for better performance
    # Category index for filtering
    op.create_index('idx_products_category', 'products', ['category'])
    
    # Subcategory index
    op.create_index('idx_products_subcategory', 'products', ['subcategory'])
    
    # Brand index for filtering and sorting
    op.create_index('idx_products_brand', 'products', ['brand'])
    
    # Timestamp indexes for sorting and analytics
    op.create_index('idx_products_created_at', 'products', ['created_at'])
    op.create_index('idx_products_updated_at', 'products', ['updated_at'])
    
    # 3. Create composite indexes for complex queries
    # Category + Brand for advanced filtering
    op.create_index('idx_products_category_brand', 'products', ['category', 'brand'])
    
    # Category + Stock for inventory management
    op.create_index('idx_products_category_stock', 'products', ['category', 'stock_quantity'])
    
    # Category + Price for price-based filtering
    op.create_index('idx_products_category_price', 'products', ['category', 'selling_price'])
    
    # Brand + Name for brand-specific searches
    op.create_index('idx_products_brand_name', 'products', ['brand', 'name'])
    
    # 4. Update existing products with default category values
    # This ensures all existing products have a valid category
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE products SET category = 'otros' WHERE category IS NULL"))


def downgrade() -> None:
    """Remove product categorization system."""
    
    # 1. Drop composite indexes first
    op.drop_index('idx_products_brand_name', table_name='products')
    op.drop_index('idx_products_category_price', table_name='products')
    op.drop_index('idx_products_category_stock', table_name='products')
    op.drop_index('idx_products_category_brand', table_name='products')
    
    # 2. Drop simple indexes
    op.drop_index('idx_products_updated_at', table_name='products')
    op.drop_index('idx_products_created_at', table_name='products')
    op.drop_index('idx_products_brand', table_name='products')
    op.drop_index('idx_products_subcategory', table_name='products')
    op.drop_index('idx_products_category', table_name='products')
    
    # 3. Remove categorization columns
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('tags')
        batch_op.drop_column('brand')
        batch_op.drop_column('subcategory')
        batch_op.drop_column('category')