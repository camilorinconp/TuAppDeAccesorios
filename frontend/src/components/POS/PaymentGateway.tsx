// ==================================================================
// PAYMENT GATEWAY - PASARELA DE PAGO
// ==================================================================

import React, { useState } from 'react';
import { CartItem } from '../../types/core';

interface PaymentGatewayProps {
  cartItems: CartItem[];
  totalAmount: number;
  onConfirmPayment: (paymentData: PaymentData) => void;
  onCancel: () => void;
}

export interface PaymentData {
  method: 'efectivo' | 'tarjeta' | 'transferencia';
  amount: number;
  amountReceived?: number;
  change?: number;
  cardDetails?: {
    cardNumber: string;
    expiryDate: string;
    cvv: string;
    cardholderName: string;
  };
  transferDetails?: {
    referenceNumber: string;
    bank: string;
  };
}

export const PaymentGateway: React.FC<PaymentGatewayProps> = ({
  cartItems,
  totalAmount,
  onConfirmPayment,
  onCancel,
}) => {
  const [paymentMethod, setPaymentMethod] = useState<'efectivo' | 'tarjeta' | 'transferencia'>('efectivo');
  const [amountReceived, setAmountReceived] = useState<string>(totalAmount.toString());
  const [cardDetails, setCardDetails] = useState({
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    cardholderName: '',
  });
  const [transferDetails, setTransferDetails] = useState({
    referenceNumber: '',
    bank: '',
  });

  const change = paymentMethod === 'efectivo' ? Math.max(0, parseFloat(amountReceived) - totalAmount) : 0;
  const isValidPayment = () => {
    if (paymentMethod === 'efectivo') {
      return parseFloat(amountReceived) >= totalAmount;
    }
    if (paymentMethod === 'tarjeta') {
      return cardDetails.cardNumber && cardDetails.expiryDate && cardDetails.cvv && cardDetails.cardholderName;
    }
    if (paymentMethod === 'transferencia') {
      return transferDetails.referenceNumber && transferDetails.bank;
    }
    return false;
  };

  const handleConfirmPayment = () => {
    if (!isValidPayment()) return;

    const paymentData: PaymentData = {
      method: paymentMethod,
      amount: totalAmount,
      ...(paymentMethod === 'efectivo' && {
        amountReceived: parseFloat(amountReceived),
        change,
      }),
      ...(paymentMethod === 'tarjeta' && { cardDetails }),
      ...(paymentMethod === 'transferencia' && { transferDetails }),
    };

    onConfirmPayment(paymentData);
  };

  return (
    <div className="payment-gateway-overlay">
      <div className="payment-gateway-modal">
        <div className="payment-header">
          <h2>Procesar Pago</h2>
          <button className="close-button" onClick={onCancel}>×</button>
        </div>

        {/* Resumen de la compra */}
        <div className="purchase-summary">
          <h3>Resumen de Compra</h3>
          <div className="items-summary">
            {cartItems.map((item) => (
              <div key={item.id} className="item-row">
                <span className="item-name">{item.name}</span>
                <span className="item-quantity">x{item.quantity_in_cart}</span>
                <span className="item-total">
                  ${(item.selling_price * item.quantity_in_cart).toLocaleString('es-CO')}
                </span>
              </div>
            ))}
          </div>
          <div className="total-amount">
            <strong>Total: ${totalAmount.toLocaleString('es-CO')}</strong>
          </div>
        </div>

        {/* Métodos de pago */}
        <div className="payment-methods">
          <h3>Método de Pago</h3>
          <div className="payment-options">
            <label className={`payment-option ${paymentMethod === 'efectivo' ? 'selected' : ''}`}>
              <input
                type="radio"
                value="efectivo"
                checked={paymentMethod === 'efectivo'}
                onChange={(e) => setPaymentMethod(e.target.value as any)}
              />
              <span>💵 Efectivo</span>
            </label>
            
            <label className={`payment-option ${paymentMethod === 'tarjeta' ? 'selected' : ''}`}>
              <input
                type="radio"
                value="tarjeta"
                checked={paymentMethod === 'tarjeta'}
                onChange={(e) => setPaymentMethod(e.target.value as any)}
              />
              <span>💳 Tarjeta</span>
            </label>
            
            <label className={`payment-option ${paymentMethod === 'transferencia' ? 'selected' : ''}`}>
              <input
                type="radio"
                value="transferencia"
                checked={paymentMethod === 'transferencia'}
                onChange={(e) => setPaymentMethod(e.target.value as any)}
              />
              <span>🏦 Transferencia</span>
            </label>
          </div>
        </div>

        {/* Detalles específicos del método de pago */}
        <div className="payment-details">
          {paymentMethod === 'efectivo' && (
            <div className="cash-payment">
              <h4>Pago en Efectivo</h4>
              <div className="cash-input">
                <label>Monto Recibido:</label>
                <input
                  type="number"
                  value={amountReceived}
                  onChange={(e) => setAmountReceived(e.target.value)}
                  min={totalAmount}
                  step="0.01"
                />
              </div>
              {change > 0 && (
                <div className="change-amount">
                  <strong>Cambio: ${change.toLocaleString('es-CO')}</strong>
                </div>
              )}
            </div>
          )}

          {paymentMethod === 'tarjeta' && (
            <div className="card-payment">
              <h4>Pago con Tarjeta</h4>
              <div className="card-form">
                <input
                  type="text"
                  placeholder="Número de tarjeta"
                  value={cardDetails.cardNumber}
                  onChange={(e) => setCardDetails({...cardDetails, cardNumber: e.target.value})}
                  maxLength={19}
                />
                <div className="card-row">
                  <input
                    type="text"
                    placeholder="MM/AA"
                    value={cardDetails.expiryDate}
                    onChange={(e) => setCardDetails({...cardDetails, expiryDate: e.target.value})}
                    maxLength={5}
                  />
                  <input
                    type="text"
                    placeholder="CVV"
                    value={cardDetails.cvv}
                    onChange={(e) => setCardDetails({...cardDetails, cvv: e.target.value})}
                    maxLength={4}
                  />
                </div>
                <input
                  type="text"
                  placeholder="Nombre del titular"
                  value={cardDetails.cardholderName}
                  onChange={(e) => setCardDetails({...cardDetails, cardholderName: e.target.value})}
                />
              </div>
            </div>
          )}

          {paymentMethod === 'transferencia' && (
            <div className="transfer-payment">
              <h4>Pago por Transferencia</h4>
              <div className="transfer-form">
                <input
                  type="text"
                  placeholder="Número de referencia"
                  value={transferDetails.referenceNumber}
                  onChange={(e) => setTransferDetails({...transferDetails, referenceNumber: e.target.value})}
                />
                <select
                  value={transferDetails.bank}
                  onChange={(e) => setTransferDetails({...transferDetails, bank: e.target.value})}
                >
                  <option value="">Seleccionar banco</option>
                  <option value="bancolombia">Bancolombia</option>
                  <option value="davivienda">Davivienda</option>
                  <option value="bbva">BBVA</option>
                  <option value="nequi">Nequi</option>
                  <option value="daviplata">Daviplata</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Botones de acción */}
        <div className="payment-actions">
          <button className="cancel-button" onClick={onCancel}>
            Cancelar
          </button>
          <button 
            className={`confirm-button ${isValidPayment() ? 'enabled' : 'disabled'}`}
            onClick={handleConfirmPayment}
            disabled={!isValidPayment()}
          >
            Confirmar Pago - ${totalAmount.toLocaleString('es-CO')}
          </button>
        </div>
      </div>
    </div>
  );
};