import React, { useState, useEffect } from 'react';
import { ProductCategory, ProductFilters as IProductFilters, CategoryInfo, BrandInfo, CATEGORY_NAMES, CATEGORY_ICONS } from '../types';
import { getProductCategories, getProductBrands } from '../services/api';

interface ProductFiltersProps {
  filters: IProductFilters;
  onFiltersChange: (filters: IProductFilters) => void;
  showAdvanced?: boolean;
}

const ProductFilters: React.FC<ProductFiltersProps> = ({
  filters,
  onFiltersChange,
  showAdvanced = false
}) => {
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [brands, setBrands] = useState<BrandInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Cargar categorías y marcas al montar el componente
  useEffect(() => {
    const loadFilterData = async () => {
      setIsLoading(true);
      try {
        const [categoriesData, brandsData] = await Promise.all([
          getProductCategories(),
          getProductBrands(filters.category)
        ]);
        setCategories(categoriesData);
        setBrands(brandsData);
      } catch (error) {
        console.error('Error loading filter data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadFilterData();
  }, [filters.category]);

  const handleFilterChange = (key: keyof IProductFilters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    
    // Si cambia la categoría, limpiar la marca
    if (key === 'category') {
      newFilters.brand = undefined;
    }
    
    onFiltersChange(newFilters);
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.values(filters).some(value => 
    value !== undefined && value !== null && value !== ''
  );

  return (
    <div style={{
      background: 'rgba(255, 255, 255, 0.05)',
      backdropFilter: 'blur(10px)',
      borderRadius: '16px',
      padding: '1.5rem',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      marginBottom: '1rem'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem'
      }}>
        <h3 style={{
          fontSize: '1.1rem',
          fontWeight: '600',
          color: '#ffffff',
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          🔍 Filtros de Productos
        </h3>
        
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            style={{
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fecaca',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              fontSize: '0.875rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
            }}
          >
            Limpiar Filtros
          </button>
        )}
      </div>

      {/* Grid de filtros */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: showAdvanced ? 'repeat(auto-fit, minmax(200px, 1fr))' : '1fr',
        gap: '1rem'
      }}>
        
        {/* Filtro por Categoría */}
        <div>
          <label style={{
            display: 'block',
            fontSize: '0.875rem',
            fontWeight: '600',
            color: 'rgba(255, 255, 255, 0.9)',
            marginBottom: '0.5rem'
          }}>
            Categoría:
          </label>
          <select
            value={filters.category || ''}
            onChange={(e) => handleFilterChange('category', e.target.value || undefined)}
            style={{
              width: '100%',
              padding: '0.75rem',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              color: '#ffffff',
              fontSize: '0.875rem',
              outline: 'none'
            }}
          >
            <option value="">Todas las categorías</option>
            {categories.map((cat) => (
              <option key={cat.category} value={cat.category} style={{ background: '#1a1a2e' }}>
                {CATEGORY_ICONS[cat.category as ProductCategory]} {cat.name} ({cat.count})
              </option>
            ))}
          </select>
        </div>

        {showAdvanced && (
          <>
            {/* Filtro por Marca */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: 'rgba(255, 255, 255, 0.9)',
                marginBottom: '0.5rem'
              }}>
                Marca:
              </label>
              <select
                value={filters.brand || ''}
                onChange={(e) => handleFilterChange('brand', e.target.value || undefined)}
                disabled={isLoading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.875rem',
                  outline: 'none',
                  opacity: isLoading ? 0.5 : 1
                }}
              >
                <option value="">Todas las marcas</option>
                {brands.map((brand) => (
                  <option key={brand.brand} value={brand.brand} style={{ background: '#1a1a2e' }}>
                    {brand.brand} ({brand.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Filtro por Precio */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: 'rgba(255, 255, 255, 0.9)',
                marginBottom: '0.5rem'
              }}>
                Precio:
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.min_price || ''}
                  onChange={(e) => handleFilterChange('min_price', e.target.value ? parseFloat(e.target.value) : undefined)}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '0.875rem',
                    outline: 'none'
                  }}
                />
                <span style={{ color: 'rgba(255, 255, 255, 0.6)' }}>-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.max_price || ''}
                  onChange={(e) => handleFilterChange('max_price', e.target.value ? parseFloat(e.target.value) : undefined)}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '0.875rem',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Filtro Solo en Stock */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: 'rgba(255, 255, 255, 0.9)',
                marginBottom: '0.5rem'
              }}>
                Disponibilidad:
              </label>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'rgba(255, 255, 255, 0.8)',
                cursor: 'pointer'
              }}>
                <input
                  type="checkbox"
                  checked={filters.in_stock || false}
                  onChange={(e) => handleFilterChange('in_stock', e.target.checked || undefined)}
                  style={{
                    width: '1rem',
                    height: '1rem',
                    accentColor: '#667eea'
                  }}
                />
                Solo productos en stock
              </label>
            </div>
          </>
        )}
      </div>

      {/* Indicador de filtros activos */}
      {hasActiveFilters && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          background: 'rgba(102, 126, 234, 0.1)',
          border: '1px solid rgba(102, 126, 234, 0.3)',
          borderRadius: '8px',
          fontSize: '0.875rem',
          color: 'rgba(255, 255, 255, 0.8)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ color: '#667eea', fontWeight: '600' }}>Filtros activos:</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {filters.category && (
              <span style={{
                background: 'rgba(102, 126, 234, 0.2)',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem'
              }}>
                {CATEGORY_NAMES[filters.category as ProductCategory]}
              </span>
            )}
            {filters.brand && (
              <span style={{
                background: 'rgba(16, 185, 129, 0.2)',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem'
              }}>
                {filters.brand}
              </span>
            )}
            {(filters.min_price || filters.max_price) && (
              <span style={{
                background: 'rgba(245, 158, 11, 0.2)',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem'
              }}>
                ${filters.min_price || 0} - ${filters.max_price || '∞'}
              </span>
            )}
            {filters.in_stock && (
              <span style={{
                background: 'rgba(16, 185, 129, 0.2)',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem'
              }}>
                Solo en stock
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductFilters;