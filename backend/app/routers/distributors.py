from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user

router = APIRouter()

@router.post("/distributors/", response_model=schemas.Distributor, dependencies=[Depends(get_current_admin_user)])
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