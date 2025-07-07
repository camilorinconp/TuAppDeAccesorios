from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user, get_current_sales_staff_user

router = APIRouter(prefix="/reports", tags=["reports"])

# Schemas para reportes
class SalesSummary(schemas.BaseModel):
    date: date
    total_transactions: int
    total_sales: float

class TopSellingProduct(schemas.BaseModel):
    product: schemas.Product
    total_sold: int
    total_revenue: float

class LowStockProduct(schemas.BaseModel):
    product: schemas.Product
    days_until_stockout: Optional[int] = None

@router.get("/sales-summary", response_model=List[SalesSummary])
async def get_sales_summary(
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_sales_staff_user)
):
    """Obtiene resumen de ventas por día en un rango de fechas"""
    if not start_date:
        start_date = date.today() - timedelta(days=30)  # Últimos 30 días por defecto
    if not end_date:
        end_date = date.today()
    
    # Convertir a datetime para la consulta
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    summary = crud.get_sales_summary_by_date_range(db, start_datetime, end_datetime)
    
    return [
        SalesSummary(
            date=item.date,
            total_transactions=item.total_transactions,
            total_sales=float(item.total_sales or 0)
        )
        for item in summary
    ]

@router.get("/top-selling-products", response_model=List[TopSellingProduct])
async def get_top_selling_products(
    limit: int = Query(10, ge=1, le=50, description="Número de productos a retornar"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_sales_staff_user)
):
    """Obtiene los productos más vendidos"""
    start_datetime = None
    end_datetime = None
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
    
    top_products = crud.get_top_selling_products(db, limit, start_datetime, end_datetime)
    
    return [
        TopSellingProduct(
            product=item[0],  # Product object
            total_sold=item[1],  # total_sold
            total_revenue=float(item[2] or 0)  # total_revenue
        )
        for item in top_products
    ]

@router.get("/low-stock-products", response_model=List[schemas.Product])
async def get_low_stock_products(
    threshold: int = Query(5, ge=0, le=100, description="Umbral de stock bajo"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_sales_staff_user)
):
    """Obtiene productos con stock bajo"""
    return crud.get_products_with_low_stock(db, threshold)

@router.get("/overdue-loans", response_model=List[schemas.ConsignmentLoan])
async def get_overdue_loans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Obtiene préstamos vencidos"""
    return crud.get_overdue_loans(db)

@router.get("/sales-by-user")
async def get_sales_by_user(
    user_id: Optional[int] = Query(None, description="ID del usuario"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio"),
    end_date: Optional[date] = Query(None, description="Fecha de fin"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_sales_staff_user)
):
    """Obtiene ventas por usuario con paginación"""
    sales = crud.get_sales_with_details(db, skip, limit, user_id)
    
    # Filtrar por fechas si se proporcionan
    if start_date or end_date:
        filtered_sales = []
        for sale in sales:
            sale_date = sale.transaction_time.date()
            if start_date and sale_date < start_date:
                continue
            if end_date and sale_date > end_date:
                continue
            filtered_sales.append(sale)
        sales = filtered_sales
    
    return sales

@router.get("/inventory-status")
async def get_inventory_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_sales_staff_user)
):
    """Obtiene estado general del inventario"""
    # Productos con stock bajo
    low_stock = crud.get_products_with_low_stock(db, 5)
    
    # Productos sin stock
    no_stock = crud.get_products_with_low_stock(db, 0)
    
    # Total de productos
    total_products = crud.get_products_count(db)
    
    # Valor total del inventario
    products = crud.get_products(db, 0, 10000)  # Obtener todos los productos
    total_inventory_value = sum(p.cost_price * p.stock_quantity for p in products)
    total_retail_value = sum(p.selling_price * p.stock_quantity for p in products)
    
    return {
        "total_products": total_products,
        "low_stock_count": len(low_stock),
        "no_stock_count": len(no_stock),
        "total_inventory_cost_value": float(total_inventory_value),
        "total_inventory_retail_value": float(total_retail_value),
        "low_stock_products": low_stock,
        "no_stock_products": no_stock
    }