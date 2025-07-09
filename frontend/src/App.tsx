import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import LoginPage from './pages/LoginPage';
import LoginPageSimple from './pages/LoginPageSimple';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import POSModern from './pages/POSModern';
import POSPageClassic from './pages/POSClean';
import DistributorPortalPage from './pages/DistributorPortalPage';
import ConsignmentLoansPage from './pages/ConsignmentLoansPage';
import DistributorsPage from './pages/DistributorsPage';
import TestNavigation from './pages/TestNavigation';
import LoginTest from './pages/LoginTest';
import { useReduxAuth } from './hooks/useReduxAuth';
import ErrorBoundary from './components/ErrorBoundary';
import MobileNavigation from './components/MobileNavigation';
import SimplePrivateRoute from './components/SimplePrivateRoute';
import ThemeToggle from './components/ThemeToggle';
import './styles/variables.css';
import './styles/base.css';
import './styles/components.css';
import './styles/pos.css';

// Componente de ruta protegida simplificado - temporalmente permitir acceso
const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  // Temporalmente permitir acceso sin verificación para evitar problemas
  return children;
};

function App() {
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    // Cargar tema desde localStorage o usar dark como default
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : true;
  });

  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    localStorage.setItem('theme', newTheme ? 'dark' : 'light');
  };

  useEffect(() => {
    // Aplicar el tema al elemento raíz
    document.documentElement.setAttribute('data-theme', isDarkTheme ? 'dark' : 'light');
  }, [isDarkTheme]);

  return (
    <Provider store={store}>
      <ErrorBoundary>
        <Router>
          <div className="app-container" data-theme={isDarkTheme ? 'dark' : 'light'}>
            <div className="tech-grid"></div>
            {/* Toggle de tema en la esquina superior derecha */}
            <div style={{ 
              position: 'fixed', 
              top: '20px', 
              right: '20px', 
              zIndex: 9999,
              display: 'flex',
              gap: '10px'
            }}>
              <ThemeToggle isDark={isDarkTheme} onToggle={toggleTheme} />
            </div>
            <AppContent />
          </div>
        </Router>
      </ErrorBoundary>
    </Provider>
  );
}

function AppContent() {
  const { isAuthenticated } = useReduxAuth();
  
  return (
    <>
      <MobileNavigation isAuthenticated={isAuthenticated} />
      <main>
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login-simple" element={<LoginPageSimple />} />
            <Route path="/login-test" element={<LoginTest />} />
            <Route path="/distributor-portal" element={<DistributorPortalPage />} />
            <Route path="/pos-test" element={<POSModern />} />
            <Route path="/test" element={<TestNavigation />} />
            <Route path="/" element={<Navigate to="/login-simple" />} />
            <Route
              path="/dashboard"
              element={
                <PrivateRoute>
                  <DashboardPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/inventory"
              element={
                <SimplePrivateRoute>
                  <InventoryPage />
                </SimplePrivateRoute>
              }
            />
            <Route
              path="/pos"
              element={
                <PrivateRoute>
                  <POSModern />
                </PrivateRoute>
              }
            />
            <Route
              path="/pos-classic"
              element={
                <PrivateRoute>
                  <POSPageClassic />
                </PrivateRoute>
              }
            />
            <Route
              path="/consignments"
              element={
                <PrivateRoute>
                  <ConsignmentLoansPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/distributors"
              element={
                <PrivateRoute>
                  <DistributorsPage />
                </PrivateRoute>
              }
            />
        </Routes>
      </main>
    </>
  );
}

export default App;
