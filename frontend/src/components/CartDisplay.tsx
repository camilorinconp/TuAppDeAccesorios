import React from 'react';
import { CartItem } from '../types';

interface CartDisplayProps {
    cart: CartItem[];
    totalAmount: number;
    onRemoveItem: (productId: number) => void;
}

const CartDisplay: React.FC<CartDisplayProps> = ({ cart, totalAmount, onRemoveItem }) => {
    
    if (cart.length === 0) {
        return (
            <div style={{ marginBottom: '20px', border: '1px solid #ccc', padding: '10px' }}>
                <h2>Carrito de Compras</h2>
                <div>
                    <p>El carrito está vacío.</p>
                </div>
                <h3 style={{ textAlign: 'right', marginTop: '10px' }}>Total: $0</h3>
            </div>
        );
    }

    return (
        <div style={{ marginBottom: '20px', border: '1px solid #ccc', padding: '10px' }}>
            <h2>Carrito de Compras ({cart.length} productos)</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr>
                        <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>Producto</th>
                        <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>Cantidad</th>
                        <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>Precio Unit.</th>
                        <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>Subtotal</th>
                        <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {cart.map(item => (
                        <tr key={item.id}>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.name}</td>
                            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.quantity_in_cart}</td>
                            <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'right' }}>
                                ${item.selling_price.toLocaleString('es-CO')}
                            </td>
                            <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'right' }}>
                                ${(item.selling_price * item.quantity_in_cart).toLocaleString('es-CO')}
                            </td>
                            <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                                <button onClick={() => onRemoveItem(item.id)}>Eliminar</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <h3 style={{ textAlign: 'right', marginTop: '10px' }}>
                Total: ${totalAmount === 0 ? '0' : totalAmount.toLocaleString('es-CO')}
            </h3>
        </div>
    );
};

export default CartDisplay;