import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, verifyAuth } from '../services/api';

const LoginTest: React.FC = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleDirectLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');
    
    try {
      console.log('Verificando conectividad con el backend...');
      console.log('REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
      
      // Primero verificar conectividad
      const backendUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      console.log('Usando backend URL:', backendUrl);
      
      const healthResponse = await fetch(`${backendUrl}/health`);
      if (!healthResponse.ok) {
        throw new Error('Backend no responde correctamente');
      }
      console.log('✅ Backend accesible');
      
      console.log('Intentando login directo...');
      const result = await loginUser(username, password);
      console.log('Login result:', result);
      
      setMessage('✅ Login exitoso! Token recibido.');
      
      // Verificar autenticación
      try {
        const profile = await verifyAuth();
        console.log('Profile:', profile);
        setMessage(prev => prev + ` Usuario: ${profile.username}, Rol: ${profile.role}`);
        
        // Redirigir a inventario
        setTimeout(() => {
          navigate('/inventory');
        }, 2000);
        
      } catch (verifyError) {
        console.error('Error en verificación:', verifyError);
        setError('Login exitoso pero fallo en verificación');
      }
      
    } catch (err: any) {
      console.error('Login error:', err);
      console.error('Error details:', JSON.stringify(err, null, 2));
      
      let errorMessage = 'Error en login';
      if (err.message) {
        errorMessage = err.message;
      } else if (err.name === 'TypeError' && err.message?.includes('fetch')) {
        errorMessage = 'Error de conexión con el servidor. Verifica que el backend esté ejecutándose en puerto 8000.';
      }
      
      setError(`Error: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      maxWidth: '500px', 
      margin: '50px auto', 
      border: '1px solid #ccc', 
      borderRadius: '8px',
      backgroundColor: '#f9f9f9'
    }}>
      <h2>🧪 Test de Login Directo</h2>
      <p style={{ color: '#666', fontSize: '14px' }}>
        Prueba directa de la API de autenticación
      </p>
      
      <form onSubmit={handleDirectLogin}>
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
              fontSize: '16px'
            }}
            required
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
              fontSize: '16px'
            }}
            required
          />
        </div>
        
        {error && (
          <div style={{ 
            color: 'red', 
            backgroundColor: '#ffe6e6',
            padding: '10px',
            borderRadius: '4px',
            marginBottom: '15px',
            border: '1px solid #ffcccc'
          }}>
            ❌ {error}
          </div>
        )}
        
        {message && (
          <div style={{ 
            color: 'green', 
            backgroundColor: '#e6ffe6',
            padding: '10px',
            borderRadius: '4px',
            marginBottom: '15px',
            border: '1px solid #ccffcc'
          }}>
            {message}
          </div>
        )}
        
        <button 
          type="submit" 
          disabled={isLoading}
          style={{ 
            width: '100%', 
            padding: '12px', 
            backgroundColor: isLoading ? '#ccc' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '5px', 
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {isLoading ? '🔄 Probando login...' : '🚀 Probar Login Directo'}
        </button>
      </form>
      
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '4px' }}>
        <h4>ℹ️ Información del Test:</h4>
        <ul style={{ fontSize: '12px', color: '#666' }}>
          <li>✅ Credenciales por defecto: admin/admin</li>
          <li>🔍 Se conecta directamente a la API</li>
          <li>🍪 Usa cookies para autenticación</li>
          <li>↗️ Redirige a /inventory si es exitoso</li>
        </ul>
      </div>
    </div>
  );
};

export default LoginTest;