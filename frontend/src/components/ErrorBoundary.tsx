import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * Componente ErrorBoundary para capturar errores de React
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Actualiza el state para mostrar la UI de error
    return { 
      hasError: true,
      error 
    };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Registrar el error
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // Llamar callback si está definido
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // En producción, enviar el error a un servicio de monitoreo
    if (process.env.NODE_ENV === 'production') {
      // Aquí se podría enviar a Sentry, LogRocket, etc.
      this.logErrorToService(error, errorInfo);
    }
  }

  private logErrorToService(error: Error, errorInfo: ErrorInfo) {
    // Implementar logging a servicio externo
    console.log('Logging error to external service:', {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack
    });
  }

  override render() {
    if (this.state.hasError) {
      // Mostrar fallback personalizado si se proporciona
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // UI de error por defecto
      return (
        <div style={{
          padding: '20px',
          margin: '20px',
          border: '2px solid #ff6b6b',
          borderRadius: '8px',
          backgroundColor: '#ffe0e0',
          textAlign: 'center'
        }}>
          <h2 style={{ color: '#d63031', marginBottom: '16px' }}>
            ¡Oops! Algo salió mal
          </h2>
          <p style={{ color: '#2d3436', marginBottom: '16px' }}>
            Ha ocurrido un error inesperado. Por favor, recarga la página o inténtalo más tarde.
          </p>
          
          <div style={{ marginBottom: '16px' }}>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '10px 20px',
                backgroundColor: '#74b9ff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                marginRight: '10px'
              }}
            >
              Recargar Página
            </button>
            
            <button
              onClick={() => this.setState({ hasError: false })}
              style={{
                padding: '10px 20px',
                backgroundColor: '#00b894',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Intentar de Nuevo
            </button>
          </div>

          {/* Mostrar detalles del error en desarrollo */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details style={{ textAlign: 'left', marginTop: '16px' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
                Detalles del Error (Solo en Desarrollo)
              </summary>
              <pre style={{
                backgroundColor: '#2d3436',
                color: '#ddd',
                padding: '10px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                marginTop: '8px'
              }}>
                {this.state.error.stack}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

/**
 * Hook para manejar errores en componentes funcionales
 */
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  const handleError = React.useCallback((error: Error) => {
    console.error('Error handled by useErrorHandler:', error);
    setError(error);
  }, []);

  const clearError = React.useCallback(() => {
    setError(null);
  }, []);

  // Si hay un error, lanzarlo para que sea capturado por ErrorBoundary
  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { handleError, clearError };
};