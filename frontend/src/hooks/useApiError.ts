import { useState, useCallback } from 'react';
import { APIErrorHandler } from '../services/apiErrorHandler';
import { useReduxAuth } from './useReduxAuth';
import { 
  getCachedProductsList, 
  cacheProductsList, 
  getCachedProductSearch, 
  cacheProductSearch,
  invalidateProductsCache 
} from '../services/clientCache';

/**
 * Hook personalizado para manejo de errores de API
 */
export const useApiError = () => {
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { logout } = useReduxAuth();

  /**
   * Maneja errores de API con lógica específica
   */
  const handleApiError = useCallback((error: any) => {
    console.error('API Error:', error);

    // Si el error requiere reautenticación, cerrar sesión
    if (APIErrorHandler.requiresReauth(error)) {
      logout();
      return;
    }

    // Configurar el error para mostrar al usuario
    setError(error);
  }, [logout]);

  /**
   * Ejecuta una función async y maneja los errores automáticamente
   */
  const executeWithErrorHandling = useCallback(async <T>(
    apiCall: () => Promise<T>,
    options: {
      showError?: boolean;
      onSuccess?: (result: T) => void;
      onError?: (error: any) => void;
    } = {}
  ): Promise<T | undefined> => {
    const { showError = true, onSuccess, onError } = options;

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiCall();
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err: any) {
      if (showError) {
        handleApiError(err);
      }
      
      if (onError) {
        onError(err);
      }
      
      return undefined;
    } finally {
      setIsLoading(false);
    }
  }, [handleApiError]);

  /**
   * Limpia el error actual
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Verifica si un error es recuperable
   */
  const isRecoverable = error ? APIErrorHandler.isRecoverableError(error) : false;

  /**
   * Obtiene mensaje amigable del error
   */
  const userMessage = error ? APIErrorHandler.getUserFriendlyMessage(error) : '';

  return {
    error,
    isLoading,
    handleApiError,
    executeWithErrorHandling,
    clearError,
    isRecoverable,
    userMessage
  };
};

/**
 * Hook específico para operaciones de productos
 */
export const useProductsApi = () => {
  const { executeWithErrorHandling, ...errorState } = useApiError();

  const createProductWithErrorHandling = useCallback(async (
    productData: any,
    onSuccess?: () => void
  ) => {
    const { createProduct } = await import('../services/api');
    
    return executeWithErrorHandling(
      () => createProduct(productData),
      {
        onSuccess: () => {
          // Invalidar caché de productos al crear uno nuevo
          invalidateProductsCache();
          if (onSuccess) onSuccess();
        }
      }
    );
  }, [executeWithErrorHandling]);

  const updateProductWithErrorHandling = useCallback(async (
    productId: number,
    productData: any,
    onSuccess?: () => void
  ) => {
    const { updateProduct } = await import('../services/api');
    
    return executeWithErrorHandling(
      () => updateProduct(productId, productData),
      {
        onSuccess: () => {
          // Invalidar caché de productos al actualizar uno
          invalidateProductsCache();
          if (onSuccess) onSuccess();
        }
      }
    );
  }, [executeWithErrorHandling]);

  const getProductsWithErrorHandling = useCallback(async (
    skip: number = 0,
    limit: number = 20
  ) => {
    // Intentar obtener del caché primero
    const cachedResult = getCachedProductsList(skip, limit);
    if (cachedResult) {
      return cachedResult;
    }
    
    const { getProducts } = await import('../services/api');
    
    return executeWithErrorHandling(
      async () => {
        const result = await getProducts(skip, limit);
        // Cachear el resultado
        if (result) {
          cacheProductsList(result.products, skip, limit);
        }
        return result;
      }
    );
  }, [executeWithErrorHandling]);

  const searchProductsWithErrorHandling = useCallback(async (query: string) => {
    // Intentar obtener del caché primero
    const cachedResult = getCachedProductSearch(query);
    if (cachedResult) {
      return cachedResult;
    }
    
    const { searchProducts } = await import('../services/api');
    
    return executeWithErrorHandling(
      async () => {
        const result = await searchProducts(query);
        // Cachear el resultado
        if (result) {
          cacheProductSearch(query, result);
        }
        return result;
      },
      { showError: false } // No mostrar errores de búsqueda automáticamente
    );
  }, [executeWithErrorHandling]);

  return {
    ...errorState,
    createProduct: createProductWithErrorHandling,
    updateProduct: updateProductWithErrorHandling,
    getProducts: getProductsWithErrorHandling,
    searchProducts: searchProductsWithErrorHandling
  };
};

/**
 * Hook específico para operaciones de ventas
 */
export const useSalesApi = () => {
  const { executeWithErrorHandling, ...errorState } = useApiError();

  const processSaleWithErrorHandling = useCallback(async (
    saleData: any,
    onSuccess?: () => void
  ) => {
    const { postSale } = await import('../services/api');
    
    return executeWithErrorHandling(
      () => postSale(saleData),
      {
        onSuccess: () => {
          // Invalidar caché de productos al hacer una venta (cambia el stock)
          invalidateProductsCache();
          if (onSuccess) onSuccess();
        }
      }
    );
  }, [executeWithErrorHandling]);

  return {
    ...errorState,
    processSale: processSaleWithErrorHandling
  };
};