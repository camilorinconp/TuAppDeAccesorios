from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user, get_current_distributor

router = APIRouter()

@router.get("/consignments/loans", response_model=List[schemas.ConsignmentLoan])
def get_all_loans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Obtiene todos los préstamos para administradores"""
    return crud.get_all_consignment_loans(db, skip=skip, limit=limit)

@router.post("/consignments/loans", response_model=schemas.ConsignmentLoan)
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

@router.put("/consignments/loans/{loan_id}/confirm")
def confirm_loan(loan_id: int, db: Session = Depends(get_db)):
    """Confirma un préstamo y mueve productos a consignación"""
    try:
        from ..services.consignment_service import ConsignmentService
        service = ConsignmentService(db)
        success = service.confirm_consignment_loan(loan_id)
        return {"success": success, "message": "Préstamo confirmado y productos movidos a consignación"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.put("/consignments/loans/{loan_id}/cancel")
def cancel_loan(loan_id: int, reason: str = None, db: Session = Depends(get_db)):
    """Cancela un préstamo pendiente"""
    try:
        from ..services.consignment_service import ConsignmentService
        service = ConsignmentService(db)
        success = service.cancel_consignment_loan(loan_id, reason)
        return {"success": success, "message": "Préstamo cancelado"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/consignments/loans/{loan_id}/summary")
def get_loan_summary(loan_id: int, db: Session = Depends(get_db)):
    """Obtiene resumen completo de un préstamo"""
    try:
        from ..services.consignment_service import ConsignmentService
        service = ConsignmentService(db)
        summary = service.get_loan_summary(loan_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.post("/consignments/loans/{loan_id}/reports", response_model=schemas.ConsignmentReport)
def create_loan_report(
    loan_id: int,
    report: schemas.ConsignmentReportCreate,
    db: Session = Depends(get_db)
):
    """Crea un reporte para un préstamo específico (admin)"""
    try:
        from ..services.consignment_service import ConsignmentService
        service = ConsignmentService(db)
        db_report = service.create_consignment_report(
            loan_id=loan_id,
            report_date=report.report_date,
            quantity_sold=report.quantity_sold,
            quantity_returned=report.quantity_returned,
            selling_price_at_report=report.selling_price_at_report,
            distributor_commission=report.distributor_commission,
            notes=report.notes,
            is_final_report=getattr(report, 'is_final_report', False)
        )
        return db_report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")