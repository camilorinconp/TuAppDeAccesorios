import { useState, useCallback } from 'react';
import { getProductNameSuggestions } from '../services/api';

interface AutocompleteState {
  suggestions: string[];
  isLoading: boolean;
  error: string | null;
  showSuggestions: boolean;
}

export const useProductNameAutocomplete = () => {
  const [state, setState] = useState<AutocompleteState>({
    suggestions: [],
    isLoading: false,
    error: null,
    showSuggestions: false
  });

  const getSuggestions = useCallback(async (query: string) => {
    // No buscar si la consulta es muy corta
    if (!query || query.trim().length < 2) {
      setState(prev => ({
        ...prev,
        suggestions: [],
        showSuggestions: false,
        error: null
      }));
      return;
    }

    setState(prev => ({
      ...prev,
      isLoading: true,
      error: null
    }));

    try {
      const result = await getProductNameSuggestions(query.trim(), 8);
      
      setState(prev => ({
        ...prev,
        suggestions: result.suggestions,
        showSuggestions: result.suggestions.length > 0,
        isLoading: false,
        error: null
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        suggestions: [],
        showSuggestions: false,
        isLoading: false,
        error: 'Error al obtener sugerencias'
      }));
    }
  }, []);

  // Debounce para evitar demasiadas peticiones
  const debouncedGetSuggestions = useCallback(
    debounce(getSuggestions, 300), // 300ms de delay
    [getSuggestions]
  );

  const hideSuggestions = useCallback(() => {
    setState(prev => ({
      ...prev,
      showSuggestions: false
    }));
  }, []);

  const clearSuggestions = useCallback(() => {
    setState({
      suggestions: [],
      isLoading: false,
      error: null,
      showSuggestions: false
    });
  }, []);

  return {
    ...state,
    getSuggestions: debouncedGetSuggestions,
    hideSuggestions,
    clearSuggestions
  };
};

// Función debounce
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | undefined;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = window.setTimeout(() => func(...args), wait);
  };
}