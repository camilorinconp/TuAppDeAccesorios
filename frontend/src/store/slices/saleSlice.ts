// ==================================================================
// SALE SLICE - GESTIÓN DE VENTAS
// ==================================================================

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { SalePayload, SaleState } from '../../types/core';
import { saleService } from '../../services/saleService';

const initialState: SaleState = {
  isLoading: false,
  isProcessing: false,
  error: null,
  lastSale: null,
  successMessage: null,
};

// Thunk asíncrono para procesar venta
export const processSale = createAsyncThunk(
  'sale/processSale',
  async (saleData: SalePayload, { rejectWithValue }) => {
    try {
      const result = await saleService.create(saleData);
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Error al procesar la venta');
    }
  }
);

const saleSlice = createSlice({
  name: 'sale',
  initialState,
  reducers: {
    clearSaleState: (state) => {
      state.error = null;
      state.successMessage = null;
      state.lastSale = null;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    clearSuccessMessage: (state) => {
      state.successMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(processSale.pending, (state) => {
        state.isProcessing = true;
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(processSale.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.isLoading = false;
        state.lastSale = action.payload;
        state.successMessage = '¡Venta registrada con éxito! Inventario actualizado automáticamente.';
        state.error = null;
      })
      .addCase(processSale.rejected, (state, action) => {
        state.isProcessing = false;
        state.isLoading = false;
        state.error = action.payload as string;
        state.successMessage = null;
      });
  },
});

export const { clearSaleState, clearError, clearSuccessMessage } = saleSlice.actions;
export default saleSlice.reducer;