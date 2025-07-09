// ==================================================================
// PANEL DE CONTROL MODERNO - DISEÑO ÚLTIMA GENERACIÓN
// ARQUITECTURA MÓVIL OPTIMIZADA CON COMPONENTES INNOVADORES
// ==================================================================

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PageLayout from '../components/PageLayout';

// Hook personalizado para detectar dispositivo
const useDeviceDetection = () => {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setIsMobile(width < 640);
      setIsTablet(width >= 640 && width < 1024);
      setScreenSize(width < 640 ? 'mobile' : width < 1024 ? 'tablet' : 'desktop');
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return { isMobile, isTablet, screenSize };
};

// Componente ModuleCard optimizado
const ModuleCard: React.FC<{
  module: any;
  index: number;
  screenSize: 'mobile' | 'tablet' | 'desktop';
}> = ({ module, index, screenSize }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  // Estilos adaptativos por tamaño de pantalla
  const getCardStyles = () => {
    const baseStyles = {
      background: 'var(--glass-bg)',
      backdropFilter: 'blur(15px)',
      borderRadius: screenSize === 'mobile' ? '16px' : '20px',
      padding: screenSize === 'mobile' ? '1.5rem' : '2rem',
      border: '1px solid var(--glass-border)',
      boxShadow: isHovered 
        ? `var(--shadow-2xl), 0 0 0 1px ${module.color}30, 0 0 20px ${module.color}20`
        : 'var(--shadow-lg)',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      cursor: 'pointer',
      position: 'relative' as const,
      overflow: 'hidden',
      minHeight: screenSize === 'mobile' ? '240px' : '280px',
      display: 'flex',
      flexDirection: 'column' as const,
      justifyContent: 'space-between',
      animation: `slideFromBottom 0.6s ease-out ${index * 0.1}s backwards`,
      transform: isHovered ? 'translateY(-8px) scale(1.02)' : isPressed ? 'translateY(2px) scale(0.98)' : 'translateY(0) scale(1)',
    };

    return baseStyles;
  };

  return (
    <div
      style={getCardStyles()}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onTouchStart={() => setIsPressed(true)}
      onTouchEnd={() => setIsPressed(false)}
    >
      {/* Efecto de fondo gradiente */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: module.gradient,
          opacity: isHovered ? 0.15 : 0.1,
          transition: 'opacity 0.3s ease',
          zIndex: -1
        }}
      />
      
      {/* Contenido del módulo */}
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <div
          className="module-icon"
          style={{
            fontSize: screenSize === 'mobile' ? '3rem' : '4rem',
            marginBottom: '1rem',
            filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))',
            animation: isHovered ? 'pulse-soft 0.6s ease-in-out' : 'float 3s ease-in-out infinite',
            transform: isHovered ? 'scale(1.1)' : 'scale(1)',
            transition: 'transform 0.3s ease'
          }}
        >
          {module.icon}
        </div>
        <h3
          style={{
            fontSize: screenSize === 'mobile' ? '1.25rem' : '1.5rem',
            fontWeight: '700',
            color: 'var(--text-primary)',
            marginBottom: '0.75rem',
            textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
          }}
        >
          {module.title}
        </h3>
        <p
          style={{
            fontSize: screenSize === 'mobile' ? '0.875rem' : '0.95rem',
            color: 'var(--text-secondary)',
            lineHeight: '1.5',
            marginBottom: '1.5rem'
          }}
        >
          {module.description}
        </p>
      </div>
      
      {/* Botón de acción */}
      <Link
        to={module.route}
        style={{
          display: 'flex',
          textDecoration: 'none',
          background: module.gradient,
          color: 'white',
          padding: screenSize === 'mobile' ? '0.75rem 1.25rem' : '0.875rem 1.5rem',
          borderRadius: '12px',
          fontSize: screenSize === 'mobile' ? '0.875rem' : '0.95rem',
          fontWeight: '600',
          textAlign: 'center',
          transition: 'all 0.2s ease',
          boxShadow: 'var(--shadow-lg)',
          border: 'none',
          cursor: 'pointer',
          minHeight: screenSize === 'mobile' ? '44px' : 'auto', // Accesibilidad táctil
          alignItems: 'center',
          justifyContent: 'center'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = 'var(--shadow-xl)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
        }}
      >
        {module.buttonText}
      </Link>
    </div>
  );
};

