"""
Sistema de paginación optimizado para TuAppDeAccesorios
"""
from typing import Generic, TypeVar, List, Optional, Dict, Any
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from math import ceil

T = TypeVar('T')

class PaginationParams:
    """Parámetros estándar de paginación para endpoints"""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número de página (empezando desde 1)"),
        per_page: int = Query(20, ge=1, le=100, description="Elementos por página (máximo 100)"),
        sort_by: Optional[str] = Query(None, description="Campo por el cual ordenar"),
        sort_order: str = Query("asc", regex="^(asc|desc)$", description="Orden: asc o desc")
    ):
        self.page = page
        self.per_page = per_page
        self.sort_by = sort_by
        self.sort_order = sort_order
        
        # Calcular offset
        self.offset = (page - 1) * per_page
        self.limit = per_page

class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada estándar"""
    
    items: List[T] = Field(description="Lista de elementos en la página actual")
    total: int = Field(description="Número total de elementos")
    page: int = Field(description="Página actual")
    per_page: int = Field(description="Elementos por página")
    pages: int = Field(description="Número total de páginas")
    has_next: bool = Field(description="Si existe página siguiente")
    has_prev: bool = Field(description="Si existe página anterior")
    next_page: Optional[int] = Field(description="Número de página siguiente")
    prev_page: Optional[int] = Field(description="Número de página anterior")
    
    class Config:
        from_attributes = True

class PaginationMeta(BaseModel):
    """Metadatos adicionales de paginación"""
    
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
    first_item: int
    last_item: int

def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    per_page: int
) -> PaginatedResponse[T]:
    """Crea una respuesta paginada estándar"""
    
    pages = ceil(total / per_page) if per_page > 0 else 0
    has_next = page < pages
    has_prev = page > 1
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=page + 1 if has_next else None,
        prev_page=page - 1 if has_prev else None
    )

def get_pagination_meta(
    total: int,
    page: int,
    per_page: int
) -> PaginationMeta:
    """Genera metadatos de paginación"""
    
    pages = ceil(total / per_page) if per_page > 0 else 0
    has_next = page < pages
    has_prev = page > 1
    
    first_item = (page - 1) * per_page + 1 if total > 0 else 0
    last_item = min(page * per_page, total)
    
    return PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=page + 1 if has_next else None,
        prev_page=page - 1 if has_prev else None,
        first_item=first_item,
        last_item=last_item
    )

class DatabasePaginator:
    """Paginador optimizado para consultas de base de datos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def paginate_query(
        self,
        query,
        page: int = 1,
        per_page: int = 20,
        count_query=None
    ) -> tuple[List[Any], int]:
        """
        Pagina una query de SQLAlchemy de forma optimizada
        
        Args:
            query: Query de SQLAlchemy
            page: Número de página
            per_page: Elementos por página
            count_query: Query opcional para contar (si es diferente a la query principal)
            
        Returns:
            tuple[items, total_count]
        """
        
        # Calcular offset
        offset = (page - 1) * per_page
        
        # Obtener elementos de la página
        items = query.offset(offset).limit(per_page).all()
        
        # Contar total de elementos
        if count_query is not None:
            total = count_query.scalar()
        else:
            # Usar count() optimizado
            total = query.offset(None).limit(None).count()
        
        return items, total
    
    def paginate_model(
        self,
        model_class,
        page: int = 1,
        per_page: int = 20,
        filters: Optional[Dict] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> tuple[List[Any], int]:
        """
        Pagina un modelo específico con filtros y ordenamiento
        
        Args:
            model_class: Clase del modelo SQLAlchemy
            page: Número de página
            per_page: Elementos por página
            filters: Diccionario de filtros {campo: valor}
            order_by: Campo por el cual ordenar
            order_desc: Si ordenar descendente
            
        Returns:
            tuple[items, total_count]
        """
        
        # Construir query base
        query = self.db.query(model_class)
        
        # Aplicar filtros
        if filters:
            for field, value in filters.items():
                if hasattr(model_class, field) and value is not None:
                    query = query.filter(getattr(model_class, field) == value)
        
        # Query para contar (antes de aplicar ordenamiento y paginación)
        count_query = query.with_entities(func.count(model_class.id))
        total = count_query.scalar()
        
        # Aplicar ordenamiento
        if order_by and hasattr(model_class, order_by):
            order_column = getattr(model_class, order_by)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return items, total

# Funciones de utilidad para endpoints específicos

def paginate_products(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    is_active: bool = True
):
    """Paginación específica para productos con filtros avanzados"""
    
    from .models import Product
    
    query = db.query(Product)
    
    # Filtro por categoría
    if category:
        query = query.filter(Product.category == category)
    
    # Filtro por marca
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    
    # Filtro por rango de precios
    if min_price is not None:
        query = query.filter(Product.selling_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.selling_price <= max_price)
    
    # Filtro por stock
    if in_stock is not None:
        if in_stock:
            query = query.filter(Product.stock_quantity > 0)
        else:
            query = query.filter(Product.stock_quantity == 0)
    
    # Búsqueda por texto (incluye códigos de barras)
    if search:
        search_filter = (
            Product.name.ilike(f"%{search}%") |
            Product.description.ilike(f"%{search}%") |
            Product.sku.ilike(f"%{search}%") |
            Product.brand.ilike(f"%{search}%") |
            Product.subcategory.ilike(f"%{search}%") |
            Product.tags.ilike(f"%{search}%") |
            Product.barcode.ilike(f"%{search}%") |
            Product.internal_code.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Ordenar por categoría, marca y nombre
    query = query.order_by(Product.category.asc(), Product.brand.asc(), Product.name.asc())
    
    # Usar paginador
    paginator = DatabasePaginator(db)
    return paginator.paginate_query(query, page, per_page)

def paginate_sales(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[int] = None
):
    """Paginación específica para ventas con filtros de fecha"""
    
    from .models import SalesTransaction
    from datetime import datetime
    
    query = db.query(SalesTransaction)
    
    # Filtro por rango de fechas
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(SalesTransaction.sale_date >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(SalesTransaction.sale_date <= end_dt)
    
    # Filtro por usuario
    if user_id:
        query = query.filter(SalesTransaction.user_id == user_id)
    
    # Ordenar por fecha más reciente
    query = query.order_by(SalesTransaction.sale_date.desc())
    
    paginator = DatabasePaginator(db)
    return paginator.paginate_query(query, page, per_page)

def paginate_users(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    is_active: Optional[bool] = None,
    role: Optional[str] = None
):
    """Paginación específica para usuarios"""
    
    from .models import User
    
    query = db.query(User)
    
    # Filtro por estado activo
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Filtro por rol
    if role:
        query = query.filter(User.role == role)
    
    # Ordenar por email
    query = query.order_by(User.email.asc())
    
    paginator = DatabasePaginator(db)
    return paginator.paginate_query(query, page, per_page)

# Esquemas de respuesta para endpoints específicos

class PaginatedProductsResponse(BaseModel):
    """Respuesta paginada específica para productos"""
    items: List[Dict[str, Any]]
    meta: PaginationMeta
    filters_applied: Dict[str, Any] = {}

class PaginatedSalesResponse(BaseModel):
    """Respuesta paginada específica para ventas"""
    items: List[Dict[str, Any]]
    meta: PaginationMeta
    summary: Dict[str, Any] = {}  # Totales, promedios, etc.

class PaginatedUsersResponse(BaseModel):
    """Respuesta paginada específica para usuarios"""
    items: List[Dict[str, Any]]
    meta: PaginationMeta
    stats: Dict[str, int] = {}  # Estadísticas de usuarios