import React, { useState, useEffect, useCallback } from 'react';
import { Product, SalePayload } from '../types';
import { searchProducts, postSale } from '../services/api';
// import { useCartState } from '../hooks/useCartState'; // Temporarily disabled - useCartState is deprecated
import CartDisplay from '../components/CartDisplay';

const POSPage: React.FC = () => {
    const [query, setQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Product[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [isProcessingSale, setIsProcessingSale] = useState(false);
    
    // const { cart, addToCart, removeFromCart, clearCart, totalAmount } = useCartState(); // Temporarily disabled
    const [cart, setCart] = useState<Product[]>([]);
    const [totalAmount, setTotalAmount] = useState(0);

    useEffect(() => {
        // Cart updated
    }, [cart]);

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            if (query.trim() !== '') {
                performSearch();
            } else {
                setSearchResults([]);
            }
        }, 300);
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
        if (isProcessingSale || cart.length === 0) {
            setError(cart.length === 0 ? "El carrito está vacío." : "Venta en proceso...");
            return;
        }

        setIsProcessingSale(true);
        setError(null);

        const salePayload: SalePayload = {
            user_id: 1,
            items: cart.map(item => ({
                product_id: item.id,
                quantity_sold: item.quantity_in_cart,
                price_at_time_of_sale: item.selling_price,
            })),
            total_amount: totalAmount,
        };

        try {
            const result = await postSale(salePayload);
            
            // Limpieza simple
            clearCart();
            setQuery('');
            setSearchResults([]);
            setSuccess("¡Venta registrada con éxito! Inventario actualizado automáticamente.");
            setTimeout(() => setSuccess(null), 3000);
            
        } catch (err: any) {
            console.error('❌ Error:', err);
            setError(`Error al registrar la venta: ${err.message || 'Error desconocido'}`);
        } finally {
            setIsProcessingSale(false);
        }
    }, [cart, totalAmount, isProcessingSale, clearCart]);

    return (
        <div style={{ padding: '20px' }}>
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

            <CartDisplay 
                key={cartRenderKey}
                cart={cart}
                totalAmount={totalAmount}
                onRemoveItem={removeFromCart}
            />

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