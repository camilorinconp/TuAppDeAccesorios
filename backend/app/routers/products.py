from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import re

from .. import crud, schemas, models
from ..models.enums import ProductCategory
from ..dependencies import get_db, get_current_admin_user
from ..metrics import business_metrics
from ..logging_config import get_secure_logger
from ..security.input_validation import validate_search_term
from ..cache_decorators import cache_products_list, cache_product_search, invalidate_products_cache
from ..pagination import PaginationParams, create_paginated_response, paginate_products

router = APIRouter()
logger = get_secure_logger(__name__)

@router.post("/products/", response_model=schemas.Product, dependencies=[Depends(get_current_admin_user)])
def create_product(product: schemas.ProductCreate, request: Request, db: Session = Depends(get_db)):
    """Crear un nuevo producto con validación robusta"""
    
    # Las validaciones de input y sanitización ahora se manejan en el esquema Pydantic (schemas.ProductCreate)
    # Las validaciones de negocio específicas que no son de formato/seguridad se mantienen aquí
    
    # Validaciones de negocio
    
    # 1. Verificar que el SKU no existe
    existing_product = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing_product:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un producto con el SKU '{product.sku}'. Los SKUs deben ser únicos."
        )
    
    # 2. Validar precios
    if product.selling_price <= product.cost_price:
        raise HTTPException(status_code=400, detail="El precio de venta no puede ser menor o igual al precio de costo")
    
    # Crear producto
    db_product = crud.create_product(db=db, product=product)
    
    # Invalidar cache de productos
    try:
        invalidate_products_cache()
    except Exception as e:
        print(f"Error en cache: {e}")
    
    # Registrar métricas de negocio
    try:
        business_metrics.record_product_created()
    except Exception as e:
        print(f"Error en métricas: {e}")
    
    # Log de auditoría (comentado temporalmente para debug)
    # logger.business(
    #     "product_created",
    #     product_id=db_product.id,
    #     product_name=db_product.name,
    #     product_sku=db_product.sku,
    #     stock_quantity=db_product.stock_quantity,
    #     selling_price=float(db_product.selling_price)
    # )
    
    return db_product

