// /frontend/src/components/PointOfSaleView.tsx
import React, { useState } from 'react';
import { Product, CartItem } from '../types';
import { postSale } from '../services/api';
import ProductSearch from './ProductSearch';
import ShoppingCart from './ShoppingCart';

const PointOfSaleView: React.FC = () => {
    const [cart, setCart] = useState<CartItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleAddProduct = (product: Product) => {
        setCart(prevCart => {
            const existingItem = prevCart.find(item => item.id === product.id);
            if (existingItem) {
                // Incrementar cantidad si el producto ya está en el carrito
                return prevCart.map(item =>
                    item.id === product.id
                        ? { ...item, quantity_in_cart: item.quantity_in_cart + 1 }
                        : item
                );
            } else {
                // Añadir nuevo producto al carrito
                return [...prevCart, { ...product, quantity_in_cart: 1 }];
            }
        });
    };

    const handleFinalizeSale = async () => {
        if (cart.length === 0) {
            setError("El carrito está vacío.");
            return;
        }

        const salePayload = {
            user_id: 1, // Hardcodeado por ahora, debería venir del estado de auth
            items: cart.map(item => ({
                product_id: item.id,
                quantity_sold: item.quantity_in_cart,
                price_at_time_of_sale: item.selling_price,
            })),
            total_amount: cart.reduce((acc, item) => acc + item.selling_price * item.quantity_in_cart, 0),
        };

        try {
            await postSale(salePayload);
            setSuccess("¡Venta registrada con éxito!");
            setCart([]); // Limpiar carrito
            setError(null);
        } catch (err) {
            setError("Error al registrar la venta. Verifique el stock.");
            setSuccess(null);
        }
    };

    return (
        <div style={{ padding: '20px' }}>
            <h1>Punto de Venta</h1>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {success && <p style={{ color: 'green' }}>{success}</p>}
            
            <ProductSearch onAddProduct={handleAddProduct} />
            
            <ShoppingCart cartItems={cart} />

            <button 
                onClick={handleFinalizeSale} 
                style={{ marginTop: '20px', padding: '10px 20px', fontSize: '1.2em' }}
            >
                Finalizar Venta
            </button>
        </div>
    );
};

export default PointOfSaleView;
