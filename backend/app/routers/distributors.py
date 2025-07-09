from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user

router = APIRouter()

@router.post("/distributors/", response_model=schemas.Distributor)
def create_distributor(distributor: schemas.DistributorCreate, db: Session = Depends(get_db)):
    return crud.create_distributor(db=db, distributor=distributor)

@router.get("/distributors/", response_model=List[schemas.Distributor])
def read_distributors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    distributors = crud.get_distributors(db, skip=skip, limit=limit)
    return distributors

@router.get("/distributors/{distributor_id}", response_model=schemas.Distributor)
def read_distributor(distributor_id: int, db: Session = Depends(get_db)):
    db_distributor = crud.get_distributor(db, distributor_id=distributor_id)
    if db_distributor is None:
        raise HTTPException(status_code=404, detail="Distributor not found")
    return db_distributor

@router.get("/distributors/access-codes/next")
def get_next_access_code(db: Session = Depends(get_db)):
    """Obtiene el próximo código de acceso disponible"""
    try:
        from ..services.access_code_service import AccessCodeService
        service = AccessCodeService(db)
        next_code = service.generate_next_access_code()
        return {"next_code": next_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distributors/access-codes/available")
def get_available_access_codes(limit: int = 10, db: Session = Depends(get_db)):
    """Obtiene una lista de códigos de acceso disponibles"""
    try:
        from ..services.access_code_service import AccessCodeService
        service = AccessCodeService(db)
        codes = service.get_next_available_codes(limit)
        return {"available_codes": codes, "count": len(codes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distributors/access-codes/statistics")
def get_access_code_statistics(db: Session = Depends(get_db)):
    """Obtiene estadísticas de uso de códigos de acceso"""
    try:
        from ..services.access_code_service import AccessCodeService
        service = AccessCodeService(db)
        stats = service.get_usage_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/distributors/access-codes/validate")
def validate_access_code(access_code: str, db: Session = Depends(get_db)):
    """Valida si un código de acceso es válido y está disponible"""
    try:
        from ..services.access_code_service import AccessCodeService
        service = AccessCodeService(db)
        is_valid_format = service.is_valid_access_code_format(access_code)
        is_available = service.is_access_code_available(access_code) if is_valid_format else False
        
        return {
            "access_code": access_code,
            "is_valid_format": is_valid_format,
            "is_available": is_available,
            "is_usable": is_valid_format and is_available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/distributors/{distributor_id}", response_model=schemas.Distributor)
def update_distributor(
    distributor_id: int, 
    distributor: schemas.DistributorUpdate, 
    db: Session = Depends(get_db)
):
    """Actualiza un distribuidor existente"""
    try:
        updated_distributor = crud.update_distributor(db, distributor_id, distributor)
        return updated_distributor
    except crud.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except crud.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.delete("/distributors/{distributor_id}")
def delete_distributor(distributor_id: int, db: Session = Depends(get_db)):
    """Elimina un distribuidor"""
    try:
        success = crud.delete_distributor(db, distributor_id)
        return {"success": success, "message": "Distribuidor eliminado exitosamente"}
    except crud.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except crud.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")