import React, { useState, useEffect } from 'react';
import { ProductCategory, CategoryInfo, CATEGORY_NAMES, CATEGORY_ICONS } from '../types';
import { getProductCategories } from '../services/api';

interface CategoryGridProps {
  selectedCategory?: ProductCategory;
  onCategorySelect: (category?: ProductCategory) => void;
  showAllOption?: boolean;
}

const CategoryGrid: React.FC<CategoryGridProps> = ({
  selectedCategory,
  onCategorySelect,
  showAllOption = true
}) => {
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const loadCategories = async () => {
      setIsLoading(true);
      try {
        const data = await getProductCategories();
        setCategories(data);
      } catch (error) {
        console.error('Error loading categories:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadCategories();
  }, []);

  const handleCategoryClick = (category?: ProductCategory) => {
    onCategorySelect(category);
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '2rem',
        color: 'rgba(255, 255, 255, 0.6)'
      }}>
        <div style={{
          width: '2rem',
          height: '2rem',
          border: '2px solid rgba(255, 255, 255, 0.3)',
          borderTop: '2px solid #667eea',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <span style={{ marginLeft: '0.5rem' }}>Cargando categorías...</span>
      </div>
    );
  }

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
        marginBottom: '1rem',
        textAlign: 'center'
      }}>
        <h3 style={{
          fontSize: '1.1rem',
          fontWeight: '600',
          color: '#ffffff',
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem'
        }}>
          📂 Categorías de Productos
        </h3>
        <p style={{
          fontSize: '0.875rem',
          color: 'rgba(255, 255, 255, 0.6)',
          margin: '0.5rem 0 0',
        }}>
          Selecciona una categoría para filtrar los productos
        </p>
      </div>

      {/* Grid de categorías */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '0.75rem'
      }}>
        {/* Opción "Todas" */}
        {showAllOption && (
          <button
            onClick={() => handleCategoryClick(undefined)}
            style={{
              background: selectedCategory === undefined 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : 'rgba(255, 255, 255, 0.1)',
              border: selectedCategory === undefined 
                ? '1px solid #667eea'
                : '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              padding: '1rem',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              color: '#ffffff',
              textAlign: 'center',
              minHeight: '100px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
            onMouseEnter={(e) => {
              if (selectedCategory !== undefined) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedCategory !== undefined) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            <div style={{ fontSize: '2rem' }}>🗂️</div>
            <div style={{
              fontSize: '0.875rem',
              fontWeight: '600',
              lineHeight: '1.2'
            }}>
              Todas
            </div>
            <div style={{
              fontSize: '0.75rem',
              color: 'rgba(255, 255, 255, 0.7)'
            }}>
              {categories.reduce((total, cat) => total + cat.count, 0)} productos
            </div>
          </button>
        )}

        {/* Categorías dinámicas */}
        {categories.map((category) => (
          <button
            key={category.category}
            onClick={() => handleCategoryClick(category.category as ProductCategory)}
            style={{
              background: selectedCategory === category.category
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : 'rgba(255, 255, 255, 0.1)',
              border: selectedCategory === category.category
                ? '1px solid #667eea'
                : '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              padding: '1rem',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              color: '#ffffff',
              textAlign: 'center',
              minHeight: '100px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
            onMouseEnter={(e) => {
              if (selectedCategory !== category.category) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedCategory !== category.category) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            <div style={{ fontSize: '2rem' }}>
              {CATEGORY_ICONS[category.category as ProductCategory]}
            </div>
            <div style={{
              fontSize: '0.875rem',
              fontWeight: '600',
              lineHeight: '1.2'
            }}>
              {category.name}
            </div>
            <div style={{
              fontSize: '0.75rem',
              color: 'rgba(255, 255, 255, 0.7)'
            }}>
              {category.count} productos
            </div>
          </button>
        ))}
      </div>

      {/* Información adicional */}
      {selectedCategory && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          background: 'rgba(102, 126, 234, 0.1)',
          border: '1px solid rgba(102, 126, 234, 0.3)',
          borderRadius: '8px',
          fontSize: '0.875rem',
          color: 'rgba(255, 255, 255, 0.8)',
          textAlign: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>
              {CATEGORY_ICONS[selectedCategory]}
            </span>
            <span style={{ fontWeight: '600', color: '#667eea' }}>
              Mostrando productos de: {CATEGORY_NAMES[selectedCategory]}
            </span>
          </div>
          <div style={{ marginTop: '0.25rem', fontSize: '0.75rem' }}>
            {categories.find(cat => cat.category === selectedCategory)?.description}
          </div>
        </div>
      )}

      {/* CSS para animación de carga */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `
      }} />
    </div>
  );
};

export default CategoryGrid;