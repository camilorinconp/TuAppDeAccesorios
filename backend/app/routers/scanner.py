from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .. import crud, schemas, models
from ..models.enums import LocationType
from ..dependencies import get_db, get_current_admin_user
from ..security.input_validation import validate_search_term

router = APIRouter(prefix="/scanner", tags=["scanner"])

# ==========================================
# SESIONES DE ESCANEO
# ==========================================

@router.post("/sessions", response_model=schemas.ScanSession)
def create_scan_session(
    session_data: schemas.ScanSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Crear nueva sesión de escaneo"""
    
    # Validar que no haya sesiones activas del mismo tipo para el usuario
    existing_session = db.query(models.ScanSession).filter(
        models.ScanSession.user_id == current_user.id,
        models.ScanSession.session_type == session_data.session_type,
        models.ScanSession.status == "active"
    ).first()
    
    if existing_session:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una sesión activa de tipo '{session_data.session_type}'"
        )
    
    # Crear nueva sesión
    db_session = models.ScanSession(
        session_type=session_data.session_type,
        user_id=current_user.id,
        location_type=session_data.location_type,
        location_id=session_data.location_id,
        reference_type=session_data.reference_type,
        reference_id=session_data.reference_id,
        device_info=session_data.device_info,
        notes=session_data.notes
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return db_session

@router.put("/sessions/{session_id}/close")
def close_scan_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Cerrar sesión de escaneo"""
    
    session = db.query(models.ScanSession).filter(
        models.ScanSession.id == session_id,
        models.ScanSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if session.status != "active":
        raise HTTPException(status_code=400, detail="La sesión no está activa")
    
    session.status = "completed"
    session.ended_at = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    return {"message": "Sesión cerrada exitosamente", "session": session}

@router.get("/sessions/active", response_model=List[schemas.ScanSession])
def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Obtener sesiones activas del usuario"""
    
    sessions = db.query(models.ScanSession).filter(
        models.ScanSession.user_id == current_user.id,
        models.ScanSession.status == "active"
    ).all()
    
    return sessions

# ==========================================
# OPERACIONES DE ESCANEO
# ==========================================

@router.post("/scan", response_model=schemas.ScanResponse)
def scan_product(
    scan_request: schemas.ScanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Escanear un producto individual"""
    
    # Validar código de barras
    barcode = validate_search_term(scan_request.barcode.strip())
    
    # Buscar producto por código de barras
    product = db.query(models.Product).filter(
        models.Product.barcode == barcode
    ).first()
    
    if not product:
        # Buscar por código interno como fallback
        product = db.query(models.Product).filter(
            models.Product.internal_code == barcode
        ).first()
    
    if not product:
        return schemas.ScanResponse(
            success=False,
            message=f"Producto no encontrado con código: {barcode}"
        )
    
    # Obtener sesión activa si se proporciona
    session = None
    if scan_request.session_id:
        session = db.query(models.ScanSession).filter(
            models.ScanSession.id == scan_request.session_id,
            models.ScanSession.user_id == current_user.id,
            models.ScanSession.status == "active"
        ).first()
        
        if session:
            session.total_scans += 1
            session.successful_scans += 1
            db.commit()
    
    return schemas.ScanResponse(
        success=True,
        message=f"Producto encontrado: {product.name}",
        product=product,
        session=session
    )

@router.post("/scan/consignment", response_model=schemas.ScanResponse)
def scan_for_consignment(
    scan_request: schemas.ScanRequest,
    action: str,  # 'loan' o 'return'
    distributor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Escanear producto para consignación (préstamo o devolución)"""
    
    if action not in ['loan', 'return']:
        raise HTTPException(status_code=400, detail="Acción debe ser 'loan' o 'return'")
    
    # Validar código de barras
    barcode = validate_search_term(scan_request.barcode.strip())
    
    # Buscar producto
    product = db.query(models.Product).filter(
        models.Product.barcode == barcode
    ).first()
    
    if not product:
        product = db.query(models.Product).filter(
            models.Product.internal_code == barcode
        ).first()
    
    if not product:
        return schemas.ScanResponse(
            success=False,
            message=f"Producto no encontrado con código: {barcode}"
        )
    
    # Validar distribuidor
    distributor = db.query(models.Distributor).filter(
        models.Distributor.id == distributor_id
    ).first()
    
    if not distributor:
        raise HTTPException(status_code=404, detail="Distribuidor no encontrado")
    
    # Crear movimiento de inventario
    movement_type = "out" if action == "loan" else "in"
    from_location = LocationType.warehouse if action == "loan" else LocationType.consignment
    to_location = LocationType.consignment if action == "loan" else LocationType.warehouse
    
    movement = models.InventoryMovement(
        product_id=product.id,
        barcode_scanned=barcode,
        movement_type=movement_type,
        from_location_type=from_location,
        from_location_id=None if action == "loan" else distributor_id,
        to_location_type=to_location,
        to_location_id=distributor_id if action == "loan" else None,
        quantity=scan_request.quantity,
        user_id=current_user.id,
        reference_type="consignment",
        reference_id=distributor_id,
        device_info=scan_request.device_info
    )
    
    db.add(movement)
    
    # Actualizar ubicación del producto
    product_location = db.query(models.ProductLocation).filter(
        models.ProductLocation.product_id == product.id,
        models.ProductLocation.location_type == from_location
    ).first()
    
    if product_location:
        if action == "loan":
            # Mover de bodega a consignación
            product_location.quantity -= scan_request.quantity
            if product_location.quantity <= 0:
                db.delete(product_location)
            
            # Crear nueva ubicación en consignación
            new_location = models.ProductLocation(
                product_id=product.id,
                location_type=LocationType.consignment,
                location_id=distributor_id,
                quantity=scan_request.quantity,
                reference_type="loan",
                reference_id=distributor_id
            )
            db.add(new_location)
        else:
            # Mover de consignación a bodega
            if product_location.location_id == distributor_id:
                product_location.quantity -= scan_request.quantity
                if product_location.quantity <= 0:
                    db.delete(product_location)
            
            # Actualizar bodega
            warehouse_location = db.query(models.ProductLocation).filter(
                models.ProductLocation.product_id == product.id,
                models.ProductLocation.location_type == LocationType.warehouse
            ).first()
            
            if warehouse_location:
                warehouse_location.quantity += scan_request.quantity
            else:
                new_warehouse = models.ProductLocation(
                    product_id=product.id,
                    location_type=LocationType.warehouse,
                    quantity=scan_request.quantity
                )
                db.add(new_warehouse)
    
    # Actualizar sesión si existe
    session = None
    if scan_request.session_id:
        session = db.query(models.ScanSession).filter(
            models.ScanSession.id == scan_request.session_id,
            models.ScanSession.user_id == current_user.id,
            models.ScanSession.status == "active"
        ).first()
        
        if session:
            session.total_scans += 1
            session.successful_scans += 1
    
    db.commit()
    db.refresh(movement)
    
    action_text = "prestado a" if action == "loan" else "devuelto por"
    message = f"Producto {action_text} {distributor.name}: {product.name}"
    
    return schemas.ScanResponse(
        success=True,
        message=message,
        product=product,
        movement=movement,
        session=session
    )

@router.post("/scan/inventory", response_model=schemas.ScanResponse)
def scan_for_inventory(
    scan_request: schemas.ScanRequest,
    movement_type: str,  # 'in', 'out', 'transfer'
    location_type: LocationType,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Escanear producto para movimiento de inventario"""
    
    if movement_type not in ['in', 'out', 'transfer']:
        raise HTTPException(status_code=400, detail="Tipo de movimiento inválido")
    
    # Validar código de barras
    barcode = validate_search_term(scan_request.barcode.strip())
    
    # Buscar producto
    product = db.query(models.Product).filter(
        models.Product.barcode == barcode
    ).first()
    
    if not product:
        product = db.query(models.Product).filter(
            models.Product.internal_code == barcode
        ).first()
    
    if not product:
        return schemas.ScanResponse(
            success=False,
            message=f"Producto no encontrado con código: {barcode}"
        )
    
    # Crear movimiento de inventario
    movement = models.InventoryMovement(
        product_id=product.id,
        barcode_scanned=barcode,
        movement_type=movement_type,
        to_location_type=location_type,
        to_location_id=location_id,
        quantity=scan_request.quantity,
        user_id=current_user.id,
        reference_type="inventory",
        device_info=scan_request.device_info
    )
    
    db.add(movement)
    
    # Actualizar stock del producto si es entrada o salida
    if movement_type == "in":
        product.stock_quantity += scan_request.quantity
    elif movement_type == "out":
        if product.stock_quantity >= scan_request.quantity:
            product.stock_quantity -= scan_request.quantity
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente. Disponible: {product.stock_quantity}"
            )
    
    # Actualizar sesión si existe
    session = None
    if scan_request.session_id:
        session = db.query(models.ScanSession).filter(
            models.ScanSession.id == scan_request.session_id,
            models.ScanSession.user_id == current_user.id,
            models.ScanSession.status == "active"
        ).first()
        
        if session:
            session.total_scans += 1
            session.successful_scans += 1
    
    db.commit()
    db.refresh(movement)
    
    return schemas.ScanResponse(
        success=True,
        message=f"Movimiento de inventario registrado: {movement_type}",
        product=product,
        movement=movement,
        session=session
    )

@router.post("/scan/bulk", response_model=schemas.BulkScanResponse)
def bulk_scan(
    bulk_request: schemas.BulkScanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Escaneo masivo de productos"""
    
    results = []
    successful_scans = 0
    failed_scans = 0
    
    session = None
    if bulk_request.session_id:
        session = db.query(models.ScanSession).filter(
            models.ScanSession.id == bulk_request.session_id,
            models.ScanSession.user_id == current_user.id,
            models.ScanSession.status == "active"
        ).first()
    
    for barcode in bulk_request.barcodes:
        try:
            # Crear request individual
            individual_request = schemas.ScanRequest(
                barcode=barcode,
                session_id=bulk_request.session_id,
                device_info=bulk_request.device_info
            )
            
            # Procesar según tipo de movimiento
            if bulk_request.movement_type == "inventory":
                result = scan_for_inventory(
                    individual_request,
                    "in",  # Por defecto entrada
                    bulk_request.location_type,
                    bulk_request.location_id,
                    db,
                    current_user
                )
            else:
                result = scan_product(individual_request, db, current_user)
            
            results.append(result)
            if result.success:
                successful_scans += 1
            else:
                failed_scans += 1
                
        except Exception as e:
            failed_scans += 1
            results.append(schemas.ScanResponse(
                success=False,
                message=f"Error procesando {barcode}: {str(e)}"
            ))
    
    # Actualizar sesión
    if session:
        session.total_scans += len(bulk_request.barcodes)
        session.successful_scans += successful_scans
        session.failed_scans += failed_scans
        db.commit()
    
    return schemas.BulkScanResponse(
        total_scanned=len(bulk_request.barcodes),
        successful_scans=successful_scans,
        failed_scans=failed_scans,
        results=results,
        session=session
    )

# ==========================================
# REPORTES Y CONSULTAS
# ==========================================

@router.get("/movements", response_model=List[schemas.InventoryMovement])
def get_inventory_movements(
    product_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    location_type: Optional[LocationType] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Obtener movimientos de inventario"""
    
    query = db.query(models.InventoryMovement)
    
    if product_id:
        query = query.filter(models.InventoryMovement.product_id == product_id)
    
    if movement_type:
        query = query.filter(models.InventoryMovement.movement_type == movement_type)
    
    if location_type:
        query = query.filter(models.InventoryMovement.to_location_type == location_type)
    
    movements = query.order_by(
        models.InventoryMovement.timestamp.desc()
    ).limit(limit).all()
    
    return movements

@router.get("/sessions/history", response_model=List[schemas.ScanSession])
def get_scan_sessions_history(
    session_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Obtener historial de sesiones de escaneo"""
    
    query = db.query(models.ScanSession).filter(
        models.ScanSession.user_id == current_user.id
    )
    
    if session_type:
        query = query.filter(models.ScanSession.session_type == session_type)
    
    sessions = query.order_by(
        models.ScanSession.started_at.desc()
    ).limit(limit).all()
    
    return sessions

@router.post("/scan/pos", response_model=schemas.ScanResponse)
def scan_for_pos(
    scan_request: schemas.ScanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Escanear producto para punto de venta"""
    
    # Validar código de barras
    barcode = validate_search_term(scan_request.barcode.strip())
    
    # Buscar producto por código de barras
    product = db.query(models.Product).filter(
        models.Product.barcode == barcode
    ).first()
    
    if not product:
        # Buscar por código interno como fallback
        product = db.query(models.Product).filter(
            models.Product.internal_code == barcode
        ).first()
    
    if not product:
        return schemas.ScanResponse(
            success=False,
            message=f"Producto no encontrado con código: {barcode}"
        )
    
    # Verificar disponibilidad de stock
    if product.stock_quantity <= 0:
        return schemas.ScanResponse(
            success=False,
            message=f"Producto sin stock disponible: {product.name}"
        )
    
    # Verificar si la cantidad solicitada está disponible
    if product.stock_quantity < scan_request.quantity:
        return schemas.ScanResponse(
            success=False,
            message=f"Stock insuficiente. Disponible: {product.stock_quantity}, Solicitado: {scan_request.quantity}"
        )
    
    # Obtener sesión activa si se proporciona
    session = None
    if scan_request.session_id:
        session = db.query(models.ScanSession).filter(
            models.ScanSession.id == scan_request.session_id,
            models.ScanSession.user_id == current_user.id,
            models.ScanSession.status == "active"
        ).first()
        
        if session:
            session.total_scans += 1
            session.successful_scans += 1
            db.commit()
    
    return schemas.ScanResponse(
        success=True,
        message=f"Producto listo para venta: {product.name} - Stock: {product.stock_quantity} - Precio: ${product.selling_price}",
        product=product,
        session=session
    )