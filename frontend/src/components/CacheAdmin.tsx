import React, { useState, useEffect } from 'react';
import { useClientCache } from '../services/clientCache';

/**
 * Componente de administración de caché del cliente
 */
const CacheAdmin: React.FC = () => {
  const { getStats, clearCache } = useClientCache();
  const [stats, setStats] = useState<any>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setStats(getStats());
  }, [refreshKey, getStats]);

  const handleClearCache = () => {
    if (window.confirm('¿Estás seguro de que quieres limpiar todo el caché del cliente?')) {
      clearCache();
      setRefreshKey(prev => prev + 1);
    }
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getCacheUsage = () => {
    try {
      const storage = JSON.stringify(localStorage);
      return storage.length * 2; // Aproximación (cada char = 2 bytes)
    } catch {
      return 0;
    }
  };

  if (!stats) {
    return <div>Cargando estadísticas del caché...</div>;
  }

  return (
    <div style={{ 
      padding: '20px', 
      border: '1px solid #ddd', 
      borderRadius: '8px',
      backgroundColor: '#f9f9fa',
      margin: '20px 0'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ margin: 0, color: '#333' }}>Administración de Caché del Cliente</h3>
        <div>
          <button
            onClick={handleRefresh}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              marginRight: '10px'
            }}
          >
            Actualizar
          </button>
          <button
            onClick={handleClearCache}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Limpiar Caché
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
        <div style={{ 
          padding: '15px', 
          backgroundColor: 'white', 
          borderRadius: '6px',
          border: '1px solid #eee'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666', fontSize: '14px' }}>Elementos en Caché</h4>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745' }}>
            {stats.size} / {stats.maxSize}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {((stats.size / stats.maxSize) * 100).toFixed(1)}% utilizado
          </div>
        </div>

        <div style={{ 
          padding: '15px', 
          backgroundColor: 'white', 
          borderRadius: '6px',
          border: '1px solid #eee'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666', fontSize: '14px' }}>Almacenamiento</h4>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#17a2b8' }}>
            {formatBytes(getCacheUsage())}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            Usado en localStorage
          </div>
        </div>

        <div style={{ 
          padding: '15px', 
          backgroundColor: 'white', 
          borderRadius: '6px',
          border: '1px solid #eee'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666', fontSize: '14px' }}>Tasa de Aciertos</h4>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffc107' }}>
            {stats.hitRate.toFixed(1)}%
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {stats.hits} aciertos / {stats.totalRequests} total
          </div>
        </div>

        <div style={{ 
          padding: '15px', 
          backgroundColor: 'white', 
          borderRadius: '6px',
          border: '1px solid #eee'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666', fontSize: '14px' }}>Estado</h4>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#28a745' }}>
            ✓ Activo
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            Cache del cliente funcionando
          </div>
        </div>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h4 style={{ color: '#666', marginBottom: '10px' }}>Información del Caché</h4>
        <div style={{ 
          padding: '10px', 
          backgroundColor: 'white', 
          border: '1px solid #eee', 
          borderRadius: '4px',
          fontSize: '14px'
        }}>
          <div style={{ marginBottom: '5px' }}>
            <strong>TTL por defecto:</strong> 5 minutos
          </div>
          <div style={{ marginBottom: '5px' }}>
            <strong>TTL productos:</strong> 2 minutos
          </div>
          <div style={{ marginBottom: '5px' }}>
            <strong>TTL búsquedas:</strong> 30 segundos
          </div>
          <div>
            <strong>Limpieza automática:</strong> Cada 60 segundos
          </div>
        </div>
      </div>

      <div style={{ marginTop: '15px' }}>
        <h4 style={{ color: '#666', marginBottom: '10px' }}>Acciones Rápidas</h4>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => {
              // Invalidar caché de productos específicamente
              const { invalidateProductsCache } = require('../services/clientCache');
              invalidateProductsCache();
              handleRefresh();
            }}
            style={{
              padding: '6px 12px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Limpiar Caché de Productos
          </button>
          <button
            onClick={() => {
              // Simular limpieza de elementos expirados
              handleRefresh();
            }}
            style={{
              padding: '6px 12px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Limpiar Expirados
          </button>
        </div>
      </div>
    </div>
  );
};

export default CacheAdmin;