const TestNavigation: React.FC = () => {
  const { isMobile, isTablet, screenSize } = useDeviceDetection();
  
  const modules = [
    {
      id: 'pos',
      title: 'Punto de Venta Moderno',
      description: 'Sistema POS moderno con UX avanzadas y Redux Toolkit',
      icon: '💰',
      route: '/pos',
      buttonText: 'Abrir POS Moderno',
      gradient: 'var(--gradient-primary)',
      color: 'var(--primary-500)'
    },
    {
      id: 'inventory',
      title: 'Inventario',
      description: 'Gestión completa de productos con validación SKU y autocompletado',
      icon: '📦',
      route: '/inventory',
      buttonText: 'Gestionar Inventario',
      gradient: 'var(--gradient-success)',
      color: 'var(--success-500)'
    },
    {
      id: 'auth',
      title: 'Autenticación',
      description: 'Sistema de login seguro con JWT y cookies HTTP-Only',
      icon: '🔐',
      route: '/login',
      buttonText: 'Iniciar Sesión',
      gradient: 'linear-gradient(135deg, var(--warning-500), var(--warning-600))',
      color: 'var(--warning-500)'
    },
    {
      id: 'dashboard',
      title: 'Dashboard',
      description: 'Panel principal con métricas y reportes (requiere autenticación)',
      icon: '📊',
      route: '/dashboard',
      buttonText: 'Ver Dashboard',
      gradient: 'var(--gradient-primary)',
      color: 'var(--primary-500)'
    }
  ];

  return (
    <PageLayout 
      title="Panel de Control" 
      subtitle="Navega por los diferentes módulos de la aplicación"
      className="fade-in"
    >
      {/* Efecto de partículas decorativas */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: -1,
          background: 'radial-gradient(circle at 25% 25%, var(--primary-100) 0%, transparent 50%), radial-gradient(circle at 75% 75%, var(--success-100) 0%, transparent 50%)',
          animation: 'pulse-soft 8s ease-in-out infinite'
        }}
      />
      
      {/* CSS embebido para grid responsivo */}
      <style dangerouslySetInnerHTML={{
        __html: `
          .navigation-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: clamp(1rem, 2vw, 1.5rem);
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 clamp(1rem, 3vw, 2rem);
            position: relative;
          }
          
          @media (max-width: 1024px) {
            .navigation-grid {
              grid-template-columns: repeat(2, 1fr);
              gap: 1.5rem;
            }
          }
          
          @media (max-width: 640px) {
            .navigation-grid {
              grid-template-columns: 1fr;
              gap: 1rem;
              padding: 0 1rem;
            }
          }
          
          @media (max-width: 480px) {
            .navigation-grid {
              gap: 0.75rem;
            }
          }
          
          /* Optimizaciones para dispositivos táctiles */
          @media (hover: none) and (pointer: coarse) {
            .navigation-grid {
              gap: 1rem;
            }
          }
        `
      }} />
      
      {/* Grid responsivo profesional */}
      <div className="navigation-grid">
        {modules.map((module, index) => (
          <ModuleCard
            key={module.id}
            module={module}
            index={index}
            screenSize={screenSize}
          />
        ))}
      </div>

      <div
        style={{
          marginTop: '4rem',
          background: 'var(--glass-bg)',
          backdropFilter: 'blur(10px)',
          borderRadius: screenSize === 'mobile' ? '16px' : '24px',
          padding: screenSize === 'mobile' ? '2rem 1.5rem' : '3rem 2rem',
          border: '1px solid var(--glass-border)',
          boxShadow: 'var(--shadow-2xl)',
          maxWidth: '1200px',
          margin: '4rem auto 0',
          position: 'relative' as const,
          overflow: 'hidden'
        }}
      >
        {/* Efecto de fondo sutil */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(135deg, var(--primary-50) 0%, var(--success-50) 100%)',
            zIndex: -1
          }}
        />
        
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <h3
            style={{
              fontSize: screenSize === 'mobile' ? '1.5rem' : '2rem',
              fontWeight: '700',
              color: 'var(--text-primary)',
              marginBottom: '0.5rem',
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
            }}
          >
            ✅ Funcionalidades Implementadas
          </h3>
          <p
            style={{
              fontSize: screenSize === 'mobile' ? '1rem' : '1.1rem',
              color: 'var(--text-secondary)',
              maxWidth: '600px',
              margin: '0 auto'
            }}
          >
            Sistema completo con tecnologías de última generación
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: screenSize === 'mobile' ? '1fr' : 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '2rem',
            alignItems: 'start'
          }}
        >
          {[
            {
              title: '📱 Frontend',
              color: 'var(--primary-500)',
              features: [
                'Redux Toolkit con estado centralizado',
                'TypeScript robusto y tipado estricto',
                'Componentes modulares',
                'Hooks personalizados',
                'Diseño responsivo y moderno'
              ]
            },
            {
              title: '🔧 Backend',
              color: 'var(--success-500)',
              features: [
                'FastAPI con validación Pydantic',
                'PostgreSQL con SQLAlchemy',
                'JWT con cookies HTTP-Only',
                'Redis para caching',
                'Celery para tareas asíncronas'
              ]
            },
            {
              title: '🚀 Características',
              color: 'var(--warning-500)',
              features: [
                'Validación SKU en tiempo real',
                'Autocompletado inteligente',
                'Debounce optimizado',
                'Manejo profesional de errores',
                'Navegación por teclado'
              ]
            }
          ].map((section, index) => (
            <div
              key={index}
              style={{
                background: 'var(--glass-bg)',
                borderRadius: '16px',
                padding: screenSize === 'mobile' ? '1.5rem' : '2rem',
                border: '1px solid var(--glass-border)',
                transition: 'all 0.3s ease',
                minHeight: screenSize === 'mobile' ? '240px' : '280px'
              }}
            >
              <h4
                style={{
                  fontSize: screenSize === 'mobile' ? '1.1rem' : '1.3rem',
                  fontWeight: '600',
                  color: section.color,
                  marginBottom: '1.5rem',
                  textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)'
                }}
              >
                {section.title}
              </h4>
              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  lineHeight: '1.8',
                  color: 'var(--text-primary)'
                }}
              >
                {section.features.map((feature, featureIndex) => (
                  <li
                    key={featureIndex}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '0.75rem',
                      fontSize: screenSize === 'mobile' ? '0.875rem' : '0.95rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <span
                      style={{
                        color: section.color,
                        marginRight: '0.75rem',
                        fontSize: '1.1rem'
                      }}
                    >
                      •
                    </span>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </PageLayout>
  );
};

export default TestNavigation;