import { useState, useCallback } from 'react';
import { checkSkuAvailability } from '../services/api';

interface SkuValidationState {
  isValidating: boolean;
  isAvailable: boolean | null;
  message: string;
  error: string | null;
}

export const useSkuValidation = (excludeProductId?: number) => {
  const [validationState, setValidationState] = useState<SkuValidationState>({
    isValidating: false,
    isAvailable: null,
    message: '',
    error: null
  });

  const validateSku = useCallback(async (sku: string) => {
    // Limpiar estado si SKU está vacío
    if (!sku || sku.trim().length < 3) {
      setValidationState({
        isValidating: false,
        isAvailable: null,
        message: '',
        error: null
      });
      return;
    }

    setValidationState(prev => ({
      ...prev,
      isValidating: true,
      error: null
    }));

    try {
      const result = await checkSkuAvailability(sku);
      
      setValidationState({
        isValidating: false,
        isAvailable: result.available,
        message: result.message,
        error: null
      });
    } catch (error) {
      setValidationState({
        isValidating: false,
        isAvailable: null,
        message: '',
        error: 'Error al verificar SKU'
      });
    }
  }, [excludeProductId]);

  // Debounce para evitar demasiadas peticiones
  const debouncedValidateSku = useCallback(
    debounce(validateSku, 500), // 500ms de delay
    [validateSku]
  );

  return {
    ...validationState,
    validateSku: debouncedValidateSku,
    clearValidation: () => setValidationState({
      isValidating: false,
      isAvailable: null,
      message: '',
      error: null
    })
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