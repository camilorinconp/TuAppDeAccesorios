import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useProductNameAutocomplete } from '../hooks/useProductNameAutocomplete';

interface ProductNameAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  style?: React.CSSProperties;
}

const ProductNameAutocomplete: React.FC<ProductNameAutocompleteProps> = ({
  value,
  onChange,
  placeholder = "Nombre del Producto (ej: Funda iPhone 14)",
  required = false,
  style = {}
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const {
    suggestions,
    isLoading,
    showSuggestions,
    getSuggestions,
    hideSuggestions
  } = useProductNameAutocomplete();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    getSuggestions(newValue);
    setSelectedIndex(-1);
  };

  const handleInputFocus = () => {
    setIsFocused(true);
    if (value && value.length >= 2) {
      getSuggestions(value);
    }
  };

  const handleInputBlur = () => {
    // Delay para permitir click en sugerencias
    setTimeout(() => {
      if (!containerRef.current?.contains(document.activeElement)) {
        setIsFocused(false);
        hideSuggestions();
      }
    }, 150);
  };

  const handleSuggestionClick = useCallback((suggestion: string) => {
    // Llamar onChange inmediatamente
    onChange(suggestion);
    
    // Limpiar estado
    hideSuggestions();
    setSelectedIndex(-1);
    setIsFocused(false);
    
    // Mantener el foco en el input
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [onChange, hideSuggestions]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      
      case 'Enter':
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          e.preventDefault();
          handleSuggestionClick(suggestions[selectedIndex]);
        }
        break;
      
      case 'Escape':
        hideSuggestions();
        setSelectedIndex(-1);
        break;
    }
  };

  // Cerrar sugerencias cuando se hace clic fuera
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        hideSuggestions();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [hideSuggestions]);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
      <input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
        onKeyDown={handleKeyDown}
        required={required}
        className="input"
        style={style}
      />
      
      {/* Indicador de carga */}
      {isLoading && isFocused && (
        <div style={{
          position: 'absolute',
          right: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          fontSize: '12px',
          color: 'var(--text-tertiary)'
        }}>
          🔍
        </div>
      )}

      {/* Lista de sugerencias */}
      {showSuggestions && isFocused && suggestions.length > 0 && (
        <div className="dropdown-content" style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          maxHeight: '200px',
          overflowY: 'auto',
          zIndex: 1000,
          opacity: 1,
          visibility: 'visible',
          transform: 'translateY(0)'
        }}>
          {suggestions.map((suggestion, index) => (
            <div
              key={`suggestion-${index}`}
              onMouseDown={(e) => {
                // Crucial: Prevenir el blur del input
                e.preventDefault();
                e.stopPropagation();
                handleSuggestionClick(suggestion);
              }}
              className="dropdown-item"
              style={{
                backgroundColor: index === selectedIndex ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                borderBottom: index < suggestions.length - 1 ? '1px solid var(--border-color)' : 'none',
                cursor: 'pointer'
              }}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              {suggestion}
            </div>
          ))}
        </div>
      )}

      {/* Hint cuando no hay sugerencias pero el usuario está escribiendo */}
      {isFocused && value.length >= 2 && !isLoading && suggestions.length === 0 && (
        <div className="alert alert-info" style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          padding: '8px 12px',
          fontSize: '12px',
          zIndex: 1000,
          margin: 0,
          borderRadius: '0 0 var(--radius-lg) var(--radius-lg)'
        }}>
          💡 Escribe palabras como "funda", "cable", "protector", etc.
        </div>
      )}
    </div>
  );
};

export default ProductNameAutocomplete;