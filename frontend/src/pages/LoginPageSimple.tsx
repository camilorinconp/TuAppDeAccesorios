import React, { useState } from 'react';

const LoginPageSimple: React.FC = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('isAuthenticated', 'true');
        localStorage.setItem('userRole', 'admin');
        // Redirigir al dashboard
        window.location.href = '/dashboard';
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Error de autenticación');
      }
    } catch (err: any) {
      console.error('Login error:', err);
      setError('Error de conexión. Verifica que el servidor esté funcionando.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setIsLoading(false);
    setError(null);
  };

  return (
    <div style={{ 
      padding: '20px', 
      maxWidth: '400px', 
      margin: '50px auto', 
      border: '1px solid #ccc', 
      borderRadius: '8px',
      backgroundColor: '#fff'
    }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>🔐 Login Simple</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="username" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Usuario:
          </label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ 
              width: '100%', 
              padding: '10px', 
              border: '1px solid #ddd',
              borderRadius: '4px',
              boxSizing: 'border-box'
            }}
            required
            disabled={isLoading}
          />
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="password" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Contraseña:
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ 
              width: '100%', 
              padding: '10px', 
              border: '1px solid #ddd',
              borderRadius: '4px',
              boxSizing: 'border-box'
            }}
            required
            disabled={isLoading}
          />
        </div>
        
        {error && (
          <div style={{ 
            color: '#dc3545', 
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            padding: '10px',
            borderRadius: '4px',
            marginBottom: '15px'
          }}>
            ❌ {error}
          </div>
        )}
        
        <button 
          type="submit" 
          disabled={isLoading}
          style={{ 
            width: '100%', 
            padding: '12px', 
            backgroundColor: isLoading ? '#6c757d' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
            marginBottom: '10px'
          }}
        >
          {isLoading ? '🔄 Ingresando...' : '🚀 Ingresar'}
        </button>
        
        {isLoading && (
          <button 
            type="button"
            onClick={handleReset}
            style={{ 
              width: '100%', 
              padding: '10px', 
              backgroundColor: '#dc3545', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px', 
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            ❌ Cancelar / Resetear
          </button>
        )}
      </form>
      
      <div style={{ 
        marginTop: '20px', 
        padding: '10px', 
        backgroundColor: '#e9ecef',
        borderRadius: '4px',
        fontSize: '12px'
      }}>
        <strong>Credenciales por defecto:</strong><br />
        Usuario: admin<br />
        Contraseña: admin123
      </div>
    </div>
  );
};

export default LoginPageSimple;