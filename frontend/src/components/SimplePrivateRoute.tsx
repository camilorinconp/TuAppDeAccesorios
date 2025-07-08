import React from 'react';
import { Navigate } from 'react-router-dom';

// Versión simplificada del PrivateRoute para debugging
const SimplePrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  try {
    // Para testing, vamos a asumir que el usuario está autenticado
    // Si quieres probar sin autenticación, cambia esto a false
    const isAuthenticated = true;
    
    if (!isAuthenticated) {
      console.log('Usuario no autenticado, redirigiendo a login');
      return <Navigate to="/login" replace />;
    }
    
    console.log('Usuario autenticado, mostrando contenido');
    return children;
    
  } catch (error) {
    console.error('Error en SimplePrivateRoute:', error);
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
          Error en Autenticación
        </h2>
        <p style={{ color: '#2d3436', marginBottom: '16px' }}>
          Error al verificar autenticación: {error instanceof Error ? error.message : 'Error desconocido'}
        </p>
        <button
          onClick={() => window.location.href = '/login'}
          style={{
            padding: '10px 20px',
            backgroundColor: '#74b9ff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Ir a Login
        </button>
      </div>
    );
  }
};

export default SimplePrivateRoute;