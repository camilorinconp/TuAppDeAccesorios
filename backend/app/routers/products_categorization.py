"""
Endpoints adicionales para categorización de productos
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from .. import crud, schemas, models
from ..models.enums import ProductCategory
from ..dependencies import get_db
from ..pagination import paginate_products, create_paginated_response

router = APIRouter()

@router.get("/products/categories", response_model=List[schemas.CategoryInfo])
async def get_product_categories(db: Session = Depends(get_db)):
    """Obtener información de todas las categorías con conteo de productos"""
    
    # Obtener categorías con conteo
    categories_data = db.query(
        models.Product.category,
        func.count(models.Product.id).label('count')
    ).group_by(models.Product.category).all()
    
    # Mapeo de nombres amigables para categorías
    category_names = {
        'fundas': 'Fundas y Carcasas',
        'cargadores': 'Cargadores',
        'cables': 'Cables',
        'audifonos': 'Audífonos',
        'vidrios': 'Vidrios Templados',
        'soportes': 'Soportes',
        'baterias': 'Baterías Externas',
        'memorias': 'Memorias',
        'limpieza': 'Limpieza',
        'vehiculos': 'Accesorios Vehiculares',
        'otros': 'Otros'
    }
    
    category_descriptions = {
        'fundas': 'Fundas, carcasas y protectores para dispositivos móviles',
        'cargadores': 'Cargadores y cables de poder para diferentes dispositivos',
        'cables': 'Cables USB, datos y conectividad',
        'audifonos': 'Audífonos, auriculares y accesorios de audio',
        'vidrios': 'Protectores de pantalla y vidrios templados',
        'soportes': 'Soportes, bases y accesorios de posicionamiento',
        'baterias': 'Baterías portátiles y power banks',
        'memorias': 'Tarjetas de memoria y dispositivos de almacenamiento',
        'limpieza': 'Kits de limpieza y mantenimiento',
        'vehiculos': 'Accesorios para automóviles y vehículos',
        'otros': 'Otros accesorios y productos diversos'
    }
    
    result = []
    for category, count in categories_data:
        result.append({
            'category': category,
            'name': category_names.get(category, category.title()),
            'count': count,
            'description': category_descriptions.get(category, f'Productos de la categoría {category}')
        })
    
    return result

@router.get("/products/brands", response_model=List[schemas.BrandInfo])
async def get_product_brands(
    category: Optional[ProductCategory] = Query(None, description="Filtrar marcas por categoría"),
    db: Session = Depends(get_db)
):
    """Obtener información de todas las marcas con conteo de productos"""
    
    query = db.query(
        models.Product.brand,
        func.count(models.Product.id).label('count'),
        func.group_concat(distinct(models.Product.category)).label('categories')
    ).filter(models.Product.brand.isnot(None)).group_by(models.Product.brand)
    
    # Filtrar por categoría si se especifica
    if category:
        query = query.filter(models.Product.category == category.value)
    
    brands_data = query.all()
    
    result = []
    for brand, count, categories in brands_data:
        # Procesar categorías (adaptado para SQLite)
        category_list = categories.split(',') if categories else []
        result.append({
            'brand': brand,
            'count': count,
            'categories': category_list
        })
    
    return result

@router.get("/products/filters", response_model=schemas.ProductFiltersResponse)
async def get_product_filters(db: Session = Depends(get_db)):
    """Obtener todos los filtros disponibles para productos"""
    
    # Obtener categorías
    categories_data = db.query(
        models.Product.category,
        func.count(models.Product.id).label('count')
    ).group_by(models.Product.category).all()
    
    # Obtener marcas
    brands_data = db.query(
        models.Product.brand,
        func.count(models.Product.id).label('count'),
        func.group_concat(distinct(models.Product.category)).label('categories')
    ).filter(models.Product.brand.isnot(None)).group_by(models.Product.brand).all()
    
    # Obtener rango de precios
    price_data = db.query(
        func.min(models.Product.selling_price).label('min_price'),
        func.max(models.Product.selling_price).label('max_price'),
        func.avg(models.Product.selling_price).label('avg_price')
    ).first()
    
    # Obtener total de productos
    total_products = db.query(func.count(models.Product.id)).scalar()
    
    # Formatear respuesta
    category_names = {
        'fundas': 'Fundas y Carcasas',
        'cargadores': 'Cargadores',
        'cables': 'Cables',
        'audifonos': 'Audífonos',
        'vidrios': 'Vidrios Templados',
        'soportes': 'Soportes',
        'baterias': 'Baterías Externas',
        'memorias': 'Memorias',
        'limpieza': 'Limpieza',
        'vehiculos': 'Accesorios Vehiculares',
        'otros': 'Otros'
    }
    
    category_descriptions = {
        'fundas': 'Fundas, carcasas y protectores para dispositivos móviles',
        'cargadores': 'Cargadores y cables de poder para diferentes dispositivos',
        'cables': 'Cables USB, datos y conectividad',
        'audifonos': 'Audífonos, auriculares y accesorios de audio',
        'vidrios': 'Protectores de pantalla y vidrios templados',
        'soportes': 'Soportes, bases y accesorios de posicionamiento',
        'baterias': 'Baterías portátiles y power banks',
        'memorias': 'Tarjetas de memoria y dispositivos de almacenamiento',
        'limpieza': 'Kits de limpieza y mantenimiento',
        'vehiculos': 'Accesorios para automóviles y vehículos',
        'otros': 'Otros accesorios y productos diversos'
    }
    
    categories = []
    for category, count in categories_data:
        categories.append({
            'category': category,
            'name': category_names.get(category, category.title()),
            'count': count,
            'description': category_descriptions.get(category, f'Productos de la categoría {category}')
        })
    
    brands = []
    for brand, count, categories_str in brands_data:
        category_list = categories_str.split(',') if categories_str else []
        brands.append({
            'brand': brand,
            'count': count,
            'categories': category_list
        })
    
    return {
        'categories': categories,
        'brands': brands,
        'price_range': {
            'min': float(price_data.min_price) if price_data.min_price else 0,
            'max': float(price_data.max_price) if price_data.max_price else 0,
            'avg': float(price_data.avg_price) if price_data.avg_price else 0
        },
        'total_products': total_products
    }

@router.get("/products/by-category/{category}", response_model=schemas.ProductList)
async def get_products_by_category(
    category: ProductCategory,
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    brand: Optional[str] = Query(None, description="Filtrar por marca"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    db: Session = Depends(get_db)
):
    """Obtener productos filtrados por categoría específica"""
    
    products, total = paginate_products(
        db=db,
        page=page,
        per_page=per_page,
        category=category.value,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        in_stock=True  # Solo productos con stock por defecto
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