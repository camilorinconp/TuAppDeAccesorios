import React, { useState, useEffect } from 'react';
import { APIErrorHandler } from '../services/apiErrorHandler';

interface ErrorNotificationProps {
  error: Error | null;
  onClose: () => void;
  autoClose?: boolean;
  autoCloseDelay?: number;
}

/**
 * Componente para mostrar notificaciones de error
 */
const ErrorNotification: React.FC<ErrorNotificationProps> = ({
  error,
  onClose,
  autoClose = true,
  autoCloseDelay = 5000
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (error) {
      setIsVisible(true);
      
      if (autoClose) {
        const timer = setTimeout(() => {
          handleClose();
        }, autoCloseDelay);

        return () => clearTimeout(timer);
      }
    } else {
      setIsVisible(false);
    }
    
    return undefined;
  }, [error, autoClose, autoCloseDelay]);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(onClose, 300); // Delay para animación
  };

  const handleRetry = () => {
    // Aquí se podría implementar lógica de retry específica
    handleClose();
  };

  if (!error || !isVisible) {
    return null;
  }

  const errorType = (error as any).type || 'unknown_error';
  const isRecoverable = APIErrorHandler.isRecoverableError(error);
  const userMessage = APIErrorHandler.getUserFriendlyMessage(error);

  const getErrorClasses = () => {
    switch (errorType) {
      case 'validation_error':
        return 'alert alert-warning';
      case 'authentication_error':
      case 'authorization_error':
        return 'alert alert-error';
      case 'network_error':
      case 'timeout_error':
        return 'alert alert-info';
      case 'insufficient_stock_error':
        return 'alert alert-warning';
      default:
        return 'alert alert-error';
    }
  };

  const getNotificationStyle = () => {
    return {
      position: 'fixed' as const,
      top: '24px',
      right: '24px',
      maxWidth: '420px',
      zIndex: 1000,
      animation: isVisible ? 'slideIn 0.3s ease-out' : 'slideOut 0.3s ease-in',
      boxShadow: 'var(--shadow-2xl)',
      backdropFilter: 'blur(20px)'
    };
  };

  return (
    <>
      <style>
        {`
          @keyframes slideIn {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
          
          @keyframes slideOut {
            from {
              transform: translateX(0);
              opacity: 1;
            }
            to {
              transform: translateX(100%);
              opacity: 0;
            }
          }
        `}
      </style>
      
      <div className={getErrorClasses()} style={getNotificationStyle()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, marginRight: '12px' }}>
            <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: 'var(--text-sm)' }}>
              {getErrorTitle(errorType)}
            </div>
            <div style={{ whiteSpace: 'pre-line', fontSize: 'var(--text-sm)' }}>
              {userMessage}
            </div>
          </div>
          
          <button
            onClick={handleClose}
            className="btn btn-ghost btn-sm"
            style={{
              minWidth: 'auto',
              width: '32px',
              height: '32px',
              padding: '0',
              fontSize: '18px'
            }}
            title="Cerrar"
          >
            ×
          </button>
        </div>

        {/* Botones de acción */}
        <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
          {isRecoverable && (
            <button
              onClick={handleRetry}
              className="btn btn-outline btn-sm"
            >
              🔄 Reintentar
            </button>
          )}
          
          <button
            onClick={handleClose}
            className="btn btn-ghost btn-sm"
          >
            Cerrar
          </button>
        </div>

        {/* Barra de progreso para auto-close */}
        {autoClose && (
          <div className="progress" style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '3px',
            borderRadius: '0 0 var(--radius-lg) var(--radius-lg)'
          }}>
            <div 
              className="progress-bar"
              style={{
                width: '100%',
                animation: `shrink ${autoCloseDelay}ms linear`
              }}
            />
          </div>
        )}
      </div>
      
      <style>
        {`
          @keyframes shrink {
            from { width: 100%; }
            to { width: 0%; }
          }
        `}
      </style>
    </>
  );
};

/**
 * Obtiene el título apropiado según el tipo de error
 */
const getErrorTitle = (errorType: string): string => {
  switch (errorType) {
    case 'validation_error':
      return 'Error de Validación';
    case 'not_found_error':
      return 'No Encontrado';
    case 'duplicate_error':
      return 'Recurso Duplicado';
    case 'insufficient_stock_error':
      return 'Stock Insuficiente';
    case 'authentication_error':
      return 'Error de Autenticación';
    case 'authorization_error':
      return 'Sin Permisos';
    case 'network_error':
      return 'Error de Conexión';
    case 'timeout_error':
      return 'Tiempo Agotado';
    case 'business_logic_error':
      return 'Error en la Operación';
    case 'database_error':
      return 'Error de Base de Datos';
    case 'internal_server_error':
      return 'Error del Servidor';
    default:
      return 'Error';
  }
};

export default ErrorNotification;