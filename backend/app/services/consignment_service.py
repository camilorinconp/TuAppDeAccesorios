# ==================================================================
# SERVICIO DE CONSIGNACIÓN - LÓGICA DE NEGOCIO MEJORADA
# ==================================================================

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..models.main import Product, ConsignmentLoan, ConsignmentReport, Distributor
from ..models.enums import LoanStatus, LocationType
from ..services.inventory_service import InventoryService
from ..logging_config import get_secure_logger
from ..exceptions import ValidationError, BusinessLogicError

logger = get_secure_logger(__name__)


class ConsignmentService:
    """Servicio para gestión de consignación con lógica de negocio mejorada"""
    
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)
    
    def create_consignment_loan(
        self,
        product_id: int,
        distributor_id: int,
        quantity_loaned: int,
        loan_date: date,
        return_due_date: date,
        max_loan_days: Optional[int] = 30,
        notes: Optional[str] = None
    ) -> ConsignmentLoan:
        """
        Crea un préstamo de consignación con la nueva lógica de negocio.
        Estado inicial: pendiente (no afecta el inventario hasta confirmación)
        """
        try:
            # Validaciones de negocio
            self._validate_loan_creation(product_id, distributor_id, quantity_loaned, loan_date, return_due_date)
            
            # Verificar stock disponible (no reservar aún)
            available_stock = self.inventory_service.get_available_stock(product_id)
            if available_stock < quantity_loaned:
                raise BusinessLogicError(f"Stock insuficiente. Disponible: {available_stock}, Requerido: {quantity_loaned}")
            
            # Crear préstamo en estado pendiente
            loan = ConsignmentLoan(
                product_id=product_id,
                distributor_id=distributor_id,
                quantity_loaned=quantity_loaned,
                loan_date=loan_date,
                return_due_date=return_due_date,
                status=LoanStatus.pendiente,
                max_loan_days=max_loan_days,
                notes=notes,
                quantity_reported=0,
                quantity_pending=quantity_loaned
            )
            
            self.db.add(loan)
            self.db.commit()
            self.db.refresh(loan)
            
            logger.info(f"Préstamo creado en estado pendiente: ID {loan.id}, Producto {product_id}, Distribuidor {distributor_id}")
            return loan
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando préstamo de consignación: {str(e)}")
            raise
    
    def confirm_consignment_loan(self, loan_id: int) -> bool:
        """
        Confirma un préstamo y mueve los productos a consignación.
        Cambia estado de pendiente a en_prestamo.
        """
        try:
            loan = self.db.query(ConsignmentLoan).filter(ConsignmentLoan.id == loan_id).first()
            if not loan:
                raise ValidationError("Préstamo no encontrado")
            
            if loan.status != LoanStatus.pendiente:
                raise BusinessLogicError(f"El préstamo debe estar en estado pendiente. Estado actual: {loan.status}")
            
            # Mover productos a consignación
            success = self.inventory_service.move_products_to_consignment(
                product_id=loan.product_id,
                quantity=loan.quantity_loaned,
                distributor_id=loan.distributor_id,
                reference_type="loan",
                reference_id=loan.id,
                notes=f"Préstamo confirmado - {loan.notes or ''}"
            )
            
            if not success:
                raise BusinessLogicError("No se pudo mover el stock a consignación")
            
            # Actualizar estado del préstamo
            loan.status = LoanStatus.en_prestamo
            loan.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Préstamo confirmado: ID {loan_id}, productos movidos a consignación")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error confirmando préstamo: {str(e)}")
            raise
    
    def cancel_consignment_loan(self, loan_id: int, reason: Optional[str] = None) -> bool:
        """
        Cancela un préstamo pendiente sin afectar el inventario.
        """
        try:
            loan = self.db.query(ConsignmentLoan).filter(ConsignmentLoan.id == loan_id).first()
            if not loan:
                raise ValidationError("Préstamo no encontrado")
            
            if loan.status != LoanStatus.pendiente:
                raise BusinessLogicError(f"Solo se pueden cancelar préstamos pendientes. Estado actual: {loan.status}")
            
            # Cambiar estado a cancelado
            loan.status = LoanStatus.cancelado
            loan.updated_at = datetime.utcnow()
            if reason:
                loan.notes = f"{loan.notes or ''} - Cancelado: {reason}"
            
            self.db.commit()
            
            logger.info(f"Préstamo cancelado: ID {loan_id}, Razón: {reason}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cancelando préstamo: {str(e)}")
            raise
    
    def create_consignment_report(
        self,
        loan_id: int,
        report_date: date,
        quantity_sold: int,
        quantity_returned: int,
        selling_price_at_report: Optional[Decimal] = None,
        distributor_commission: Optional[Decimal] = None,
        notes: Optional[str] = None,
        is_final_report: bool = False
    ) -> ConsignmentReport:
        """
        Crea un reporte de consignación con la nueva lógica de negocio.
        """
        try:
            # Validaciones
            loan = self.db.query(ConsignmentLoan).filter(ConsignmentLoan.id == loan_id).first()
            if not loan:
                raise ValidationError("Préstamo no encontrado")
            
            if loan.status not in [LoanStatus.en_prestamo, LoanStatus.parcialmente_devuelto]:
                raise BusinessLogicError(f"No se puede reportar sobre un préstamo en estado: {loan.status}")
            
            # Validar cantidades
            total_reported = quantity_sold + quantity_returned
            if total_reported <= 0:
                raise ValidationError("Debe reportar al menos una unidad vendida o devuelta")
            
            # Verificar que no exceda lo pendiente
            if loan.quantity_pending < total_reported:
                raise ValidationError(f"Cantidad reportada ({total_reported}) excede lo pendiente ({loan.quantity_pending})")
            
            # Procesar ventas en el inventario
            if quantity_sold > 0:
                success = self.inventory_service.process_consignment_sale(
                    product_id=loan.product_id,
                    quantity_sold=quantity_sold,
                    distributor_id=loan.distributor_id,
                    reference_type="report",
                    reference_id=loan_id,
                    selling_price=selling_price_at_report,
                    notes=notes
                )
                if not success:
                    raise BusinessLogicError("No se pudo procesar la venta en el inventario")
            
            # Procesar devoluciones en el inventario
            if quantity_returned > 0:
                success = self.inventory_service.process_consignment_return(
                    product_id=loan.product_id,
                    quantity_returned=quantity_returned,
                    distributor_id=loan.distributor_id,
                    reference_type="report",
                    reference_id=loan_id,
                    notes=notes
                )
                if not success:
                    raise BusinessLogicError("No se pudo procesar la devolución en el inventario")
            
            # Crear reporte
            report = ConsignmentReport(
                loan_id=loan_id,
                report_date=report_date,
                quantity_sold=quantity_sold,
                quantity_returned=quantity_returned,
                selling_price_at_report=selling_price_at_report,
                distributor_commission=distributor_commission,
                notes=notes,
                is_final_report=is_final_report
            )
            
            self.db.add(report)
            
            # Actualizar préstamo
            loan.quantity_reported += total_reported
            loan.quantity_pending -= total_reported
            loan.updated_at = datetime.utcnow()
            
            # Actualizar estado del préstamo
            if loan.quantity_pending == 0 or is_final_report:
                loan.status = LoanStatus.devuelto
                loan.actual_return_date = report_date
            else:
                loan.status = LoanStatus.parcialmente_devuelto
            
            self.db.commit()
            self.db.refresh(report)
            
            logger.info(f"Reporte de consignación creado: ID {report.id}, Préstamo {loan_id}")
            return report
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando reporte de consignación: {str(e)}")
            raise
    
    def get_overdue_loans(self, as_of_date: Optional[date] = None) -> List[ConsignmentLoan]:
        """
        Obtiene préstamos vencidos que deben ser marcados como tal.
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        overdue_loans = self.db.query(ConsignmentLoan).filter(
            and_(
                ConsignmentLoan.return_due_date < as_of_date,
                ConsignmentLoan.status.in_([LoanStatus.en_prestamo, LoanStatus.parcialmente_devuelto])
            )
        ).all()
        
        return overdue_loans
    
    def mark_loans_as_overdue(self, as_of_date: Optional[date] = None) -> int:
        """
        Marca préstamos vencidos y retorna el número de préstamos actualizados.
        """
        try:
            overdue_loans = self.get_overdue_loans(as_of_date)
            count = 0
            
            for loan in overdue_loans:
                loan.status = LoanStatus.vencido
                loan.updated_at = datetime.utcnow()
                count += 1
            
            self.db.commit()
            
            logger.info(f"Marcados {count} préstamos como vencidos")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marcando préstamos como vencidos: {str(e)}")
            raise
    
    def get_loan_summary(self, loan_id: int) -> Dict[str, Any]:
        """
        Obtiene un resumen completo de un préstamo.
        """
        loan = self.db.query(ConsignmentLoan).filter(ConsignmentLoan.id == loan_id).first()
        if not loan:
            raise ValidationError("Préstamo no encontrado")
        
        # Obtener reportes
        reports = self.db.query(ConsignmentReport).filter(
            ConsignmentReport.loan_id == loan_id
        ).order_by(ConsignmentReport.report_date.desc()).all()
        
        # Calcular totales
        total_sold = sum(report.quantity_sold for report in reports)
        total_returned = sum(report.quantity_returned for report in reports)
        total_revenue = sum(
            (report.quantity_sold * report.selling_price_at_report) 
            for report in reports 
            if report.selling_price_at_report
        ) or 0
        
        return {
            'loan': {
                'id': loan.id,
                'product_id': loan.product_id,
                'distributor_id': loan.distributor_id,
                'quantity_loaned': loan.quantity_loaned,
                'quantity_reported': loan.quantity_reported,
                'quantity_pending': loan.quantity_pending,
                'loan_date': loan.loan_date,
                'return_due_date': loan.return_due_date,
                'actual_return_date': loan.actual_return_date,
                'status': loan.status,
                'notes': loan.notes
            },
            'summary': {
                'total_reports': len(reports),
                'total_sold': total_sold,
                'total_returned': total_returned,
                'total_revenue': float(total_revenue),
                'completion_percentage': (loan.quantity_reported / loan.quantity_loaned) * 100 if loan.quantity_loaned > 0 else 0,
                'is_overdue': loan.return_due_date < date.today() and loan.status in [LoanStatus.en_prestamo, LoanStatus.parcialmente_devuelto]
            },
            'reports': [
                {
                    'id': report.id,
                    'report_date': report.report_date,
                    'quantity_sold': report.quantity_sold,
                    'quantity_returned': report.quantity_returned,
                    'selling_price_at_report': float(report.selling_price_at_report) if report.selling_price_at_report else None,
                    'distributor_commission': float(report.distributor_commission) if report.distributor_commission else None,
                    'notes': report.notes,
                    'is_final_report': report.is_final_report
                }
                for report in reports
            ]
        }
    
    def get_distributor_consignment_summary(self, distributor_id: int) -> Dict[str, Any]:
        """
        Obtiene un resumen de consignación para un distribuidor.
        """
        # Obtener productos en consignación
        consignment_products = self.inventory_service.get_products_by_location(
            location_type=LocationType.consignment,
            location_id=distributor_id
        )
        
        # Obtener préstamos activos
        active_loans = self.db.query(ConsignmentLoan).filter(
            and_(
                ConsignmentLoan.distributor_id == distributor_id,
                ConsignmentLoan.status.in_([LoanStatus.en_prestamo, LoanStatus.parcialmente_devuelto])
            )
        ).all()
        
        # Obtener préstamos vencidos
        overdue_loans = self.db.query(ConsignmentLoan).filter(
            and_(
                ConsignmentLoan.distributor_id == distributor_id,
                ConsignmentLoan.status == LoanStatus.vencido
            )
        ).all()
        
        return {
            'distributor_id': distributor_id,
            'products_in_consignment': consignment_products,
            'active_loans_count': len(active_loans),
            'overdue_loans_count': len(overdue_loans),
            'total_products_value': sum(
                p['quantity'] * p['cost_price'] 
                for p in consignment_products
            ),
            'total_selling_value': sum(
                p['quantity'] * p['selling_price'] 
                for p in consignment_products
            )
        }
    
    def _validate_loan_creation(
        self,
        product_id: int,
        distributor_id: int,
        quantity_loaned: int,
        loan_date: date,
        return_due_date: date
    ):
        """Validaciones de negocio para creación de préstamos"""
        
        # Validar producto existe
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValidationError("Producto no encontrado")
        
        # Validar distribuidor existe
        distributor = self.db.query(Distributor).filter(Distributor.id == distributor_id).first()
        if not distributor:
            raise ValidationError("Distribuidor no encontrado")
        
        # Validar cantidad
        if quantity_loaned <= 0:
            raise ValidationError("La cantidad a prestar debe ser mayor a 0")
        
        # Validar fechas
        if return_due_date <= loan_date:
            raise ValidationError("La fecha de vencimiento debe ser posterior a la fecha de préstamo")
        
        # Validar que no haya préstamos activos del mismo producto al mismo distribuidor
        existing_loan = self.db.query(ConsignmentLoan).filter(
            and_(
                ConsignmentLoan.product_id == product_id,
                ConsignmentLoan.distributor_id == distributor_id,
                ConsignmentLoan.status.in_([LoanStatus.pendiente, LoanStatus.en_prestamo, LoanStatus.parcialmente_devuelto])
            )
        ).first()
        
        if existing_loan:
            raise BusinessLogicError(f"Ya existe un préstamo activo del producto {product.name} para este distribuidor")