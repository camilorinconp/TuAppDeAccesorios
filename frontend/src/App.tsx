import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import POSPage from './pages/POSClean';
import DistributorPortalPage from './pages/DistributorPortalPage';
import ConsignmentLoansPage from './pages/ConsignmentLoansPage';
import TestNavigation from './pages/TestNavigation';
import LoginTest from './pages/LoginTest';
import { useReduxAuth } from './hooks/useReduxAuth';
import ErrorBoundary from './components/ErrorBoundary';
import MobileNavigation from './components/MobileNavigation';
import SimplePrivateRoute from './components/SimplePrivateRoute';
import './styles/variables.css';
import './styles/base.css';
import './styles/components.css';
import './styles/pos.css';

// Componente de ruta protegida
const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isInitialized } = useReduxAuth();
  
  if (!isInitialized) {
    return (
      <div className="container section mobile-center">
        <div className="spinner"></div>
        <p>Cargando...</p>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <Provider store={store}>
      <ErrorBoundary>
        <Router
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true
          }}
        >
          <div className="app-container" data-theme="dark">
            <div className="tech-grid"></div>
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
            <Route path="/login-test" element={<LoginTest />} />
            <Route path="/distributor-portal" element={<DistributorPortalPage />} />
            <Route path="/pos-test" element={<POSPage />} />
            <Route path="/test" element={<TestNavigation />} />
            <Route path="/" element={<Navigate to="/login" />} />
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
                  <POSPage />
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
        </Routes>
      </main>
    </>
  );
}

export default App;
