from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user, get_current_distributor

router = APIRouter()

@router.get("/consignments/loans", response_model=List[schemas.ConsignmentLoan], dependencies=[Depends(get_current_admin_user)])
def get_all_loans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Obtiene todos los préstamos para administradores"""
    return crud.get_all_consignment_loans(db, skip=skip, limit=limit)

@router.post("/consignments/loans", response_model=schemas.ConsignmentLoan, dependencies=[Depends(get_current_admin_user)])
def create_loan(loan: schemas.ConsignmentLoanCreate, db: Session = Depends(get_db)):
    try:
        db_loan = crud.create_consignment_loan(db, loan)
        return db_loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/distributors/{distributor_id}/loans", response_model=List[schemas.ConsignmentLoan], dependencies=[Depends(get_current_admin_user)])
def get_distributor_loans(distributor_id: int, db: Session = Depends(get_db)):
    loans = crud.get_distributor_loans(db, distributor_id)
    return loans

# Endpoint para que los distribuidores accedan a sus propios préstamos
@router.get("/my-loans", response_model=List[schemas.ConsignmentLoan])
def get_my_loans(
    current_distributor: models.Distributor = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Obtiene los préstamos del distribuidor autenticado"""
    loans = crud.get_distributor_loans(db, current_distributor.id)
    return loans

@router.post("/consignments/reports", response_model=schemas.ConsignmentReport)
def create_report(
    report: schemas.ConsignmentReportCreate, 
    current_distributor: models.Distributor = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Crea un reporte de consignación para un distribuidor autenticado"""
    try:
        db_report = crud.create_consignment_report(db, report)
        return db_report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")