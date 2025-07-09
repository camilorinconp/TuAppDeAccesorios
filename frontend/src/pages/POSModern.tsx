import React, { useState, useEffect, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../hooks/useAppDispatch';
import { useDebounce } from '../hooks/useDebounce';
import { searchProducts, setQuery, clearSearch } from '../store/slices/searchSlice';
import { addToCart, removeFromCart, clearCart, updateQuantity } from '../store/slices/cartSlice';
import { processSale, clearSuccessMessage } from '../store/slices/saleSlice';
import { PaymentGateway, PaymentData } from '../components/POS/PaymentGateway';

interface Product {
  id: number;
  name: string;
  sku: string;
  cost_price: number;
  selling_price: number;
  stock_quantity: number;
  category?: string;
  image_url?: string;
  description?: string;
}

interface CartItem extends Product {
  quantity_in_cart: number;
}

const POSModern: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Estados locales
  const [searchQuery, setSearchQuery] = useState('');
  const [showPaymentGateway, setShowPaymentGateway] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [isGridView, setIsGridView] = useState(true);
  
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
  
  // Limpiar mensaje de éxito
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        dispatch(clearSuccessMessage());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage, dispatch]);

  // Funciones de manejo
  const handleAddToCart = useCallback((product: Product) => {
    if (product.stock_quantity > 0) {
      dispatch(addToCart(product));
    }
  }, [dispatch]);

  const handleRemoveFromCart = useCallback((productId: number) => {
    dispatch(removeFromCart(productId));
  }, [dispatch]);

  const handleUpdateQuantity = useCallback((productId: number, quantity: number) => {
    if (quantity === 0) {
      dispatch(removeFromCart(productId));
    } else {
      dispatch(updateQuantity({ id: productId, quantity }));
    }
  }, [dispatch]);

  const handleClearCart = useCallback(() => {
    dispatch(clearCart());
  }, [dispatch]);

  const handleCheckout = useCallback(() => {
    if (cartItems.length > 0) {
      setShowPaymentGateway(true);
    }
  }, [cartItems.length]);

  const handlePaymentComplete = useCallback((paymentData: PaymentData) => {
    const saleData = {
      user_id: 1, // TODO: Obtener el ID del usuario autenticado
      items: cartItems.map(item => ({
        product_id: item.id,
        quantity_sold: item.quantity_in_cart,
        price_at_time_of_sale: item.selling_price,
      })),
      total_amount: totalAmount,
    };

    dispatch(processSale(saleData));
    setShowPaymentGateway(false);
  }, [cartItems, totalAmount, dispatch]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const categories = ['all', 'fundas', 'cargadores', 'protectores', 'cables', 'audífonos'];
  const filteredResults = selectedCategory === 'all' 
    ? results 
    : results.filter(product => 
        product.category?.toLowerCase().includes(selectedCategory.toLowerCase())
      );

  return (
    <div style={{
      backgroundColor: '#f8fafc',
      minHeight: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Header moderno */}
      <div style={{
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        padding: '16px 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center' 
          }}>
            <div>
              <h1 style={{
                margin: 0,
                fontSize: '28px',
                fontWeight: '700',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                💰 Punto de Venta
              </h1>
              <p style={{ margin: 0, color: '#6b7280', fontSize: '14px' }}>
                Sistema moderno de ventas
              </p>
            </div>
            
            {/* Quick actions */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                onClick={() => setIsGridView(!isGridView)}
                style={{
                  padding: '8px 12px',
                  backgroundColor: isGridView ? '#3b82f6' : 'white',
                  color: isGridView ? 'white' : '#374151',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: '500'
                }}
              >
                {isGridView ? '📊 Grid' : '📋 Lista'}
              </button>
              
              {cartItems.length > 0 && (
                <button
                  onClick={handleClearCart}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#dc2626',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '500'
                  }}
                >
                  🗑️ Limpiar
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Notificaciones */}
      {successMessage && (
        <div style={{
          backgroundColor: '#dcfce7',
          border: '1px solid #bbf7d0',
          borderRadius: '8px',
          padding: '12px 16px',
          margin: '16px 24px',
          color: '#166534',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>✅</span>
          <span style={{ fontWeight: '500' }}>{successMessage}</span>
        </div>
      )}

      {saleError && (
        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          padding: '12px 16px',
          margin: '16px 24px',
          color: '#991b1b',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>❌</span>
          <span style={{ fontWeight: '500' }}>{saleError}</span>
        </div>
      )}

      <div style={{ 
        maxWidth: '1400px', 
        margin: '0 auto', 
        padding: '24px',
        display: 'grid',
        gridTemplateColumns: '1fr 400px',
        gap: '24px',
        minHeight: 'calc(100vh - 120px)'
      }}>
        {/* Panel izquierdo - Búsqueda y productos */}
        <div>
          {/* Barra de búsqueda moderna */}
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            padding: '20px',
            marginBottom: '20px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ position: 'relative' }}>
                <div style={{
                  position: 'absolute',
                  left: '16px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#9ca3af',
                  fontSize: '18px'
                }}>
                  🔍
                </div>
                <input
                  type="text"
                  placeholder="Buscar productos por nombre, SKU o código..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '16px 16px 16px 52px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '12px',
                    fontSize: '16px',
                    outline: 'none',
                    transition: 'all 0.2s ease',
                    backgroundColor: '#f9fafb'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#3b82f6';
                    e.target.style.backgroundColor = 'white';
                    e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e5e7eb';
                    e.target.style.backgroundColor = '#f9fafb';
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>
            </div>

            {/* Filtros de categoría */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '20px',
                    border: 'none',
                    backgroundColor: selectedCategory === category ? '#3b82f6' : '#f3f4f6',
                    color: selectedCategory === category ? 'white' : '#374151',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '500',
                    textTransform: 'capitalize',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {category === 'all' ? 'Todos' : category}
                </button>
              ))}
            </div>
          </div>

          {/* Resultados de búsqueda */}
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            minHeight: '500px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px'
            }}>
              <h3 style={{ margin: 0, color: '#111827', fontSize: '18px', fontWeight: '600' }}>
                📦 Productos Disponibles
              </h3>
              {searchLoading && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px',
                  color: '#6b7280'
                }}>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid #e5e7eb',
                    borderTop: '2px solid #3b82f6',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                  Buscando...
                </div>
              )}
            </div>

            {searchError && (
              <div style={{
                padding: '16px',
                backgroundColor: '#fef2f2',
                borderRadius: '8px',
                color: '#991b1b',
                textAlign: 'center'
              }}>
                ❌ Error en la búsqueda: {searchError}
              </div>
            )}

            {!searchLoading && !searchError && filteredResults.length === 0 && (
              <div style={{
                textAlign: 'center',
                padding: '60px 20px',
                color: '#6b7280'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
                <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                  {searchQuery ? 'No se encontraron productos' : 'Busca productos para comenzar'}
                </h4>
                <p style={{ margin: 0, fontSize: '14px' }}>
                  {searchQuery 
                    ? `No hay resultados para "${searchQuery}"`
                    : 'Escribe el nombre, SKU o código del producto'
                  }
                </p>
              </div>
            )}

            {/* Grid de productos */}
            {filteredResults.length > 0 && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: isGridView 
                  ? 'repeat(auto-fill, minmax(240px, 1fr))' 
                  : '1fr',
                gap: '16px'
              }}>
                {filteredResults.map((product: Product) => (
                  <div
                    key={product.id}
                    style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '12px',
                      padding: '16px',
                      backgroundColor: product.stock_quantity === 0 ? '#f9fafb' : 'white',
                      opacity: product.stock_quantity === 0 ? 0.6 : 1,
                      transition: 'all 0.2s ease',
                      cursor: product.stock_quantity > 0 ? 'pointer' : 'not-allowed'
                    }}
                    onMouseEnter={(e) => {
                      if (product.stock_quantity > 0) {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
                        e.currentTarget.style.borderColor = '#3b82f6';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (product.stock_quantity > 0) {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                        e.currentTarget.style.borderColor = '#e5e7eb';
                      }
                    }}
                    onClick={() => handleAddToCart(product)}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'flex-start',
                      marginBottom: '12px'
                    }}>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ 
                          margin: '0 0 4px 0', 
                          fontSize: '14px', 
                          fontWeight: '600',
                          color: '#111827',
                          lineHeight: '1.3'
                        }}>
                          {product.name}
                        </h4>
                        <p style={{ 
                          margin: '0 0 8px 0', 
                          fontSize: '12px', 
                          color: '#6b7280'
                        }}>
                          SKU: {product.sku}
                        </p>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          marginBottom: '8px'
                        }}>
                          <span style={{
                            fontSize: '16px',
                            fontWeight: '700',
                            color: '#059669'
                          }}>
                            {formatCurrency(product.selling_price)}
                          </span>
                        </div>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: product.stock_quantity === 0 
                              ? '#dc2626' 
                              : product.stock_quantity <= 5 
                              ? '#f59e0b' 
                              : '#10b981'
                          }}></div>
                          <span style={{
                            fontSize: '12px',
                            color: product.stock_quantity === 0 ? '#dc2626' : '#374151',
                            fontWeight: '500'
                          }}>
                            {product.stock_quantity === 0 
                              ? 'Sin stock' 
                              : `${product.stock_quantity} disponibles`
                            }
                          </span>
                        </div>
                      </div>
                      
                      {product.stock_quantity > 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddToCart(product);
                          }}
                          style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '8px',
                            backgroundColor: '#3b82f6',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '16px',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = '#2563eb';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = '#3b82f6';
                          }}
                        >
                          +
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Panel derecho - Carrito */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          height: 'fit-content',
          position: 'sticky',
          top: '100px'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            paddingBottom: '16px',
            borderBottom: '2px solid #f3f4f6'
          }}>
            <h3 style={{ margin: 0, color: '#111827', fontSize: '18px', fontWeight: '700' }}>
              🛒 Carrito de Venta
            </h3>
            {cartItems.length > 0 && (
              <div style={{
                backgroundColor: '#3b82f6',
                color: 'white',
                borderRadius: '12px',
                padding: '4px 8px',
                fontSize: '12px',
                fontWeight: '600'
              }}>
                {totalItems} items
              </div>
            )}
          </div>

          {cartItems.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🛒</div>
              <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                El carrito está vacío
              </h4>
              <p style={{ margin: 0, fontSize: '14px' }}>
                Agrega productos para comenzar una venta
              </p>
            </div>
          ) : (
            <>
              {/* Items del carrito */}
              <div style={{ 
                maxHeight: '400px', 
                overflowY: 'auto',
                marginBottom: '20px'
              }}>
                {cartItems.map((item: CartItem) => (
                  <div
                    key={item.id}
                    style={{
                      padding: '12px',
                      border: '1px solid #f3f4f6',
                      borderRadius: '8px',
                      marginBottom: '8px',
                      backgroundColor: '#f9fafb'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '8px'
                    }}>
                      <div style={{ flex: 1 }}>
                        <h5 style={{
                          margin: '0 0 4px 0',
                          fontSize: '13px',
                          fontWeight: '600',
                          color: '#111827'
                        }}>
                          {item.name}
                        </h5>
                        <p style={{
                          margin: 0,
                          fontSize: '11px',
                          color: '#6b7280'
                        }}>
                          {formatCurrency(item.selling_price)} c/u
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveFromCart(item.id)}
                        style={{
                          width: '20px',
                          height: '20px',
                          border: 'none',
                          borderRadius: '4px',
                          backgroundColor: '#dc2626',
                          color: 'white',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        ×
                      </button>
                    </div>
                    
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        <button
                          onClick={() => handleUpdateQuantity(item.id, item.quantity_in_cart - 1)}
                          style={{
                            width: '24px',
                            height: '24px',
                            border: '1px solid #d1d5db',
                            borderRadius: '4px',
                            backgroundColor: 'white',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          -
                        </button>
                        <span style={{
                          minWidth: '20px',
                          textAlign: 'center',
                          fontSize: '13px',
                          fontWeight: '600'
                        }}>
                          {item.quantity_in_cart}
                        </span>
                        <button
                          onClick={() => handleUpdateQuantity(item.id, item.quantity_in_cart + 1)}
                          disabled={item.quantity_in_cart >= item.stock_quantity}
                          style={{
                            width: '24px',
                            height: '24px',
                            border: '1px solid #d1d5db',
                            borderRadius: '4px',
                            backgroundColor: item.quantity_in_cart >= item.stock_quantity ? '#f3f4f6' : 'white',
                            cursor: item.quantity_in_cart >= item.stock_quantity ? 'not-allowed' : 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          +
                        </button>
                      </div>
                      <span style={{
                        fontSize: '14px',
                        fontWeight: '700',
                        color: '#059669'
                      }}>
                        {formatCurrency(item.selling_price * item.quantity_in_cart)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Resumen y total */}
              <div style={{
                borderTop: '2px solid #f3f4f6',
                paddingTop: '16px'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px'
                }}>
                  <span style={{
                    fontSize: '18px',
                    fontWeight: '700',
                    color: '#111827'
                  }}>
                    Total:
                  </span>
                  <span style={{
                    fontSize: '24px',
                    fontWeight: '800',
                    color: '#059669'
                  }}>
                    {formatCurrency(totalAmount)}
                  </span>
                </div>

                <button
                  onClick={handleCheckout}
                  disabled={cartItems.length === 0 || isProcessing}
                  style={{
                    width: '100%',
                    padding: '16px',
                    backgroundColor: cartItems.length === 0 || isProcessing ? '#9ca3af' : '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: '700',
                    cursor: cartItems.length === 0 || isProcessing ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  {isProcessing ? (
                    <>
                      <div style={{
                        width: '16px',
                        height: '16px',
                        border: '2px solid #ffffff40',
                        borderTop: '2px solid #ffffff',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                      }}></div>
                      Procesando...
                    </>
                  ) : (
                    <>
                      💳 Finalizar Venta
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Payment Gateway Modal */}
      {showPaymentGateway && (
        <PaymentGateway
          cartItems={cartItems}
          totalAmount={totalAmount}
          onConfirmPayment={handlePaymentComplete}
          onCancel={() => setShowPaymentGateway(false)}
        />
      )}

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default POSModern;