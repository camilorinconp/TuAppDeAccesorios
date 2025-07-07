import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface MobileNavigationProps {
  isAuthenticated?: boolean;
}

const MobileNavigation: React.FC<MobileNavigationProps> = ({ isAuthenticated = false }) => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  const closeMenu = () => {
    setIsOpen(false);
  };

  const navigationItems = [
    { to: "/test", label: "Inicio", icon: "🏠", public: true },
    { to: "/pos-test", label: "Punto de Venta", icon: "🛒", public: true },
    { to: "/inventory", label: "Inventario", icon: "📦", public: false },
    { to: "/dashboard", label: "Dashboard", icon: "📊", public: false },
    { to: "/login", label: "Iniciar Sesión", icon: "🔐", public: true, showWhenLoggedOut: true },
  ];

  const filteredItems = navigationItems.filter(item => {
    if (item.showWhenLoggedOut && isAuthenticated) return false;
    if (!item.public && !isAuthenticated) return false;
    return true;
  });

  return (
    <>
      {/* Mobile Navigation Header */}
      <div className="lg:hidden">
        <div className="navbar">
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Link to="/test" className="navbar-brand" onClick={closeMenu}>
              🧪 TuApp
            </Link>
            
            <button
              onClick={toggleMenu}
              className="btn btn-ghost btn-sm"
              style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '3px',
                padding: '8px',
                minWidth: '40px',
                minHeight: '40px'
              }}
              aria-label="Menú de navegación"
            >
              <span style={{ 
                width: '20px', 
                height: '2px', 
                backgroundColor: 'var(--text-primary)', 
                transition: 'all 0.3s',
                transform: isOpen ? 'rotate(45deg) translate(6px, 6px)' : 'none'
              }}></span>
              <span style={{ 
                width: '20px', 
                height: '2px', 
                backgroundColor: 'var(--text-primary)', 
                transition: 'all 0.3s',
                opacity: isOpen ? 0 : 1
              }}></span>
              <span style={{ 
                width: '20px', 
                height: '2px', 
                backgroundColor: 'var(--text-primary)', 
                transition: 'all 0.3s',
                transform: isOpen ? 'rotate(-45deg) translate(6px, -6px)' : 'none'
              }}></span>
            </button>
          </div>
        </div>

        {/* Mobile Menu Overlay */}
        {isOpen && (
          <div 
            className="modal-overlay" 
            style={{ 
              background: 'rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(5px)',
              zIndex: 'var(--z-mobile-nav)'
            }}
            onClick={closeMenu}
          >
            <div 
              className="card"
              style={{ 
                position: 'fixed',
                top: 'var(--mobile-nav-height)',
                left: '0',
                right: '0',
                margin: 'var(--spacing-md)',
                maxHeight: 'calc(100vh - var(--mobile-nav-height) - var(--spacing-xl))',
                overflow: 'auto',
                animation: 'slideUp 0.3s ease-out'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="card-body" style={{ padding: '0' }}>
                <nav>
                  {filteredItems.map((item, index) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      onClick={closeMenu}
                      className={`navbar-link ${location.pathname === item.to ? 'active' : ''}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-md)',
                        padding: 'var(--spacing-lg)',
                        borderBottom: index < filteredItems.length - 1 ? '1px solid var(--border-color)' : 'none',
                        fontSize: 'var(--text-base)',
                        fontWeight: '500',
                        textDecoration: 'none',
                        borderRadius: '0'
                      }}
                    >
                      <span style={{ fontSize: '20px' }}>{item.icon}</span>
                      <span>{item.label}</span>
                      {location.pathname === item.to && (
                        <span style={{ 
                          marginLeft: 'auto', 
                          color: 'var(--primary-400)',
                          fontSize: '12px'
                        }}>
                          ●
                        </span>
                      )}
                    </Link>
                  ))}
                </nav>
              </div>
              
              <div className="card-footer mobile-center">
                <div style={{ 
                  fontSize: 'var(--text-xs)', 
                  color: 'var(--text-tertiary)',
                  lineHeight: '1.4'
                }}>
                  <div>📱 Versión Móvil</div>
                  <div>Sistema de Gestión de Inventario</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Desktop Navigation - Hidden on mobile */}
      <div className="hidden lg:block">
        <div className="navbar">
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Link to="/test" className="navbar-brand">
              🧪 TuAppDeAccesorios
            </Link>
            
            <nav className="navbar-nav">
              {filteredItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`navbar-link ${location.pathname === item.to ? 'active' : ''}`}
                >
                  <span style={{ marginRight: 'var(--spacing-sm)' }}>{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </nav>
            
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
              Sistema de Gestión de Inventario
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default MobileNavigation;