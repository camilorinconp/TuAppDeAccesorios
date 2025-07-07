import React, { useState, useEffect, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { Product, SalePayload } from '../types';
import { searchProducts, postSale, apiRequest } from '../services/api';
import { useCart } from '../context/CartContext';
import CartDisplay from '../components/CartDisplay';

const POSPage: React.FC = () => {
    // Estados simplificados - el carrito ahora está en el contexto
    const [query, setQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Product[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [isProcessingSale, setIsProcessingSale] = useState(false);
    
    // Usar el contexto del carrito
    const { cart, addToCart, removeFromCart, clearCart, totalAmount } = useCart();
    // const { isAuthenticated } = useAuth(); // Para verificar el rol si es necesario

    // Monitorear cambios del carrito desde el contexto
    useEffect(() => {
        // Cart updated from context
    }, [cart]);

    // Búsqueda automática con debounce cuando cambia el query
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            if (query.trim() !== '') {
                performSearch();
            } else {
                setSearchResults([]);
            }
        }, 300); // Espera 300ms después de que el usuario deje de escribir

        return () => clearTimeout(timeoutId);
    }, [query]);

    const performSearch = async () => {
        if (query.trim() === '') {
            setSearchResults([]);
            return;
        }
        setIsSearching(true);
        try {
            const foundProducts = await searchProducts(query);
            setSearchResults(foundProducts);
            setError(null);
        } catch (err) {
            setError("Error al buscar productos.");
            setSearchResults([]);
        } finally {
            setIsSearching(false);
        }
    };

    const handleSearch = async () => {
        await performSearch();
    };

    const handleAddProductToCart = (product: Product) => {
        addToCart(product);
        setSuccess(null);
        setError(null);
    };

    const handleFinalizeSale = useCallback(async () => {
        if (isProcessingSale) {
            return;
        }

        
        if (cart.length === 0) {
            setError("El carrito está vacío.");
            return;
        }

        // Bloquear procesamiento múltiple
        flushSync(() => {
            setIsProcessingSale(true);
            setError(null);
        });

        const userId = 1; 
        const salePayload: SalePayload = {
            user_id: userId, 
            items: cart.map(item => ({
                product_id: item.id,
                quantity_sold: item.quantity_in_cart,
                price_at_time_of_sale: item.selling_price,
            })),
            total_amount: cart.reduce((acc, item) => acc + item.selling_price * item.quantity_in_cart, 0),
        };


        try {
            await apiRequest('/products/?skip=0&limit=1');
            
            const result = await postSale(salePayload);
            
            // Limpieza INMEDIATA con flushSync
            
            // SOLUCIÓN DEFINITIVA: Destruir y recrear completamente la UI
            
            // Primero, destruir la UI actual
            flushSync(() => {
                setRenderKey(0); // Desmontar todo
                setIsProcessingSale(false);
            });
            
            // Después de 200ms, recrear todo con estado limpio
            setTimeout(() => {
                
                // Limpiar todo ANTES de recrear
                setCart([]);
                setQuery('');
                setSearchResults([]);
                setSuccess("¡Venta registrada con éxito! Inventario actualizado automáticamente.");
                setForceUpdate(0);
                
                // Usar setTimeout adicional para asegurar limpieza
                setTimeout(() => {
                    flushSync(() => {
                        setRenderKey(Date.now()); // Recrear todo
                    });
                }, 50);
            }, 200);
            
            // Ocultar mensaje de éxito después de 3 segundos
            setTimeout(() => {
                setSuccess(null);
            }, 3000);
            
        } catch (err: any) {
            console.error('❌ Error al procesar venta:', err);
            
            flushSync(() => {
                setIsProcessingSale(false);
                if (err.message?.includes('401') || err.message?.includes('unauthorized')) {
                    setError('Error de autenticación. Por favor, vuelve a iniciar sesión.');
                } else if (err.message?.includes('403') || err.message?.includes('forbidden')) {
                    setError('No tienes permisos para realizar ventas.');
                } else {
                    setError(`Error al registrar la venta: ${err.message || err.toString() || 'Error desconocido'}`);
                }
                setSuccess(null);
            });
        }
    }, [cart, isProcessingSale]);

    const totalAmount = cart.reduce((acc, item) => acc + item.selling_price * item.quantity_in_cart, 0);

    // Si renderKey es 0, no renderizar nada (estado de destrucción)
    if (renderKey === 0) {
        return <div style={{ padding: '20px', textAlign: 'center' }}>
            <h1>Procesando venta...</h1>
            <p>🔄 Actualizando interfaz...</p>
        </div>;
    }

    return (
        <div key={renderKey} style={{ padding: '20px' }}>
            <h1>Punto de Venta</h1>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {success && <p style={{ color: 'green' }}>{success}</p>}
            
            <div style={{ marginBottom: '20px' }}>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="Buscar producto por nombre o SKU..."
                    style={{ padding: '8px', width: '300px', marginRight: '10px' }}
                />
                <button onClick={handleSearch} style={{ padding: '8px 15px' }} disabled={isSearching}>
                    {isSearching ? 'Buscando...' : 'Buscar'}
                </button>
            </div>

            <div style={{ marginBottom: '20px', border: '1px solid #eee', padding: '10px' }}>
                <h3>Resultados de Búsqueda</h3>
                {isSearching ? (
                    <p>🔍 Buscando productos...</p>
                ) : searchResults.length === 0 ? (
                    <p>No hay resultados.</p>
                ) : (
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {searchResults.map(product => (
                            <li key={product.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px dotted #eee' }}>
                                <span>{product.name} (SKU: {product.sku}) - ${product.selling_price.toLocaleString('es-CO')} - Stock: {product.stock_quantity}</span>
                                <button onClick={() => handleAddProductToCart(product)} disabled={product.stock_quantity === 0}>Añadir al Carrito</button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div style={{ marginBottom: '20px', border: '1px solid #ccc', padding: '10px' }}>
                <h2>Carrito de Compras</h2>
                {cart.length === 0 ? (
                    <p>El carrito está vacío.</p>
                ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                <th style={{ border: '1px solid #ddd', padding: '8px' }}>Producto</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px' }}>Cantidad</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px' }}>Precio Unit.</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px' }}>Subtotal</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px' }}>Acción</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cart.map(item => (
                                <tr key={item.id}>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.name}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.quantity_in_cart}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>${item.selling_price.toLocaleString('es-CO')}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>${(item.selling_price * item.quantity_in_cart).toLocaleString('es-CO')}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                                        <button onClick={() => handleRemoveProductFromCart(item.id)}>Eliminar</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
                <h3 style={{ textAlign: 'right', marginTop: '10px' }}>Total: ${totalAmount === 0 ? '0' : totalAmount.toLocaleString('es-CO')}</h3>
            </div>

            <button 
                onClick={handleFinalizeSale} 
                style={{ 
                    marginTop: '20px', 
                    padding: '10px 20px', 
                    fontSize: '1.2em', 
                    backgroundColor: isProcessingSale ? '#6c757d' : '#28a745', 
                    color: 'white', 
                    border: 'none', 
                    borderRadius: '5px', 
                    cursor: isProcessingSale ? 'not-allowed' : 'pointer',
                    opacity: isProcessingSale ? 0.7 : 1
                }}
                disabled={cart.length === 0 || isProcessingSale}
            >
                {isProcessingSale ? 'Procesando Venta...' : 'Finalizar Venta'}
            </button>
        </div>
    );
};

export default POSPage;
