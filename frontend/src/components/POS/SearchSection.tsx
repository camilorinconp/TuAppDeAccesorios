// ==================================================================
// SEARCH SECTION - SECCIÓN DE BÚSQUEDA DE PRODUCTOS
// ==================================================================

import React from 'react';
import { Product } from '../../types/core';

interface SearchSectionProps {
  query: string;
  results: Product[];
  isLoading: boolean;
  onQueryChange: (query: string) => void;
  onProductSelect: (product: Product) => void;
}

export const SearchSection: React.FC<SearchSectionProps> = ({
  query,
  results,
  isLoading,
  onQueryChange,
  onProductSelect,
}) => {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && results.length > 0) {
      onProductSelect(results[0]);
    }
  };

  return (
    <div className="search-section">
      <div className="search-input-container">
        <input
          type="text"
          placeholder="Buscar producto por nombre o SKU..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyPress={handleKeyPress}
          className="search-input"
        />
        <button 
          className="search-button"
          disabled={!query.trim() || isLoading}
        >
          {isLoading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>

      <div className="search-results">
        <h3>Resultados de Búsqueda</h3>
        {isLoading ? (
          <div className="loading">Buscando productos...</div>
        ) : results.length === 0 ? (
          <div className="no-results">No hay resultados.</div>
        ) : (
          <div className="results-list">
            {results.map((product) => (
              <div 
                key={product.id} 
                className="product-item"
                onClick={() => onProductSelect(product)}
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
  );
};