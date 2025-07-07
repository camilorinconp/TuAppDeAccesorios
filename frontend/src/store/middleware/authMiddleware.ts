// ==================================================================
// AUTH MIDDLEWARE - REEMPLAZO DEL useTokenRefresh HOOK
// ==================================================================

import { createListenerMiddleware } from '@reduxjs/toolkit';
import { refreshAuthToken, logout, selectIsAuthenticated } from '../slices/authSlice';
import type { RootState } from '../index';

export const authMiddleware = createListenerMiddleware();

// Intervalo para refresh automático del token (14 minutos)
const TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutos en milisegundos

let refreshInterval: ReturnType<typeof setInterval> | null = null;

// Listener para iniciar/detener el refresh automático
authMiddleware.startListening({
  predicate: (_, currentState, previousState) => {
    const current = currentState as RootState;
    const previous = previousState as RootState;
    
    // Verificar si cambió el estado de autenticación
    return current.auth.isAuthenticated !== previous.auth.isAuthenticated;
  },
  effect: async (_, listenerApi) => {
    const state = listenerApi.getState() as RootState;
    const isAuthenticated = selectIsAuthenticated(state);
    
    if (isAuthenticated) {
      // Iniciar refresh automático
      startTokenRefreshInterval(listenerApi);
    } else {
      // Detener refresh automático
      stopTokenRefreshInterval();
    }
  },
});

// Listener para manejar errores de autenticación
authMiddleware.startListening({
  predicate: (action) => {
    // Detectar errores 401 Unauthorized
    return action.type.endsWith('/rejected') && 
           (action.payload as any)?.status === 401;
  },
  effect: async (_, listenerApi) => {
    const state = listenerApi.getState() as RootState;
    const isAuthenticated = selectIsAuthenticated(state);
    
    if (isAuthenticated) {
      // Intentar refrescar token
      const refreshResult = await listenerApi.dispatch(refreshAuthToken());
      
      if (refreshAuthToken.rejected.match(refreshResult)) {
        // Si el refresh falla, hacer logout
        await listenerApi.dispatch(logout());
      }
    }
  },
});

// Función para iniciar el intervalo de refresh
function startTokenRefreshInterval(listenerApi: any) {
  // Limpiar intervalo existente
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  
  // Crear nuevo intervalo
  refreshInterval = setInterval(async () => {
    const state = listenerApi.getState() as RootState;
    const isAuthenticated = selectIsAuthenticated(state);
    
    if (isAuthenticated) {
      try {
        const refreshResult = await listenerApi.dispatch(refreshAuthToken());
        
        if (refreshAuthToken.rejected.match(refreshResult)) {
          console.warn('Token refresh failed, logging out');
          await listenerApi.dispatch(logout());
        }
      } catch (error) {
        console.error('Error during token refresh:', error);
        await listenerApi.dispatch(logout());
      }
    }
  }, TOKEN_REFRESH_INTERVAL);
}

// Función para detener el intervalo de refresh
function stopTokenRefreshInterval() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// Limpiar intervalo cuando la aplicación se cierre
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    stopTokenRefreshInterval();
  });
}

export default authMiddleware;