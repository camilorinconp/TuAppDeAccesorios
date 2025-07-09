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
  const [amountReceived, setAmountReceived] = useState<string>((totalAmount || 0).toString());
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

  // Validación de seguridad para evitar errores
  if (!cartItems || cartItems.length === 0) {
    return (
      <div className="payment-gateway-overlay">
        <div className="payment-gateway-modal">
          <div className="payment-header">
            <h2>Error</h2>
            <button className="close-button" onClick={onCancel}>×</button>
          </div>
          <p>No hay productos en el carrito para procesar el pago.</p>
          <button onClick={onCancel}>Cerrar</button>
        </div>
      </div>
    );
  }

  const safeTotal = totalAmount || 0;
  const change = paymentMethod === 'efectivo' ? Math.max(0, parseFloat(amountReceived) - safeTotal) : 0;
  const isValidPayment = () => {
    if (paymentMethod === 'efectivo') {
      return parseFloat(amountReceived) >= safeTotal;
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
      amount: safeTotal,
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
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.2)',
        position: 'relative'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 24px',
          borderBottom: '1px solid #e5e7eb'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '600', color: '#1f2937' }}>Procesar Pago</h2>
          <button 
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#6b7280',
              padding: '4px 8px',
              borderRadius: '4px'
            }}
            onClick={onCancel}
            onMouseOver={(e) => (e.target as HTMLElement).style.backgroundColor = '#f3f4f6'}
            onMouseOut={(e) => (e.target as HTMLElement).style.backgroundColor = 'transparent'}
          >×</button>
        </div>

        {/* Resumen de la compra */}
        <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', fontWeight: '600', color: '#1f2937' }}>Resumen de Compra</h3>
          <div>
            {cartItems.map((item) => (
              <div key={item.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: '1px solid #f3f4f6'
              }}>
                <span style={{ fontSize: '14px', color: '#374151', flex: 1 }}>{item.name}</span>
                <span style={{ fontSize: '14px', color: '#6b7280', margin: '0 12px' }}>x{item.quantity_in_cart}</span>
                <span style={{ fontSize: '14px', fontWeight: '600', color: '#1f2937' }}>
                  ${(item.selling_price * item.quantity_in_cart).toLocaleString('es-CO')}
                </span>
              </div>
            ))}
          </div>
          <div style={{
            marginTop: '16px',
            padding: '16px 0',
            borderTop: '2px solid #e5e7eb',
            textAlign: 'right'
          }}>
            <strong style={{ fontSize: '1.25rem', color: '#1f2937' }}>Total: ${safeTotal.toLocaleString('es-CO')}</strong>
          </div>
        </div>

        {/* Métodos de pago */}
        <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', fontWeight: '600', color: '#1f2937' }}>Método de Pago</h3>
          <div style={{ display: 'flex', gap: '12px', flexDirection: 'column' }}>
            {['efectivo', 'tarjeta', 'transferencia'].map((method) => (
              <label 
                key={method}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '12px 16px',
                  border: `2px solid ${paymentMethod === method ? '#10b981' : '#e5e7eb'}`,
                  borderRadius: '8px',
                  cursor: 'pointer',
                  backgroundColor: paymentMethod === method ? '#f0fdf4' : '#fff',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  if (paymentMethod !== method) {
                    (e.target as HTMLElement).style.backgroundColor = '#f9fafb';
                  }
                }}
                onMouseOut={(e) => {
                  if (paymentMethod !== method) {
                    (e.target as HTMLElement).style.backgroundColor = '#fff';
                  }
                }}
              >
                <input
                  type="radio"
                  value={method}
                  checked={paymentMethod === method}
                  onChange={(e) => setPaymentMethod(e.target.value as any)}
                  style={{ marginRight: '12px' }}
                />
                <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                  {method === 'efectivo' && '💵 Efectivo'}
                  {method === 'tarjeta' && '💳 Tarjeta'}
                  {method === 'transferencia' && '🏦 Transferencia'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Detalles específicos del método de pago */}
        <div style={{ padding: '24px' }}>
          {paymentMethod === 'efectivo' && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: '600', color: '#1f2937' }}>Pago en Efectivo</h4>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                  Monto Recibido:
                </label>
                <input
                  type="number"
                  value={amountReceived}
                  onChange={(e) => setAmountReceived(e.target.value)}
                  min={safeTotal}
                  step="0.01"
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '14px',
                    backgroundColor: '#fff'
                  }}
                />
              </div>
              {change > 0 && (
                <div style={{
                  padding: '12px 16px',
                  backgroundColor: '#f0fdf4',
                  border: '1px solid #10b981',
                  borderRadius: '8px',
                  textAlign: 'center'
                }}>
                  <strong style={{ fontSize: '1.125rem', color: '#059669' }}>
                    Cambio: ${change.toLocaleString('es-CO')}
                  </strong>
                </div>
              )}
            </div>
          )}

          {paymentMethod === 'tarjeta' && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: '600', color: '#1f2937' }}>Pago con Tarjeta</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                    Número de tarjeta
                  </label>
                  <input
                    type="text"
                    placeholder="1234 5678 9012 3456"
                    value={cardDetails.cardNumber}
                    onChange={(e) => {
                      // Formatear número de tarjeta con espacios
                      const value = e.target.value.replace(/\s/g, '').replace(/(.{4})/g, '$1 ').trim();
                      if (value.length <= 19) {
                        setCardDetails({...cardDetails, cardNumber: value});
                      }
                    }}
                    maxLength={19}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      backgroundColor: '#fff',
                      fontFamily: 'monospace'
                    }}
                  />
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                      Fecha de vencimiento
                    </label>
                    <input
                      type="text"
                      placeholder="MM/AA"
                      value={cardDetails.expiryDate}
                      onChange={(e) => {
                        // Formatear fecha MM/AA
                        let value = e.target.value.replace(/\D/g, '');
                        if (value.length >= 2) {
                          value = value.substring(0, 2) + '/' + value.substring(2, 4);
                        }
                        setCardDetails({...cardDetails, expiryDate: value});
                      }}
                      maxLength={5}
                      style={{
                        width: '100%',
                        padding: '12px 16px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '14px',
                        backgroundColor: '#fff',
                        fontFamily: 'monospace'
                      }}
                    />
                  </div>
                  
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                      CVV
                    </label>
                    <input
                      type="password"
                      placeholder="123"
                      value={cardDetails.cvv}
                      onChange={(e) => {
                        const value = e.target.value.replace(/\D/g, '');
                        setCardDetails({...cardDetails, cvv: value});
                      }}
                      maxLength={4}
                      style={{
                        width: '100%',
                        padding: '12px 16px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '14px',
                        backgroundColor: '#fff',
                        fontFamily: 'monospace'
                      }}
                    />
                  </div>
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                    Nombre del titular
                  </label>
                  <input
                    type="text"
                    placeholder="Juan Pérez"
                    value={cardDetails.cardholderName}
                    onChange={(e) => setCardDetails({...cardDetails, cardholderName: e.target.value.toUpperCase()})}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      backgroundColor: '#fff',
                      textTransform: 'uppercase'
                    }}
                  />
                </div>
                
                {/* Información de seguridad */}
                <div style={{
                  padding: '12px 16px',
                  backgroundColor: '#f0f9ff',
                  border: '1px solid #0ea5e9',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: '#0c4a6e'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>🔒</span>
                    <span>Sus datos están protegidos con encriptación SSL</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {paymentMethod === 'transferencia' && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: '600', color: '#1f2937' }}>Pago por Transferencia</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                    Banco o entidad financiera
                  </label>
                  <select
                    value={transferDetails.bank}
                    onChange={(e) => setTransferDetails({...transferDetails, bank: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      backgroundColor: '#fff',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="">Seleccionar banco</option>
                    <option value="bancolombia">🏦 Bancolombia</option>
                    <option value="davivienda">🏦 Davivienda</option>
                    <option value="bbva">🏦 BBVA</option>
                    <option value="banco_bogota">🏦 Banco de Bogotá</option>
                    <option value="banco_popular">🏦 Banco Popular</option>
                    <option value="nequi">📱 Nequi</option>
                    <option value="daviplata">📱 Daviplata</option>
                    <option value="movii">📱 Movii</option>
                    <option value="rappipay">📱 RappiPay</option>
                  </select>
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                    Número de referencia o comprobante
                  </label>
                  <input
                    type="text"
                    placeholder="Ej: 123456789 o REF001234"
                    value={transferDetails.referenceNumber}
                    onChange={(e) => setTransferDetails({...transferDetails, referenceNumber: e.target.value.toUpperCase()})}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      backgroundColor: '#fff',
                      fontFamily: 'monospace',
                      textTransform: 'uppercase'
                    }}
                  />
                </div>
                
                {/* Información adicional */}
                <div style={{
                  padding: '16px',
                  backgroundColor: '#fffbeb',
                  border: '1px solid #f59e0b',
                  borderRadius: '8px',
                  fontSize: '13px',
                  color: '#92400e'
                }}>
                  <div style={{ marginBottom: '8px', fontWeight: '600' }}>
                    💡 Información importante:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '16px' }}>
                    <li>Verifique que el monto transferido sea exactamente ${safeTotal.toLocaleString('es-CO')}</li>
                    <li>Guarde el comprobante de la transferencia</li>
                    <li>El número de referencia debe coincidir con el del comprobante</li>
                  </ul>
                </div>
                
                {/* Cuenta de destino (ejemplo) */}
                <div style={{
                  padding: '12px 16px',
                  backgroundColor: '#f0f9ff',
                  border: '1px solid #0ea5e9',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: '#0c4a6e'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                    📋 Datos de transferencia:
                  </div>
                  <div>Cuenta: ****-****-****-1234</div>
                  <div>Titular: TuApp de Accesorios SAS</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Botones de acción */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          padding: '24px',
          backgroundColor: '#f9fafb',
          borderTop: '1px solid #e5e7eb'
        }}>
          <button 
            style={{
              flex: 1,
              padding: '12px 24px',
              backgroundColor: '#fff',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              color: '#374151',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onClick={onCancel}
            onMouseOver={(e) => (e.target as HTMLElement).style.backgroundColor = '#f3f4f6'}
            onMouseOut={(e) => (e.target as HTMLElement).style.backgroundColor = '#fff'}
          >
            Cancelar
          </button>
          <button 
            style={{
              flex: 2,
              padding: '12px 24px',
              backgroundColor: isValidPayment() ? '#10b981' : '#d1d5db',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              color: isValidPayment() ? '#fff' : '#9ca3af',
              cursor: isValidPayment() ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s ease',
              opacity: isValidPayment() ? 1 : 0.6
            }}
            onClick={handleConfirmPayment}
            disabled={!isValidPayment()}
            onMouseOver={(e) => {
              if (isValidPayment()) {
                (e.target as HTMLElement).style.backgroundColor = '#059669';
              }
            }}
            onMouseOut={(e) => {
              if (isValidPayment()) {
                (e.target as HTMLElement).style.backgroundColor = '#10b981';
              }
            }}
          >
            Confirmar Pago - ${safeTotal.toLocaleString('es-CO')}
          </button>
        </div>
      </div>
    </div>
  );
};