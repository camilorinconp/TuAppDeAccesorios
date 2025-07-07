// ==================================================================
// REDUX AUTH HOOK - REEMPLAZO DEL useAuth HOOK
// ==================================================================

import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './useAppDispatch';
import { 
  login, 
  logout, 
  checkAuthStatus, 
  clearError,
  selectAuth,
  selectIsAuthenticated,
  selectUserRole,
  selectIsInitialized,
  selectIsLoading,
  selectAuthError 
} from '../store/slices/authSlice';

export const useReduxAuth = () => {
  const dispatch = useAppDispatch();
  
  // Selectores
  const auth = useAppSelector(selectAuth);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const userRole = useAppSelector(selectUserRole);
  const isInitialized = useAppSelector(selectIsInitialized);
  const isLoading = useAppSelector(selectIsLoading);
  const error = useAppSelector(selectAuthError);
  
  // Verificar autenticación al cargar
  useEffect(() => {
    if (!isInitialized) {
      dispatch(checkAuthStatus());
    }
  }, [dispatch, isInitialized]);
  
  // Funciones de acción
  const handleLogin = async (credentials: { username: string; password: string }) => {
    const result = await dispatch(login(credentials));
    return login.fulfilled.match(result);
  };
  
  const handleLogout = async () => {
    await dispatch(logout());
  };
  
  const handleClearError = () => {
    dispatch(clearError());
  };
  
  const handleCheckAuthStatus = async () => {
    const result = await dispatch(checkAuthStatus());
    return checkAuthStatus.fulfilled.match(result);
  };
  
  return {
    // Estado
    isAuthenticated,
    userRole,
    isInitialized,
    isLoading,
    error,
    
    // Acciones
    login: handleLogin,
    logout: handleLogout,
    clearError: handleClearError,
    checkAuthStatus: handleCheckAuthStatus,
    
    // Estado completo (para compatibilidad)
    auth,
  };
};

// Hook especializado para verificación de roles
export const useAuthRole = () => {
  const { isAuthenticated, userRole } = useReduxAuth();
  
  return {
    isAuthenticated,
    userRole,
    isAdmin: userRole === 'admin',
    isSalesStaff: userRole === 'sales_staff',
    hasRole: (role: string) => userRole === role,
    hasAnyRole: (roles: string[]) => roles.includes(userRole || ''),
  };
};

// Hook para inicialización automática
export const useAuthInit = () => {
  const { isInitialized, checkAuthStatus } = useReduxAuth();
  
  useEffect(() => {
    if (!isInitialized) {
      checkAuthStatus();
    }
  }, [isInitialized, checkAuthStatus]);
  
  return { isInitialized };
};

export default useReduxAuth;