// ==================================================================
// STORE CENTRALIZADO - REDUX TOOLKIT
// ==================================================================

import { configureStore } from '@reduxjs/toolkit';
import cartReducer from './slices/cartSlice';
import searchReducer from './slices/searchSlice';
import saleReducer from './slices/saleSlice';
import authReducer from './slices/authSlice';
import { authMiddleware } from './middleware/authMiddleware';

export const store = configureStore({
  reducer: {
    cart: cartReducer,
    search: searchReducer,
    sale: saleReducer,
    auth: authReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }).prepend(authMiddleware.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;