# ==================================================================
# SERVICIO DE INVENTARIO - GESTIÓN AVANZADA DE UBICACIONES
# ==================================================================

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date
from decimal import Decimal

from ..models.main import Product, ProductLocation, ConsignmentLoan, ConsignmentReport, Distributor
from ..models.enums import LocationType, LoanStatus
from ..logging_config import get_secure_logger

logger = get_secure_logger(__name__)


class InventoryService:
    """Servicio para gestión avanzada de inventario con tracking de ubicaciones"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_available_stock(self, product_id: int) -> int:
        """
        Obtiene el stock disponible real (en bodega) para un producto.
        No incluye productos en consignación.
        """
        warehouse_stock = self.db.query(func.sum(ProductLocation.quantity)).filter(
            and_(
                ProductLocation.product_id == product_id,
                ProductLocation.location_type == LocationType.warehouse
            )
        ).scalar() or 0
        
        return max(0, warehouse_stock)
    
    def get_consignment_stock(self, product_id: int, distributor_id: Optional[int] = None) -> int:
        """
        Obtiene el stock en consignación para un producto.
        Si se especifica distributor_id, solo para ese distribuidor.
        """
        query = self.db.query(func.sum(ProductLocation.quantity)).filter(
            and_(
                ProductLocation.product_id == product_id,
                ProductLocation.location_type == LocationType.consignment
            )
        )
        
        if distributor_id:
            query = query.filter(ProductLocation.location_id == distributor_id)
        
        return query.scalar() or 0
    
    def get_total_stock(self, product_id: int) -> Dict[str, int]:
        """
        Obtiene un resumen completo del stock por ubicación.
        """
        locations = self.db.query(
            ProductLocation.location_type,
            func.sum(ProductLocation.quantity).label('total_quantity')
        ).filter(
            ProductLocation.product_id == product_id
        ).group_by(ProductLocation.location_type).all()
        
        stock_summary = {
            'warehouse': 0,
            'consignment': 0,
            'sold': 0,
            'returned': 0
        }
        
        for location_type, quantity in locations:
            stock_summary[location_type.value] = quantity or 0
        
        return stock_summary
    
    def move_products_to_consignment(
        self, 
        product_id: int, 
        quantity: int, 
        distributor_id: int,
        reference_type: str = "loan",
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Mueve productos de bodega a consignación.
        Retorna True si la operación fue exitosa.
        """
        try:
            # Verificar stock disponible en bodega
            available_stock = self.get_available_stock(product_id)
            if available_stock < quantity:
                logger.warning(f"Stock insuficiente para producto {product_id}. Disponible: {available_stock}, Requerido: {quantity}")
                return False
            
            # Reducir stock en bodega
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.warehouse,
                quantity_change=-quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Movido a consignación - {notes or ''}"
            )
            
            # Agregar stock en consignación
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.consignment,
                location_id=distributor_id,
                quantity_change=quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Recibido en consignación - {notes or ''}"
            )
            
            logger.info(f"Productos movidos a consignación: {quantity} unidades del producto {product_id} al distribuidor {distributor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error moviendo productos a consignación: {str(e)}")
            return False
    
    def process_consignment_sale(
        self,
        product_id: int,
        quantity_sold: int,
        distributor_id: int,
        reference_type: str = "sale",
        reference_id: Optional[int] = None,
        selling_price: Optional[Decimal] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Procesa una venta desde consignación.
        Mueve productos de consignación a vendidos.
        """
        try:
            # Verificar stock en consignación
            consignment_stock = self.get_consignment_stock(product_id, distributor_id)
            if consignment_stock < quantity_sold:
                logger.warning(f"Stock insuficiente en consignación para producto {product_id}. Disponible: {consignment_stock}, Requerido: {quantity_sold}")
                return False
            
            # Reducir stock en consignación
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.consignment,
                location_id=distributor_id,
                quantity_change=-quantity_sold,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Vendido desde consignación - {notes or ''}"
            )
            
            # Agregar a vendidos
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.sold,
                location_id=distributor_id,
                quantity_change=quantity_sold,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Venta procesada - Precio: {selling_price} - {notes or ''}"
            )
            
            logger.info(f"Venta procesada: {quantity_sold} unidades del producto {product_id} por distribuidor {distributor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error procesando venta desde consignación: {str(e)}")
            return False
    
    def process_consignment_return(
        self,
        product_id: int,
        quantity_returned: int,
        distributor_id: int,
        reference_type: str = "return",
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Procesa una devolución desde consignación.
        Mueve productos de consignación de vuelta a bodega.
        """
        try:
            # Verificar stock en consignación
            consignment_stock = self.get_consignment_stock(product_id, distributor_id)
            if consignment_stock < quantity_returned:
                logger.warning(f"Stock insuficiente en consignación para devolución del producto {product_id}. Disponible: {consignment_stock}, Requerido: {quantity_returned}")
                return False
            
            # Reducir stock en consignación
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.consignment,
                location_id=distributor_id,
                quantity_change=-quantity_returned,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Devuelto desde consignación - {notes or ''}"
            )
            
            # Agregar de vuelta a bodega
            self._update_location_stock(
                product_id=product_id,
                location_type=LocationType.warehouse,
                quantity_change=quantity_returned,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"Devuelto a bodega - {notes or ''}"
            )
            
            logger.info(f"Devolución procesada: {quantity_returned} unidades del producto {product_id} del distribuidor {distributor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error procesando devolución desde consignación: {str(e)}")
            return False
    
    def _update_location_stock(
        self,
        product_id: int,
        location_type: LocationType,
        quantity_change: int,
        location_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ):
        """
        Actualiza el stock en una ubicación específica.
        Crea un nuevo registro si no existe.
        """
        existing_location = self.db.query(ProductLocation).filter(
            and_(
                ProductLocation.product_id == product_id,
                ProductLocation.location_type == location_type,
                ProductLocation.location_id == location_id
            )
        ).first()
        
        if existing_location:
            # Actualizar registro existente
            existing_location.quantity += quantity_change
            existing_location.updated_at = datetime.utcnow()
            if notes:
                existing_location.notes = notes
        else:
            # Crear nuevo registro
            new_location = ProductLocation(
                product_id=product_id,
                location_type=location_type,
                location_id=location_id,
                quantity=max(0, quantity_change),  # No permitir cantidades negativas
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes
            )
            self.db.add(new_location)
        
        self.db.commit()
    
    def get_products_by_location(self, location_type: LocationType, location_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene todos los productos en una ubicación específica.
        """
        query = self.db.query(
            ProductLocation,
            Product.sku,
            Product.name,
            Product.cost_price,
            Product.selling_price
        ).join(Product).filter(
            ProductLocation.location_type == location_type
        )
        
        if location_id:
            query = query.filter(ProductLocation.location_id == location_id)
        
        results = query.all()
        
        products = []
        for location, sku, name, cost_price, selling_price in results:
            products.append({
                'product_id': location.product_id,
                'sku': sku,
                'name': name,
                'quantity': location.quantity,
                'cost_price': cost_price,
                'selling_price': selling_price,
                'location_id': location.location_id,
                'reference_type': location.reference_type,
                'reference_id': location.reference_id,
                'updated_at': location.updated_at,
                'notes': location.notes
            })
        
        return products
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen completo del inventario por ubicaciones.
        """
        summary = self.db.query(
            ProductLocation.location_type,
            func.count(ProductLocation.product_id.distinct()).label('unique_products'),
            func.sum(ProductLocation.quantity).label('total_quantity'),
            func.sum(ProductLocation.quantity * Product.cost_price).label('total_cost_value'),
            func.sum(ProductLocation.quantity * Product.selling_price).label('total_selling_value')
        ).join(Product).group_by(ProductLocation.location_type).all()
        
        result = {
            'by_location': {},
            'totals': {
                'unique_products': 0,
                'total_quantity': 0,
                'total_cost_value': 0,
                'total_selling_value': 0
            }
        }
        
        for location_type, unique_products, total_quantity, total_cost_value, total_selling_value in summary:
            result['by_location'][location_type.value] = {
                'unique_products': unique_products or 0,
                'total_quantity': total_quantity or 0,
                'total_cost_value': float(total_cost_value or 0),
                'total_selling_value': float(total_selling_value or 0)
            }
            
            # Acumular totales
            result['totals']['unique_products'] += unique_products or 0
            result['totals']['total_quantity'] += total_quantity or 0
            result['totals']['total_cost_value'] += float(total_cost_value or 0)
            result['totals']['total_selling_value'] += float(total_selling_value or 0)
        
        return result
    
    def initialize_product_in_warehouse(self, product_id: int, initial_quantity: int):
        """
        Inicializa un producto en bodega cuando se crea.
        """
        self._update_location_stock(
            product_id=product_id,
            location_type=LocationType.warehouse,
            quantity_change=initial_quantity,
            reference_type="initial_stock",
            notes="Stock inicial del producto"
        )