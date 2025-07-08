"""improve_consignment_logic_and_inventory_tracking

Revision ID: 893df3c2c41b
Revises: 79a24bab3acc
Create Date: 2025-07-08 09:57:49.636478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '893df3c2c41b'
down_revision: Union[str, Sequence[str], None] = '79a24bab3acc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with improved consignment logic and inventory tracking."""
    
    # 1. Create product_locations table for inventory tracking (simplified for SQLite)
    op.create_table(
        'product_locations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('location_type', sa.String(), nullable=False, index=True),  # warehouse, consignment, sold, returned
        sa.Column('location_id', sa.Integer(), nullable=True, index=True),  # distributor_id for consignment
        sa.Column('quantity', sa.Integer(), nullable=False, default=0, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('reference_type', sa.String(), nullable=True),  # 'loan', 'sale', 'return'
        sa.Column('reference_id', sa.Integer(), nullable=True),  # ID del préstamo/venta relacionado
        sa.Column('notes', sa.String(), nullable=True),
    )
    
    # 2. Add new columns to consignment_loans table (simplified for SQLite)
    op.add_column('consignment_loans', sa.Column('actual_return_date', sa.Date(), nullable=True))
    op.add_column('consignment_loans', sa.Column('max_loan_days', sa.Integer(), nullable=True))
    op.add_column('consignment_loans', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('consignment_loans', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('consignment_loans', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('consignment_loans', sa.Column('quantity_reported', sa.Integer(), nullable=True))
    op.add_column('consignment_loans', sa.Column('quantity_pending', sa.Integer(), nullable=True))
    
    # 3. Add new columns to consignment_reports table (simplified for SQLite)
    op.add_column('consignment_reports', sa.Column('selling_price_at_report', sa.Numeric(10, 2), nullable=True))
    op.add_column('consignment_reports', sa.Column('profit_margin', sa.Numeric(10, 2), nullable=True))
    op.add_column('consignment_reports', sa.Column('distributor_commission', sa.Numeric(10, 2), nullable=True))
    op.add_column('consignment_reports', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('consignment_reports', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('consignment_reports', sa.Column('is_final_report', sa.Boolean(), nullable=True))
    
    # 4. Update default status for consignment_loans to 'pendiente'
    # Note: This will be handled in the application logic since SQLite doesn't support ALTER COLUMN
    
    # 5. Create indices for product_locations
    op.create_index('idx_product_location_type', 'product_locations', ['product_id', 'location_type'])
    op.create_index('idx_location_type_id', 'product_locations', ['location_type', 'location_id'])
    op.create_index('idx_product_location_reference', 'product_locations', ['product_id', 'reference_type', 'reference_id'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove indices
    op.drop_index('idx_product_location_reference', table_name='product_locations')
    op.drop_index('idx_location_type_id', table_name='product_locations')
    op.drop_index('idx_product_location_type', table_name='product_locations')
    
    # Remove columns from consignment_reports
    op.drop_column('consignment_reports', 'is_final_report')
    op.drop_column('consignment_reports', 'notes')
    op.drop_column('consignment_reports', 'created_at')
    op.drop_column('consignment_reports', 'distributor_commission')
    op.drop_column('consignment_reports', 'profit_margin')
    op.drop_column('consignment_reports', 'selling_price_at_report')
    
    # Remove columns from consignment_loans
    op.drop_column('consignment_loans', 'quantity_pending')
    op.drop_column('consignment_loans', 'quantity_reported')
    op.drop_column('consignment_loans', 'updated_at')
    op.drop_column('consignment_loans', 'created_at')
    op.drop_column('consignment_loans', 'notes')
    op.drop_column('consignment_loans', 'max_loan_days')
    op.drop_column('consignment_loans', 'actual_return_date')
    
    # Remove product_locations table
    op.drop_table('product_locations')