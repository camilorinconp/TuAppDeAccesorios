// /frontend/src/components/ShoppingCart.tsx
import React from 'react';
import { CartItem } from '../types';

interface Props {
    cartItems: CartItem[];
}

const ShoppingCart: React.FC<Props> = ({ cartItems }) => {
    const total = cartItems.reduce((acc, item) => acc + item.selling_price * item.quantity_in_cart, 0);

    return (
        <div style={{ marginTop: '20px' }}>
            <h2>Carrito de Compras</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>Producto</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>Cantidad</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>Precio Unit.</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {cartItems.map(item => (
                        <tr key={item.id}>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.name}</td>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.quantity_in_cart}</td>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>${item.selling_price.toFixed(2)}</td>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>${(item.selling_price * item.quantity_in_cart).toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <h3>Total: ${total.toFixed(2)}</h3>
        </div>
    );
};

export default ShoppingCart;
