import React, { useState, useEffect, useCallback } from 'react';
import { Product } from '../types';
import { searchProducts } from '../services/api';

interface Props {
    onAddProduct: (product: Product) => void;
}

const ProductSearch: React.FC<Props> = ({ onAddProduct }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Product[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Debounced search function
    const debouncedSearch = useCallback(
        async (searchQuery: string) => {
            if (searchQuery.trim() === '') {
                setResults([]);
                setLoading(false);
                return;
            }

            setLoading(true);
            setError(null);

            try {
                const foundProducts = await searchProducts(searchQuery);
                setResults(foundProducts);
            } catch (err) {
                setError('Error al buscar productos');
                setResults([]);
            } finally {
                setLoading(false);
            }
        },
        []
    );

    // Effect para debouncing
    useEffect(() => {
        const timer = setTimeout(() => {
            debouncedSearch(query);
        }, 300); // 300ms de delay

        return () => clearTimeout(timer);
    }, [query, debouncedSearch]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setQuery(e.target.value);
    };

    return (
        <div>
            <div style={{ position: 'relative' }}>
                <input
                    type="text"
                    value={query}
                    onChange={handleInputChange}
                    placeholder="Buscar por nombre o SKU..."
                    style={{ 
                        padding: '10px', 
                        width: '300px',
                        borderRadius: '4px',
                        border: '1px solid #ccc'
                    }}
                />
                {loading && (
                    <div style={{ 
                        position: 'absolute', 
                        right: '10px', 
                        top: '50%', 
                        transform: 'translateY(-50%)',
                        fontSize: '12px',
                        color: '#666'
                    }}>
                        Buscando...
                    </div>
                )}
            </div>
            
            {error && (
                <div style={{ 
                    color: 'red', 
                    fontSize: '14px', 
                    marginTop: '5px' 
                }}>
                    {error}
                </div>
            )}
            
            <div style={{ 
                marginTop: '10px', 
                border: '1px solid #ccc', 
                minHeight: '100px',
                borderRadius: '4px',
                backgroundColor: '#f9f9f9'
            }}>
                {query.trim() && results.length === 0 && !loading && (
                    <div style={{ 
                        padding: '20px', 
                        textAlign: 'center', 
                        color: '#666' 
                    }}>
                        No se encontraron productos
                    </div>
                )}
                {results.map(product => (
                    <div key={product.id} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        padding: '10px',
                        borderBottom: '1px solid #eee',
                        backgroundColor: 'white',
                        margin: '5px',
                        borderRadius: '4px'
                    }}>
                        <span>
                            <strong>{product.name}</strong> ({product.sku})<br/>
                            <small>Precio: ${product.selling_price} - Stock: {product.stock_quantity}</small>
                        </span>
                        <button 
                            onClick={() => onAddProduct(product)}
                            style={{
                                padding: '5px 10px',
                                backgroundColor: '#007bff',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            Añadir
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ProductSearch;