@router.post("/products/duplicate/{product_id}", response_model=schemas.Product, dependencies=[Depends(get_current_admin_user)])
async def duplicate_product(
    product_id: int,
    new_sku: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Duplicar un producto existente con nuevo SKU"""
    
    # Validar nuevo SKU
    validated_sku = validate_search_term(new_sku.strip().upper())
    
    # Verificar que el nuevo SKU no existe
    existing_sku = db.query(models.Product).filter(models.Product.sku == validated_sku).first()
    if existing_sku:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un producto con el SKU '{validated_sku}'"
        )
    
    # Obtener producto original
    original_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not original_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Crear nuevo producto con los mismos datos pero nuevo SKU
    new_product_data = schemas.ProductCreate(
        sku=validated_sku,
        name=original_product.name,
        description=original_product.description,
        image_url=original_product.image_url,
        cost_price=original_product.cost_price,
        selling_price=original_product.selling_price,
        stock_quantity=0  # Iniciar con stock 0
    )
    
    # Crear producto
    db_product = crud.create_product(db=db, product=new_product_data)
    
    # Invalidar cache
    try:
        invalidate_products_cache()
    except Exception as e:
        print(f"Error en cache: {e}")
    
    return db_product

@router.get("/products/check-sku/{sku}")
async def check_sku_availability(sku: str, db: Session = Depends(get_db)):
    """Verificar si un SKU está disponible"""
    # Validar SKU con input validator
    validated_sku = validate_search_term(sku.strip().upper())
    
    existing_product = db.query(models.Product).filter(models.Product.sku == validated_sku).first()
    
    return {
        "sku": validated_sku,
        "available": existing_product is None,
        "exists": existing_product is not None,
        "message": "SKU disponible" if existing_product is None else f"SKU '{validated_sku}' ya existe",
        "existing_product": {
            "id": existing_product.id,
            "name": existing_product.name,
            "sku": existing_product.sku
        } if existing_product else None
    }

@router.get("/products/")
@cache_products_list()
async def read_products(
    request: Request,
    page: int = Query(1, ge=1, description="Número de página (empezando desde 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página (máximo 100)"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre, descripción, marca, SKU, código de barras o código interno"),
    category: Optional[ProductCategory] = Query(None, description="Filtrar por categoría"),
    brand: Optional[str] = Query(None, description="Filtrar por marca"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    in_stock: Optional[bool] = Query(None, description="Solo productos con stock"),
    is_active: bool = Query(True, description="Mostrar solo productos activos"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista paginada de productos con filtros y búsqueda optimizada
    """
    
    # Usar paginación optimizada con filtros avanzados
    products, total = paginate_products(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        category=category.value if category else None,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        is_active=is_active
    )
    
    # Convertir a esquemas Pydantic
    products_data = [schemas.Product.from_orm(product) for product in products]
    
    # Crear respuesta paginada
    return create_paginated_response(
        items=products_data,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/products/suggest-names")
@cache_product_search()
async def suggest_product_names(
    request: Request,
    q: str = Query(..., min_length=1, description="Término de búsqueda para autocompletado"),
    limit: int = Query(10, ge=1, le=20, description="Número máximo de sugerencias"),
    db: Session = Depends(get_db)
):
    """Obtener sugerencias de nombres de productos para autocompletado"""
    
    # Validar término de búsqueda
    search_term = validate_search_term(q.strip())
    
    # Buscar productos que coincidan
    products = db.query(models.Product).filter(
        models.Product.name.ilike(f"%{search_term}%")
    ).order_by(models.Product.name.asc()).limit(limit).all()
    
    # Retornar solo nombres únicos para autocompletado simple
    unique_names = set()
    suggestions = []
    for product in products:
        if product.name not in unique_names:
            unique_names.add(product.name)
            suggestions.append(product.name)
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "search_term": search_term
    }

@router.get("/products/search", response_model=List[schemas.Product])
def search_products(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    use_fulltext: bool = Query(True, description="Usar búsqueda full-text avanzada"),
    db: Session = Depends(get_db)
):
    """Buscar productos por nombre o SKU con full-text search y seguridad anti-SQL injection"""
    
    # La validación de 'q' ahora se maneja directamente por Pydantic en el Query
    # y por InputValidator a través de la función validate_search_term si se usa.
    from ..security.input_validation import validate_search_term
    search_term_validated = validate_search_term(q) # Asegura que el término de búsqueda sea seguro

    if use_fulltext:
        # Usar búsqueda full-text avanzada
        from ..utils.search import search_products_fulltext
        products = search_products_fulltext(db, query=search_term_validated, limit=limit)
    else:
        # Usar búsqueda con métricas (método anterior)
        products = crud.search_products_with_metrics(db, query=search_term_validated, limit=limit)
    
    return products

@router.get("/products/search/barcode/{barcode}", response_model=schemas.Product)
def search_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db)
):
    """Buscar producto por código de barras"""
    
    # Validar código de barras
    validated_barcode = validate_search_term(barcode.strip())
    
    # Buscar producto por código de barras
    product = db.query(models.Product).filter(
        models.Product.barcode == validated_barcode
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontró producto con código de barras '{validated_barcode}'"
        )
    
    return product

@router.get("/products/search/internal-code/{internal_code}", response_model=schemas.Product)
def search_product_by_internal_code(
    internal_code: str,
    db: Session = Depends(get_db)
):
    """Buscar producto por código interno"""
    
    # Validar código interno
    validated_code = validate_search_term(internal_code.strip())
    
    # Buscar producto por código interno
    product = db.query(models.Product).filter(
        models.Product.internal_code == validated_code
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontró producto con código interno '{validated_code}'"
        )
    
    return product

@router.post("/products/validate-barcode")
def validate_barcode_availability(
    barcode_data: dict,
    db: Session = Depends(get_db)
):
    """Validar si un código de barras está disponible"""
    
    barcode = barcode_data.get("barcode", "").strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Código de barras requerido")
    
    # Validar formato
    validated_barcode = validate_search_term(barcode)
    
    # Verificar si ya existe
    existing_product = db.query(models.Product).filter(
        models.Product.barcode == validated_barcode
    ).first()
    
    return {
        "barcode": validated_barcode,
        "available": existing_product is None,
        "exists": existing_product is not None,
        "message": "Código de barras disponible" if existing_product is None else f"Código de barras '{validated_barcode}' ya existe",
        "existing_product": {
            "id": existing_product.id,
            "name": existing_product.name,
            "sku": existing_product.sku,
            "barcode": existing_product.barcode
        } if existing_product else None
    }


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
    
    # Log de auditoría (temporalmente deshabilitado - logger.business no existe)
    # logger.business(
    #     "product_updated",
    #     product_id=db_product.id,
    #     product_name=db_product.name,
    #     product_sku=db_product.sku,
    #     stock_quantity=db_product.stock_quantity,
    #     selling_price=float(db_product.selling_price)
    # )
    
    return db_product