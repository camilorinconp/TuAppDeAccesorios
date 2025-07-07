// ==================================================================
// AUTH SLICE - REEMPLAZO DEL CONTEXT API
// ==================================================================

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { 
  loginUser, 
  refreshToken as apiRefreshToken, 
  logoutUser, 
  verifyAuth 
} from '../../services/api';

export interface AuthState {
  isAuthenticated: boolean;
  userRole: string | null;
  isInitialized: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  userRole: null,
  isInitialized: false,
  isLoading: false,
  error: null,
};

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      await loginUser(credentials.username, credentials.password);
      
      // La API maneja las cookies automáticamente, pero obtener perfil para rol
      const profile = await verifyAuth();
      
      return {
        userRole: profile.role,
      };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Error en el login');
    }
  }
);

export const refreshAuthToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { rejectWithValue }) => {
    try {
      await apiRefreshToken();
      
      return {
        success: true,
      };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Error al refrescar token');
    }
  }
);

export const checkAuthStatus = createAsyncThunk(
  'auth/checkStatus',
  async (_, { dispatch, rejectWithValue }) => {
    try {
      // Verificar autenticación usando la API
      const profile = await verifyAuth();
      
      return {
        userRole: profile.role,
        isValid: true,
      };
    } catch (error: any) {
      // Si la verificación falla, intentar refrescar
      try {
        const refreshResult = await dispatch(refreshAuthToken());
        if (refreshAuthToken.fulfilled.match(refreshResult)) {
          const profile = await verifyAuth();
          return {
            userRole: profile.role,
            isValid: true,
          };
        }
      } catch (refreshError) {
        // Si el refresh también falla, el usuario no está autenticado
      }
      
      return rejectWithValue('Authentication verification failed');
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async () => {
    try {
      await logoutUser();
    } catch (error) {
      // Ignorar errores de logout en el servidor
      console.warn('Logout server error:', error);
    }
    // La API maneja la limpieza de cookies automáticamente
  }
);

// Slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    resetAuth: (state) => {
      Object.assign(state, initialState);
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.userRole = action.payload.userRole;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.userRole = null;
        state.error = action.payload as string;
      })
      
      // Refresh token
      .addCase(refreshAuthToken.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(refreshAuthToken.fulfilled, (state) => {
        state.isLoading = false;
        state.error = null;
      })
      .addCase(refreshAuthToken.rejected, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.userRole = null;
        state.error = action.payload as string;
      })
      
      // Check auth status
      .addCase(checkAuthStatus.pending, (state) => {
        state.isLoading = true;
        state.isInitialized = false;
      })
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isInitialized = true;
        state.isAuthenticated = action.payload.isValid;
        state.userRole = action.payload.userRole;
        state.error = null;
      })
      .addCase(checkAuthStatus.rejected, (state, action) => {
        state.isLoading = false;
        state.isInitialized = true;
        state.isAuthenticated = false;
        state.userRole = null;
        state.error = action.payload as string;
      })
      
      // Logout
      .addCase(logout.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logout.fulfilled, (state) => {
        Object.assign(state, initialState, { isInitialized: true });
      })
      .addCase(logout.rejected, (state) => {
        // Siempre limpiar el estado incluso si el logout falla
        Object.assign(state, initialState, { isInitialized: true });
      });
  },
});

export const { clearError, resetAuth } = authSlice.actions;
export default authSlice.reducer;

// Selectores
export const selectAuth = (state: { auth: AuthState }) => state.auth;
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated;
export const selectUserRole = (state: { auth: AuthState }) => state.auth.userRole;
export const selectIsInitialized = (state: { auth: AuthState }) => state.auth.isInitialized;
export const selectIsLoading = (state: { auth: AuthState }) => state.auth.isLoading;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;