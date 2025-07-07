/**
 * Manejo centralizado de errores de API
 */

export interface APIError {
  message: string;
  type: string;
  details: Record<string, any>;
  status?: number;
}

export class APIErrorHandler {
  /**
   * Procesa errores de respuesta de la API
   */
  static async handleResponse(response: Response): Promise<any> {
    if (response.ok) {
      return response.json();
    }

    let errorData: APIError;
    
    try {
      errorData = await response.json();
    } catch {
      // Si no se puede parsear el JSON, crear error genérico
      errorData = {
        message: `Error ${response.status}: ${response.statusText}`,
        type: 'http_error',
        details: {},
        status: response.status
      };
    }

    // Agregar código de estado si no está presente
    if (!errorData.status) {
      errorData.status = response.status;
    }

    // Procesar tipos específicos de error
    throw this.createErrorFromAPIResponse(errorData);
  }

  /**
   * Crea una instancia de error específica basada en la respuesta de la API
   */
  private static createErrorFromAPIResponse(errorData: APIError): Error {
    const error = new Error(errorData.message);
    (error as any).type = errorData.type;
    (error as any).details = errorData.details;
    (error as any).status = errorData.status;
    
    return error;
  }

  /**
   * Maneja errores de red y otros errores inesperados
   */
  static handleNetworkError(error: any): Error {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      const networkError = new Error('Error de conexión. Verifica tu conexión a internet.');
      (networkError as any).type = 'network_error';
      (networkError as any).details = {};
      return networkError;
    }

    if (error.name === 'AbortError') {
      const timeoutError = new Error('La petición tardó demasiado tiempo. Inténtalo de nuevo.');
      (timeoutError as any).type = 'timeout_error';
      (timeoutError as any).details = {};
      return timeoutError;
    }

    // Si ya es un error procesado, devolverlo tal como está
    if ((error as any).type) {
      return error;
    }

    // Error genérico
    const genericError = new Error('Ocurrió un error inesperado');
    (genericError as any).type = 'unknown_error';
    (genericError as any).details = { originalError: error.message };
    return genericError;
  }

  /**
   * Obtiene un mensaje de error amigable para el usuario
   */
  static getUserFriendlyMessage(error: any): string {
    const errorType = (error as any).type;
    const errorDetails = (error as any).details || {};

    switch (errorType) {
      case 'validation_error':
        if (errorDetails.validation_errors && Array.isArray(errorDetails.validation_errors)) {
          return `Error de validación: ${errorDetails.validation_errors[0]?.msg || error.message}`;
        }
        return `Datos inválidos: ${error.message}`;

      case 'not_found_error':
        return 'El recurso solicitado no fue encontrado';

      case 'duplicate_error':
        return 'Ya existe un recurso con esos datos';

      case 'insufficient_stock_error':
        if (errorDetails.insufficient_items) {
          const items = errorDetails.insufficient_items;
          const itemMessages = items.map((item: any) => 
            `${item.product_name}: disponible ${item.available}, solicitado ${item.requested}`
          );
          return `Stock insuficiente:\n${itemMessages.join('\n')}`;
        }
        return 'Stock insuficiente para completar la operación';

      case 'business_logic_error':
        return `Error en la operación: ${error.message}`;

      case 'authentication_error':
        return 'Error de autenticación. Por favor, inicia sesión nuevamente';

      case 'authorization_error':
        return 'No tienes permisos para realizar esta acción';

      case 'database_integrity_error':
        return 'Error de integridad en los datos. Verifica la información';

      case 'database_error':
        return 'Error en la base de datos. Inténtalo más tarde';

      case 'network_error':
        return 'Error de conexión. Verifica tu conexión a internet';

      case 'timeout_error':
        return 'La operación tardó demasiado tiempo. Inténtalo de nuevo';

      case 'internal_server_error':
        return 'Error interno del servidor. Inténtalo más tarde';

      default:
        return error.message || 'Ocurrió un error inesperado';
    }
  }

  /**
   * Determina si un error es recuperable (el usuario puede intentar de nuevo)
   */
  static isRecoverableError(error: any): boolean {
    const errorType = (error as any).type;
    const status = (error as any).status;

    // Errores de red y timeout son recuperables
    if (errorType === 'network_error' || errorType === 'timeout_error') {
      return true;
    }

    // Errores 5xx del servidor son recuperables
    if (status >= 500) {
      return true;
    }

    // Errores 4xx generalmente no son recuperables (excepto 408, 429)
    if (status === 408 || status === 429) {
      return true;
    }

    return false;
  }

  /**
   * Determina si el error requiere reautenticación
   */
  static requiresReauth(error: any): boolean {
    const status = (error as any).status;
    const errorType = (error as any).type;

    return status === 401 || errorType === 'authentication_error';
  }
}

/**
 * Wrapper para fetch que maneja errores automáticamente
 */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<any> {
  try {
    // Agregar timeout por defecto
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 segundos

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      credentials: 'include' // Incluir cookies por defecto
    });

    clearTimeout(timeoutId);
    return await APIErrorHandler.handleResponse(response);

  } catch (error) {
    throw APIErrorHandler.handleNetworkError(error);
  }
}