// ==================================================================
// CART SECTION - SECCIÓN DEL CARRITO DE COMPRAS
// ==================================================================

import React from 'react';
import { CartItem } from '../../types/core';

interface CartSectionProps {
  items: CartItem[];
  totalAmount: number;
  totalItems: number;
  onRemoveItem: (productId: number) => void;
}

export const CartSection: React.FC<CartSectionProps> = ({
  items,
  totalAmount,
  totalItems,
  onRemoveItem,
}) => {

  if (items.length === 0) {
    return (
      <div className="cart-section">
        <h2>Carrito de Compras</h2>
        <div className="empty-cart">
          <p>El carrito está vacío.</p>
        </div>
        <div className="cart-total">
          <h3>Total: $0</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="cart-section">
      <h2>Carrito de Compras ({totalItems} productos)</h2>
      
      <div className="cart-items">
        <table className="cart-table">
          <thead>
            <tr>
              <th>Producto</th>
              <th>Cantidad</th>
              <th>Precio Unit.</th>
              <th>Subtotal</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="product-info">
                    <span className="product-name">{item.name}</span>
                    <small className="product-sku">SKU: {item.sku}</small>
                  </div>
                </td>
                <td className="quantity">{item.quantity_in_cart}</td>
                <td className="price">
                  ${item.selling_price.toLocaleString('es-CO')}
                </td>
                <td className="subtotal">
                  ${(item.selling_price * item.quantity_in_cart).toLocaleString('es-CO')}
                </td>
                <td>
                  <button 
                    onClick={() => onRemoveItem(item.id)}
                    className="remove-button"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="cart-total">
        <h3>Total: ${totalAmount.toLocaleString('es-CO')}</h3>
      </div>
    </div>
  );
};