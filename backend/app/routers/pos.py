from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_sales_staff_user

router = APIRouter()

@router.post("/pos/sales", response_model=schemas.PointOfSaleTransaction, dependencies=[Depends(get_current_sales_staff_user)])
def create_sale(sale: schemas.PointOfSaleTransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_sales_staff_user)):
    db_sale = crud.create_pos_sale(db, sale, current_user.id)
    if db_sale is None:
        raise HTTPException(status_code=400, detail="Invalid sale data or insufficient stock")
    return db_sale

@router.post("/sales", response_model=schemas.PointOfSaleTransaction)
def create_sale_test(sale: schemas.PointOfSaleTransactionCreate, db: Session = Depends(get_db)):
    """Endpoint temporal para testing sin autenticación"""
    # Usar usuario ID 1 (admin) por defecto para testing
    db_sale = crud.create_pos_sale(db, sale, user_id=1)
    if db_sale is None:
        raise HTTPException(status_code=400, detail="Invalid sale data or insufficient stock")
    return db_sale