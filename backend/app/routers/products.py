from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import re

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_admin_user
from ..metrics import business_metrics
from ..logging_config import get_secure_logger
from ..security.input_validation import InputValidator, validate_query_param

router = APIRouter()
logger = get_secure_logger(__name__)

@router.post("/products/", response_model=schemas.Product, dependencies=[Depends(get_current_admin_user)])
def create_product(product: schemas.ProductCreate, request: Request, db: Session = Depends(get_db)):
    """Crear un nuevo producto con validación robusta"""
    
    # Validar y sanitizar inputs
    try:
        # Validar nombre del producto
        if product.name:
            product.name = InputValidator.validate_input(product.name, 'name', max_length=255)
        
        # Validar SKU
        if product.sku:
            product.sku = InputValidator.validate_input(product.sku, 'sku', max_length=50)
        
        # Validar descripción
        if product.description:
            product.description = InputValidator.validate_input(product.description, 'description', max_length=1000)
        
        # Validar categoría
        if product.category:
            product.category = InputValidator.validate_input(product.category, 'name', max_length=100)
        
        # Validaciones de negocio
        if product.selling_price <= 0:
            raise HTTPException(status_code=400, detail="El precio de venta debe ser mayor a 0")
        
        if product.cost_price < 0:
            raise HTTPException(status_code=400, detail="El precio de costo no puede ser negativo")
        
        if product.stock_quantity < 0:
            raise HTTPException(status_code=400, detail="La cantidad en stock no puede ser negativa")
        
    except HTTPException as e:
        logger.warning(
            f"Invalid product data provided",
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent"),
            error_detail=e.detail
        )
        raise e
    except Exception as e:
        logger.error(f"Error validating product data: {e}")
        raise HTTPException(status_code=400, detail="Datos del producto inválidos")
    
    # Crear producto
    db_product = crud.create_product(db=db, product=product)
    
    # Registrar métricas de negocio
    business_metrics.record_product_created()
    
    # Log de auditoría
    logger.business(
        "product_created",
        product_id=db_product.id,
        product_name=db_product.name,
        product_sku=db_product.sku,
        stock_quantity=db_product.stock_quantity,
        selling_price=float(db_product.selling_price)
    )
    
    return db_product

