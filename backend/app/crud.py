from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_, func, desc, asc
from . import models, schemas
from .exceptions import NotFoundError, DuplicateError, InsufficientStockError, ValidationError
from datetime import datetime
from .utils import security
from .utils.search import search_products_secure, SearchPerformanceTracker
from .cache import cached, CacheConfig, cache_manager # Importar 'cached' y 'CacheConfig'
from .decorators.audit_decorator import audit_create, audit_update, audit_delete, audit_search, audit_sale
from .utils.performance_optimizer import cache_expensive_operation, optimize_db_session, monitor_performance
from .services.intelligent_cache import ProductCacheManager, cache_product_operation
import time

# Funciones CRUD para Product
def get_product(db: Session, product_id: int):
    """Obtiene un producto por ID con caché inteligente"""
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise NotFoundError(f"Producto con ID {product_id} no encontrado")
    return product

def get_products(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene lista de productos con caché inteligente"""
    
    def fetch_products():
        return db.query(models.Product).offset(skip).limit(limit).all()
    
    # Para simplificar, usar directamente la DB por ahora
    return fetch_products()

def get_products_count(db: Session) -> int:
    """Obtiene el número total de productos"""
    return db.query(func.count(models.Product.id)).scalar()

def search_products(db: Session, query: str, limit: int = 10):
    """
    Busca productos por nombre o SKU con seguridad anti-SQL injection
    DEPRECADO: Usar search_products_secure en su lugar
    """
    import warnings
    warnings.warn(
        "search_products está deprecado. Usar search_products_secure para mayor seguridad.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Importar función segura
    from .utils.search import search_products_secure
    return search_products_secure(db, query, limit)


@audit_search(description="Búsqueda de productos con métricas de rendimiento")
@monitor_performance("search_products_with_metrics")
@optimize_db_session  
def search_products_with_metrics(db: Session, query: str, limit: int = 10):
    """
    Búsqueda segura de productos con tracking de métricas de performance
    """
    start_time = time.time()
    
    try:
        results = search_products_secure(db, query, limit)
        execution_time = time.time() - start_time
        
        # Log métricas para monitoreo
        SearchPerformanceTracker.log_search_metrics(
            query=query,
            results_count=len(results),
            execution_time=execution_time
        )
        
        return results
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        # Log error con métricas
        SearchPerformanceTracker.log_search_metrics(
            query=query,
            results_count=0,
            execution_time=execution_time
        )
        
        raise e


def create_product(db: Session, product: schemas.ProductCreate):
    # Validar que no exista un producto con el mismo SKU
    existing_product = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing_product:
        raise DuplicateError(f"❌ SKU duplicado: Ya existe un producto con el código '{product.sku}'. Cada producto debe tener un SKU único en el inventario.")
    
    # Las validaciones de negocio (precios, stock) ahora se manejan en el esquema Pydantic
    
    try:
        db_product = models.Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except Exception as e:
        db.rollback()
        raise ValidationError(f"Error al crear producto: {str(e)}")

def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):
    db_product = get_product(db, product_id)  # Ya lanza NotFoundError si no existe
    
    update_data = product_update.dict(exclude_unset=True)
    
    # Validaciones de negocio
    if 'sku' in update_data:
        existing_product = db.query(models.Product).filter(
            models.Product.sku == update_data['sku'],
            models.Product.id != product_id
        ).first()
        if existing_product:
            raise DuplicateError(f"❌ SKU duplicado: Ya existe otro producto con el código '{update_data['sku']}'. Cada producto debe tener un SKU único en el inventario.")
    
    # Las validaciones de negocio (precios, stock) ahora se manejan en el esquema Pydantic
    
    # Validar que precio de venta >= precio de costo
    new_cost = update_data.get('cost_price', db_product.cost_price)
    new_selling = update_data.get('selling_price', db_product.selling_price)
    if new_selling is not None and new_cost is not None and new_selling < new_cost:
        raise ValidationError("El precio de venta no puede ser menor al precio de costo")
    
    try:
        for key, value in update_data.items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except Exception as e:
        db.rollback()
        raise ValidationError(f"Error al actualizar producto: {str(e)}")

# Funciones CRUD para Distributor
def get_distributor(db: Session, distributor_id: int):
    distributor = db.query(models.Distributor).filter(models.Distributor.id == distributor_id).first()
    if not distributor:
        raise NotFoundError(f"Distribuidor con ID {distributor_id} no encontrado")
    return distributor

def get_distributor_by_name(db: Session, name: str):
    """Obtiene un distribuidor por nombre"""
    return db.query(models.Distributor).filter(models.Distributor.name == name).first()

def get_distributor_by_access_code(db: Session, access_code: str):
    distributor = db.query(models.Distributor).filter(models.Distributor.access_code == access_code).first()
    if not distributor or not security.verify_password(access_code, distributor.access_code):
        raise NotFoundError("Código de acceso o distribuidor incorrecto")
    return distributor

def get_distributors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Distributor).offset(skip).limit(limit).all()

def update_distributor(db: Session, distributor_id: int, distributor_update: schemas.DistributorUpdate):
    from .logging_config import get_secure_logger
    logger = get_secure_logger(__name__)
    
    db_distributor = get_distributor(db, distributor_id)  # Ya lanza NotFoundError si no existe
    
    update_data = distributor_update.dict(exclude_unset=True)
    
    try:
        # Actualizar campos
        for key, value in update_data.items():
            if key == 'access_code' and value:
                # Si se actualiza el código de acceso, hashearlo
                value = security.get_password_hash(value)
            setattr(db_distributor, key, value)
        
        db.commit()
        db.refresh(db_distributor)
        
        # Invalidar caché de distribuidores
        cache_manager.delete_pattern("cache:distributors:*")
        
        logger.info(f"Distribuidor actualizado: {db_distributor.name} (ID: {distributor_id})")
        return db_distributor
        
    except Exception as e:
        db.rollback()
        raise ValidationError(f"Error al actualizar distribuidor: {str(e)}")

def delete_distributor(db: Session, distributor_id: int):
    from .logging_config import get_secure_logger
    logger = get_secure_logger(__name__)
    
    db_distributor = get_distributor(db, distributor_id)  # Ya lanza NotFoundError si no existe
    
    # Verificar si el distribuidor tiene préstamos activos
    active_loans = db.query(models.ConsignmentLoan).filter(
        models.ConsignmentLoan.distributor_id == distributor_id,
        models.ConsignmentLoan.status.in_([
            models.LoanStatus.pendiente,
            models.LoanStatus.en_prestamo,
            models.LoanStatus.parcialmente_devuelto,
            models.LoanStatus.vencido
        ])
    ).first()
    
    if active_loans:
        raise ValidationError(
            f"No se puede eliminar el distribuidor '{db_distributor.name}' porque tiene préstamos activos. "
            "Debe completar o cancelar todos los préstamos antes de eliminar el distribuidor."
        )
    
    try:
        distributor_name = db_distributor.name
        db.delete(db_distributor)
        db.commit()
        
        # Invalidar caché de distribuidores
        cache_manager.delete_pattern("cache:distributors:*")
        
        logger.info(f"Distribuidor eliminado: {distributor_name} (ID: {distributor_id})")
        return True
        
    except Exception as e:
        db.rollback()
        raise ValidationError(f"Error al eliminar distribuidor: {str(e)}")

def create_distributor(db: Session, distributor: schemas.DistributorCreate):
    from .services.access_code_service import AccessCodeService
    from .logging_config import get_secure_logger
    logger = get_secure_logger(__name__)
    
    # Generar código de acceso automáticamente
    access_code_service = AccessCodeService(db)
    generated_access_code = access_code_service.generate_next_access_code()
    
    # Preparar datos del distribuidor
    distributor_data = distributor.dict()
    
    # Si se proporcionó un access_code, validar que tenga el formato correcto
    # Si no, usar el generado automáticamente
    if hasattr(distributor, 'access_code') and distributor.access_code:
        if not access_code_service.is_valid_access_code_format(distributor.access_code):
            raise ValidationError(f"El código de acceso debe tener el formato BGA + 4 dígitos (ej: BGA0001)")
        if not access_code_service.is_access_code_available(distributor.access_code):
            raise ValidationError(f"El código de acceso {distributor.access_code} ya está en uso")
        generated_access_code = distributor.access_code
    
    # Hashear el access_code antes de guardarlo
    distributor_data['access_code'] = security.get_password_hash(generated_access_code)
    
    db_distributor = models.Distributor(**distributor_data)
    db.add(db_distributor)
    db.commit()
    db.refresh(db_distributor)
    
    # Registrar el código en la tabla de tracking
    access_code_service.register_access_code(generated_access_code, db_distributor.id)
    
    # Invalidar caché de distribuidores
    cache_manager.delete_pattern("cache:distributors:*")
    
    # Log del código generado (antes de hashearlo)
    logger.info(f"Distribuidor creado: {db_distributor.name}, Código: {generated_access_code}")
    
    return db_distributor

# Funciones CRUD para User
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise NotFoundError(f"Usuario '{username}' no encontrado")
    return user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Funciones para Ventas
def create_pos_sale(db: Session, sale: schemas.PointOfSaleTransactionCreate, user_id: int):
    # Validaciones iniciales
    if not sale.items:
        raise ValidationError("La venta debe tener al menos un producto")
    
    # Cargar todos los productos de una vez para evitar consultas múltiples
    product_ids = [item.product_id for item in sale.items]
    products = db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()
    products_dict = {p.id: p for p in products}
    
    # Verificar que todos los productos existen
    missing_products = set(product_ids) - set(products_dict.keys())
    if missing_products:
        raise NotFoundError(f"Productos no encontrados: {missing_products}")
    
    total_amount = 0
    insufficient_stock_items = []
    
    # Validar stock y calcular total
    for item in sale.items:
        if item.quantity_sold <= 0:
            raise ValidationError(f"La cantidad debe ser mayor a 0 para el producto {item.product_id}")
        
        product = products_dict[item.product_id]
        if product.stock_quantity < item.quantity_sold:
            insufficient_stock_items.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "requested": item.quantity_sold,
                "available": product.stock_quantity
            })
        total_amount += product.selling_price * item.quantity_sold
    
    if insufficient_stock_items:
        raise InsufficientStockError(
            "Stock insuficiente para algunos productos",
            details={"insufficient_items": insufficient_stock_items}
        )
    
    try:
        db_sale = models.PointOfSaleTransaction(
            user_id=user_id,
            total_amount=total_amount,
            transaction_time=datetime.utcnow()
        )
        db.add(db_sale)
        db.commit()

        # Crear ítems y actualizar stock en una sola operación
        for item in sale.items:
            product = products_dict[item.product_id]
            product.stock_quantity -= item.quantity_sold
            db_item = models.PointOfSaleItem(
                transaction_id=db_sale.id,
                product_id=item.product_id,
                quantity_sold=item.quantity_sold,
                price_at_time_of_sale=product.selling_price
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_sale)
        return db_sale
        
    except Exception as e:
        db.rollback()
        raise ValidationError(f"Error al procesar la venta: {str(e)}")

# Funciones para Consignación
def create_consignment_loan(db: Session, loan: schemas.ConsignmentLoanCreate):
    """Crea un préstamo de consignación y actualiza el inventario automáticamente"""
    try:
        # Verificar que el producto existe y tiene stock suficiente
        product = get_product(db, loan.product_id)
        if not product:
            raise ValueError(f"Producto con ID {loan.product_id} no encontrado")
        
        if product.stock_quantity < loan.quantity_loaned:
            raise ValueError(f"Stock insuficiente. Disponible: {product.stock_quantity}, Solicitado: {loan.quantity_loaned}")
        
        # Verificar que el distribuidor existe
        distributor = get_distributor(db, loan.distributor_id)
        if not distributor:
            raise ValueError(f"Distribuidor con ID {loan.distributor_id} no encontrado")
        
        # Crear el préstamo
        db_loan = models.ConsignmentLoan(**loan.dict())
        db.add(db_loan)
        
        # Actualizar el stock del producto (restar cantidad prestada)
        product.stock_quantity -= loan.quantity_loaned
        
        # Registrar la transacción en logs de auditoría si es necesario
        from .logging_config import get_secure_logger
        logger = get_secure_logger(__name__)
        logger.info(
            f"Consignment loan created: loan_id={db_loan.id}, "
            f"distributor_id={loan.distributor_id}, "
            f"product_id={loan.product_id}, "
            f"quantity_loaned={loan.quantity_loaned}, "
            f"previous_stock={product.stock_quantity + loan.quantity_loaned}, "
            f"new_stock={product.stock_quantity}"
        )
        
        db.commit()
        db.refresh(db_loan)
        return db_loan
        
    except Exception as e:
        db.rollback()
        raise e

def get_all_consignment_loans(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene todos los préstamos de consignación con eager loading de productos y distribuidores"""
    return db.query(models.ConsignmentLoan)\
        .options(joinedload(models.ConsignmentLoan.product))\
        .options(joinedload(models.ConsignmentLoan.distributor))\
        .order_by(desc(models.ConsignmentLoan.loan_date))\
        .offset(skip).limit(limit).all()

def get_distributor_loans(db: Session, distributor_id: int):
    """Obtiene los préstamos de un distribuidor con eager loading de productos"""
    return db.query(models.ConsignmentLoan)\
        .options(joinedload(models.ConsignmentLoan.product))\
        .options(joinedload(models.ConsignmentLoan.distributor))\
        .filter(models.ConsignmentLoan.distributor_id == distributor_id)\
        .order_by(desc(models.ConsignmentLoan.loan_date))\
        .all()

def create_consignment_report(db: Session, report: schemas.ConsignmentReportCreate):
    """Crea un reporte de consignación y actualiza el inventario automáticamente"""
    try:
        # Verificar que el préstamo existe
        loan = db.query(models.ConsignmentLoan).filter(models.ConsignmentLoan.id == report.loan_id).first()
        if not loan:
            raise ValueError(f"Préstamo con ID {report.loan_id} no encontrado")
        
        # Verificar que el préstamo está en estado activo
        if loan.status != models.LoanStatus.en_prestamo:
            raise ValueError(f"El préstamo está en estado '{loan.status}' y no puede recibir reportes")
        
        # Validar que las cantidades no excedan lo prestado
        total_reported = report.quantity_sold + report.quantity_returned
        if total_reported > loan.quantity_loaned:
            raise ValueError(f"Total reportado ({total_reported}) excede cantidad prestada ({loan.quantity_loaned})")
        
        # Verificar si ya hay reportes previos para este préstamo
        existing_reports = db.query(models.ConsignmentReport).filter(
            models.ConsignmentReport.loan_id == report.loan_id
        ).all()
        
        total_previous_sold = sum(r.quantity_sold for r in existing_reports)
        total_previous_returned = sum(r.quantity_returned for r in existing_reports)
        total_previous = total_previous_sold + total_previous_returned
        
        if total_previous + total_reported > loan.quantity_loaned:
            remaining = loan.quantity_loaned - total_previous
            raise ValueError(f"Total acumulado excede lo prestado. Disponible para reportar: {remaining}")
        
        # Obtener el producto para actualizar stock
        product = get_product(db, loan.product_id)
        if not product:
            raise ValueError(f"Producto con ID {loan.product_id} no encontrado")
        
        # Crear el reporte
        db_report = models.ConsignmentReport(**report.dict())
        db.add(db_report)
        
        # Devolver al stock solo los productos retornados (no vendidos)
        previous_stock = product.stock_quantity
        product.stock_quantity += report.quantity_returned
        
        # Verificar si el préstamo está completamente reportado
        total_reported_final = total_previous + total_reported
        if total_reported_final == loan.quantity_loaned:
            loan.status = models.LoanStatus.devuelto
        
        # Registrar la transacción en logs de auditoría
        from .logging_config import get_secure_logger
        logger = get_secure_logger(__name__)
        logger.info(
            f"Consignment report created: report_id={db_report.id}, "
            f"loan_id={report.loan_id}, "
            f"distributor_id={loan.distributor_id}, "
            f"product_id={loan.product_id}, "
            f"quantity_sold={report.quantity_sold}, "
            f"quantity_returned={report.quantity_returned}, "
            f"previous_stock={previous_stock}, "
            f"new_stock={product.stock_quantity}, "
            f"loan_status={loan.status.value}"
        )
        
        db.commit()
        db.refresh(db_report)
        return db_report
        
    except Exception as e:
        db.rollback()
        raise e

# Funciones optimizadas para reportes y consultas frecuentes

def get_sales_with_details(db: Session, skip: int = 0, limit: int = 100, user_id: int = None):
    """Obtiene transacciones de venta con detalles de productos y usuario usando eager loading"""
    query = db.query(models.PointOfSaleTransaction)\
        .options(joinedload(models.PointOfSaleTransaction.user))\
        .options(selectinload(models.PointOfSaleTransaction.items).joinedload(models.PointOfSaleItem.product))
    
    if user_id:
        query = query.filter(models.PointOfSaleTransaction.user_id == user_id)
    
    return query.order_by(desc(models.PointOfSaleTransaction.transaction_time))\
        .offset(skip).limit(limit).all()

def get_products_with_low_stock(db: Session, threshold: int = 5):
    """Obtiene productos con stock bajo de forma optimizada"""
    return db.query(models.Product)\
        .filter(models.Product.stock_quantity <= threshold)\
        .order_by(asc(models.Product.stock_quantity), asc(models.Product.name))\
        .all()

def get_loans_by_status(db: Session, status: models.LoanStatus, skip: int = 0, limit: int = 100):
    """Obtiene préstamos por estado con eager loading"""
    return db.query(models.ConsignmentLoan)\
        .options(joinedload(models.ConsignmentLoan.product))\
        .options(joinedload(models.ConsignmentLoan.distributor))\
        .filter(models.ConsignmentLoan.status == status)\
        .order_by(asc(models.ConsignmentLoan.return_due_date))\
        .offset(skip).limit(limit).all()

def get_overdue_loans(db: Session):
    """Obtiene préstamos vencidos"""
    from datetime import date
    return db.query(models.ConsignmentLoan)\
        .options(joinedload(models.ConsignmentLoan.product))\
        .options(joinedload(models.ConsignmentLoan.distributor))\
        .filter(
            models.ConsignmentLoan.status == models.LoanStatus.en_prestamo,
            models.ConsignmentLoan.return_due_date < date.today()
        )\
        .order_by(asc(models.ConsignmentLoan.return_due_date))\
        .all()

def get_sales_summary_by_date_range(db: Session, start_date, end_date):
    """Obtiene resumen de ventas por rango de fechas"""
    return db.query(
        func.date(models.PointOfSaleTransaction.transaction_time).label('date'),
        func.count(models.PointOfSaleTransaction.id).label('total_transactions'),
        func.sum(models.PointOfSaleTransaction.total_amount).label('total_sales')
    ).filter(
        models.PointOfSaleTransaction.transaction_time >= start_date,
        models.PointOfSaleTransaction.transaction_time <= end_date
    ).group_by(
        func.date(models.PointOfSaleTransaction.transaction_time)
    ).order_by(
        func.date(models.PointOfSaleTransaction.transaction_time)
    ).all()

def get_top_selling_products(db: Session, limit: int = 10, start_date=None, end_date=None):
    """Obtiene los productos más vendidos"""
    query = db.query(
        models.Product,
        func.sum(models.PointOfSaleItem.quantity_sold).label('total_sold'),
        func.sum(models.PointOfSaleItem.quantity_sold * models.PointOfSaleItem.price_at_time_of_sale).label('total_revenue')
    ).join(
        models.PointOfSaleItem, models.Product.id == models.PointOfSaleItem.product_id
    ).join(
        models.PointOfSaleTransaction, models.PointOfSaleItem.transaction_id == models.PointOfSaleTransaction.id
    )
    
    if start_date:
        query = query.filter(models.PointOfSaleTransaction.transaction_time >= start_date)
    if end_date:
        query = query.filter(models.PointOfSaleTransaction.transaction_time <= end_date)
    
    return query.group_by(models.Product.id)\
        .order_by(desc('total_sold'))\
        .limit(limit).all()