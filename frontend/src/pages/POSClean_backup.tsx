// ==================================================================
// POINT OF SALE - VERSIÓN LIMPIA Y COMPILABLE
// ==================================================================

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../hooks/useAppDispatch';
import { useDebounce } from '../hooks/useDebounce';
import { searchProducts, setQuery, clearSearch } from '../store/slices/searchSlice';
import { addToCart, removeFromCart, clearCart } from '../store/slices/cartSlice';
import { processSale, clearSuccessMessage } from '../store/slices/saleSlice';
import { PaymentGateway, PaymentData } from '../components/POS/PaymentGateway';
import '../styles/pos.css';
import '../styles/paymentGateway.css';

const POSClean: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Estados locales
  const [searchQuery, setSearchQuery] = useState('');
  const [cartKey, setCartKey] = useState(0);
  const [showPaymentGateway, setShowPaymentGateway] = useState(false);
  
  // Selectores de estado Redux
  const { results, isLoading: searchLoading, error: searchError } = useAppSelector(state => state.search);
  const { items: cartItems, totalAmount, totalItems } = useAppSelector(state => state.cart);
  const { isProcessing, error: saleError, successMessage } = useAppSelector(state => state.sale);
  
  // Debounce para optimizar búsquedas
  const debouncedQuery = useDebounce(searchQuery, 300);
  
  // Efecto para búsqueda automática
  useEffect(() => {
    dispatch(setQuery(debouncedQuery));
    if (debouncedQuery.trim()) {
      dispatch(searchProducts(debouncedQuery));
    } else {
      dispatch(clearSearch());
    }
  }, [debouncedQuery, dispatch]);

  // Efecto para monitorear cambios en el carrito
  useEffect(() => {
    // Cart state updated
  }, [cartItems, totalAmount, totalItems, cartKey]);

  // Efecto para monitorear cambios en showPaymentGateway
  useEffect(() => {
    // Payment gateway state updated
  }, [showPaymentGateway]);
  
  // Limpiar mensaje de éxito
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        dispatch(clearSuccessMessage());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage, dispatch]);
  
  // Handlers
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };
  
  const handleAddToCart = (product: any) => {
    dispatch(addToCart(product));
  };
  
  const handleRemoveFromCart = (productId: number) => {
    dispatch(removeFromCart(productId));
  };
  
  const handleFinalizeSale = () => {
    if (cartItems.length === 0) {
      return;
    }
    
    setShowPaymentGateway(true);
  };

  const handlePaymentConfirm = async (paymentData: PaymentData) => {
    const saleData = {
      user_id: 1,
      items: cartItems.map(item => ({
        product_id: item.id,
        quantity_sold: item.quantity_in_cart,
        price_at_time_of_sale: item.selling_price,
      })),
      total_amount: totalAmount,
      payment_method: paymentData.method,
      payment_details: paymentData,
    };
    
    const result = await dispatch(processSale(saleData));
    
    if (processSale.fulfilled.match(result)) {
      dispatch(clearCart());
      setSearchQuery('');
      dispatch(clearSearch());
      setCartKey(prev => prev + 1);
      setShowPaymentGateway(false);
      
      // Mostrar recibo o confirmación
      alert(`Venta completada exitosamente!\nMétodo: ${paymentData.method}\nTotal: $${totalAmount.toLocaleString('es-CO')}`);
    }
  };

  const handlePaymentCancel = () => {
    setShowPaymentGateway(false);
  };
  
  return (
    <div className="pos-page">
      <h1>Punto de Venta</h1>
      
      <div className="pos-layout">
        {/* Panel de Búsqueda */}
        <div className="pos-left-panel">
          <div className="search-section">
            <div className="search-input-container">
              <input
                type="text"
                placeholder="Buscar producto por nombre o SKU..."
                value={searchQuery}
                onChange={handleSearchChange}
                className="search-input"
              />
              <button 
                className="search-button"
                disabled={!searchQuery.trim() || searchLoading}
              >
                {searchLoading ? 'Buscando...' : 'Buscar'}
              </button>
            </div>

            <div className="search-results">
              <h3>Resultados de Búsqueda</h3>
              {searchLoading ? (
                <div className="loading">Buscando productos...</div>
              ) : results.length === 0 ? (
                <div className="no-results">No hay resultados.</div>
              ) : (
                <div className="results-list">
                  {results.map((product) => (
                    <div 
                      key={product.id} 
                      className="product-item"
                      onClick={() => handleAddToCart(product)}
                    >
                      <div className="product-info">
                        <h4>{product.name}</h4>
                        <p className="product-sku">SKU: {product.sku}</p>
                        <p className="product-price">
                          ${product.selling_price.toLocaleString('es-CO')}
                        </p>
                        <p className="product-stock">Stock: {product.stock_quantity}</p>
                      </div>
                      <button className="add-button">Agregar</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Panel del Carrito */}
        <div className="pos-right-panel">
          <div key={`cart-section-${cartKey}`} className="cart-section">
            <h2>Carrito de Compras ({totalItems} productos)</h2>
            
            {cartItems.length === 0 ? (
              <div className="empty-cart">
                <p>El carrito está vacío.</p>
              </div>
            ) : (
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
                    {cartItems.map((item) => (
                      <tr key={`${item.id}-${cartKey}`}>
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
                            onClick={() => handleRemoveFromCart(item.id)}
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
            )}
            
            <div className="cart-total">
              <h3>Total: ${totalAmount.toLocaleString('es-CO')}</h3>
            </div>
          </div>
          
          {/* Botón de Finalizar Venta */}
          <div className="sale-actions">
            <button
              onClick={handleFinalizeSale}
              disabled={cartItems.length === 0 || isProcessing}
              className={`finalize-sale-button ${cartItems.length > 0 && !isProcessing ? 'enabled' : 'disabled'}`}
            >
              {isProcessing ? 'Procesando venta...' : 'Finalizar Venta'}
            </button>
          </div>
          
          {/* Mensajes de Estado */}
          <div className="status-messages">
            {successMessage && (
              <div className="message success">
                ✅ {successMessage}
              </div>
            )}
            
            {saleError && (
              <div className="message error">
                ❌ {saleError}
              </div>
            )}
            
            {searchError && (
              <div className="message error">
                🔍 Error en búsqueda: {searchError}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pasarela de Pago */}
      {showPaymentGateway && (
        <PaymentGateway
          cartItems={cartItems}
          totalAmount={totalAmount}
          onConfirmPayment={handlePaymentConfirm}
          onCancel={handlePaymentCancel}
        />
      )}
    </div>
  );
};

export default POSClean;