@router.get("/products/", response_model=schemas.ProductList)
def read_products(
    skip: int = Query(0, ge=0, description="Número de productos a omitir"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de productos por página"),
    db: Session = Depends(get_db)
):
    products = crud.get_products(db, skip=skip, limit=limit)
    total = crud.get_products_count(db)
    return {
        "products": products,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_next": skip + limit < total
    }

@router.get("/products/search", response_model=List[schemas.Product])
def search_products(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    use_fulltext: bool = Query(True, description="Usar búsqueda full-text avanzada"),
    db: Session = Depends(get_db)
):
    """Buscar productos por nombre o SKU con full-text search y seguridad anti-SQL injection"""
    
    if use_fulltext:
        # Usar búsqueda full-text avanzada
        from ..utils.search import search_products_fulltext
        products = search_products_fulltext(db, query=q, limit=limit)
    else:
        # Usar búsqueda con métricas (método anterior)
        products = crud.search_products_with_metrics(db, query=q, limit=limit)
    
    return products

@router.get("/products/check-sku/{sku}")
def check_sku_availability(sku: str, db: Session = Depends(get_db)):
    """Verificar si un SKU ya existe en el inventario"""
    # Normalizar el SKU (mayúsculas y sin espacios)
    normalized_sku = sku.strip().upper()
    
    # Buscar producto con este SKU
    existing_product = db.query(models.Product).filter(models.Product.sku == normalized_sku).first()
    
    return {
        "sku": normalized_sku,
        "available": existing_product is None,
        "exists": existing_product is not None,
        "message": "SKU disponible" if existing_product is None else f"SKU '{normalized_sku}' ya existe"
    }

@router.get("/products/suggest-names")
def suggest_product_names(
    q: str = Query(..., min_length=2, description="Término de búsqueda para autocompletado"),
    limit: int = Query(8, ge=1, le=20, description="Número máximo de sugerencias"),
    db: Session = Depends(get_db)
):
    """Obtener sugerencias de nombres de productos para autocompletado"""
    # Validar y sanitizar input para prevenir SQL injection
    from ..security.input_validation import validate_search_term
    
    try:
        search_term = validate_search_term(q.strip(), max_length=50)
    except HTTPException as e:
        raise e
    
    # Buscar productos que contengan el término en el nombre (usando parámetros seguros)
    existing_names = db.query(models.Product.name).filter(
        models.Product.name.ilike(f"%{search_term}%")
    ).distinct().limit(limit).all()
    
    suggestions = [name[0] for name in existing_names]
    
    # Agregar sugerencias comunes basadas en categorías de accesorios
    common_suggestions = get_common_product_suggestions(search_term)
    
    # Combinar y eliminar duplicados manteniendo el orden
    all_suggestions = suggestions + [s for s in common_suggestions if s not in suggestions]
    
    return {
        "query": q,
        "suggestions": all_suggestions[:limit]
    }

def get_common_product_suggestions(search_term: str) -> list[str]:
    """Obtener sugerencias comunes basadas en categorías de accesorios para celulares"""
    
    # Diccionario de categorías y productos comunes
    categories = {
        "funda": [
            "Funda iPhone 14", "Funda iPhone 13", "Funda iPhone 12", "Funda Samsung Galaxy",
            "Funda Transparente", "Funda con Soporte", "Funda Cuero", "Funda Silicona"
        ],
        "case": [
            "Case iPhone 14", "Case iPhone 13", "Case Samsung", "Case Transparente",
            "Case con Soporte", "Case Protector"
        ],
        "protector": [
            "Protector Pantalla", "Protector Templado", "Protector iPhone", "Protector Samsung",
            "Protector Cámara", "Protector Privacidad"
        ],
        "cargador": [
            "Cargador iPhone", "Cargador Samsung", "Cargador Rápido", "Cargador Inalámbrico",
            "Cargador USB-C", "Cargador Lightning", "Cargador Portátil"
        ],
        "cable": [
            "Cable USB-C", "Cable Lightning", "Cable Micro USB", "Cable Carga Rápida",
            "Cable iPhone", "Cable Samsung", "Cable Datos"
        ],
        "audífono": [
            "Audífonos Bluetooth", "Audífonos Inalámbricos", "Audífonos iPhone",
            "Audífonos Samsung", "Audífonos Gaming", "Audífonos Deportivos"
        ],
        "auricular": [
            "Auriculares Bluetooth", "Auriculares Inalámbricos", "Auriculares Gaming",
            "Auriculares Deportivos", "Auriculares con Micrófono"
        ],
        "soporte": [
            "Soporte Celular", "Soporte Auto", "Soporte Mesa", "Soporte Anillo",
            "Soporte Magnético", "Soporte Escritorio"
        ],
        "batería": [
            "Batería Externa", "Batería Portátil", "Power Bank", "Batería iPhone",
            "Batería Samsung", "Batería Inalámbrica"
        ],
        "memoria": [
            "Memoria USB", "Memoria MicroSD", "Memoria Externa", "Tarjeta SD"
        ],
        "adaptador": [
            "Adaptador USB-C", "Adaptador Lightning", "Adaptador Audio",
            "Adaptador Carga", "Adaptador OTG"
        ],
        "mouse": [
            "Mouse Inalámbrico", "Mouse Bluetooth", "Mouse Gaming", "Mouse Óptico",
            "Mouse Portátil", "Mouse Ergonómico"
        ],
        "teclado": [
            "Teclado Bluetooth", "Teclado Inalámbrico", "Teclado Gaming",
            "Teclado Mecánico", "Teclado Portátil"
        ]
    }
    
    suggestions = []
    
    # Buscar en todas las categorías
    for category, items in categories.items():
        if category in search_term or search_term in category:
            suggestions.extend(items)
    
    # También buscar por coincidencias parciales en los nombres
    for category, items in categories.items():
        for item in items:
            if search_term in item.lower():
                suggestions.append(item)
    
    # Eliminar duplicados manteniendo el orden
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)
    
    return unique_suggestions[:8]

@router.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.put("/products/{product_id}", response_model=schemas.Product, dependencies=[Depends(get_current_admin_user)])
def update_product(product_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_product = crud.update_product(db, product_id, product)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Registrar métricas de negocio
    business_metrics.record_product_updated()
    
    # Log de auditoría
    logger.business(
        "product_updated",
        product_id=db_product.id,
        product_name=db_product.name,
        product_sku=db_product.sku,
        stock_quantity=db_product.stock_quantity,
        selling_price=float(db_product.selling_price)
    )
    
    return db_product