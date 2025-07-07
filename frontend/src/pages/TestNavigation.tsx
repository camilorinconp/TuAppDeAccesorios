// ==================================================================
// PÁGINA DE NAVEGACIÓN PARA TESTING
// ==================================================================

import React from 'react';
import { Link } from 'react-router-dom';
import PageLayout from '../components/PageLayout';

const TestNavigation: React.FC = () => {
  return (
    <PageLayout 
      title="Panel de Navegación" 
      subtitle="Navega por los diferentes módulos de la aplicación"
      className="fade-in"
    >
      
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-mobile">
          
          <div className="card hover-lift">
            <div className="card-body mobile-center">
              <div style={{ fontSize: 'clamp(40px, 8vw, 48px)', marginBottom: 'var(--spacing-md)' }}>🛒</div>
              <h3>Punto de Venta</h3>
              <p style={{ marginBottom: 'var(--spacing-lg)' }}>Sistema POS con Redux Toolkit y arquitectura moderna</p>
              <Link 
                to="/pos-test" 
                className="btn btn-primary mobile-full"
                style={{ textDecoration: 'none' }}
              >
                Abrir POS
              </Link>
            </div>
          </div>

          <div className="card hover-lift">
            <div className="card-body mobile-center">
              <div style={{ fontSize: 'clamp(40px, 8vw, 48px)', marginBottom: 'var(--spacing-md)' }}>📦</div>
              <h3>Inventario</h3>
              <p style={{ marginBottom: 'var(--spacing-lg)' }}>Gestión completa de productos con validación SKU y autocompletado</p>
              <Link 
                to="/inventory" 
                className="btn btn-success mobile-full"
                style={{ textDecoration: 'none' }}
              >
                Gestionar Inventario
              </Link>
            </div>
          </div>

          <div className="card hover-lift">
            <div className="card-body mobile-center">
              <div style={{ fontSize: 'clamp(40px, 8vw, 48px)', marginBottom: 'var(--spacing-md)' }}>🔐</div>
              <h3>Autenticación</h3>
              <p style={{ marginBottom: 'var(--spacing-lg)' }}>Sistema de login seguro con JWT y cookies HTTP-Only</p>
              <Link 
                to="/login" 
                className="btn btn-secondary mobile-full"
                style={{ textDecoration: 'none' }}
              >
                Iniciar Sesión
              </Link>
            </div>
          </div>

          <div className="card hover-lift">
            <div className="card-body mobile-center">
              <div style={{ fontSize: 'clamp(40px, 8vw, 48px)', marginBottom: 'var(--spacing-md)' }}>📊</div>
              <h3>Dashboard</h3>
              <p style={{ marginBottom: 'var(--spacing-lg)' }}>Panel principal con métricas y reportes (requiere autenticación)</p>
              <Link 
                to="/dashboard" 
                className="btn btn-primary mobile-full"
                style={{ textDecoration: 'none' }}
              >
                Ver Dashboard
              </Link>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>✅ Funcionalidades Implementadas</h3>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-mobile">
              <div className="space-y-mobile">
                <h4>📱 Frontend</h4>
                <ul style={{ listStyle: 'none', padding: 0, lineHeight: '1.6' }}>
                  <li>• Redux Toolkit con estado centralizado</li>
                  <li>• TypeScript robusto y tipado estricto</li>
                  <li>• Componentes modulares</li>
                  <li>• Hooks personalizados</li>
                  <li>• Diseño responsivo y moderno</li>
                </ul>
              </div>
              <div className="space-y-mobile">
                <h4>🔧 Backend</h4>
                <ul style={{ listStyle: 'none', padding: 0, lineHeight: '1.6' }}>
                  <li>• FastAPI con validación Pydantic</li>
                  <li>• PostgreSQL con SQLAlchemy</li>
                  <li>• JWT con cookies HTTP-Only</li>
                  <li>• Redis para caching</li>
                  <li>• Celery para tareas asíncronas</li>
                </ul>
              </div>
              <div className="space-y-mobile">
                <h4>🚀 Características</h4>
                <ul style={{ listStyle: 'none', padding: 0, lineHeight: '1.6' }}>
                  <li>• Validación SKU en tiempo real</li>
                  <li>• Autocompletado inteligente</li>
                  <li>• Debounce optimizado</li>
                  <li>• Manejo profesional de errores</li>
                  <li>• Navegación por teclado</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
    </PageLayout>
  );
};

export default TestNavigation;