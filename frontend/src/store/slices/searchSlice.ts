// ==================================================================
// SEARCH SLICE - GESTIÓN DE BÚSQUEDA DE PRODUCTOS
// ==================================================================

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { SearchState } from '../../types/core';
import { productService } from '../../services/productService';

const initialState: SearchState = {
  query: '',
  results: [],
  isLoading: false,
  error: null,
};

// Thunk asíncrono para búsqueda de productos
export const searchProducts = createAsyncThunk(
  'search/searchProducts',
  async (query: string, { rejectWithValue }) => {
    try {
      if (query.trim().length === 0) {
        return [];
      }
      const products = await productService.search(query);
      return products;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Error en la búsqueda');
    }
  }
);

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload;
    },
    
    clearSearch: (state) => {
      state.query = '';
      state.results = [];
      state.error = null;
    },
    
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(searchProducts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(searchProducts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.results = action.payload;
        state.error = null;
      })
      .addCase(searchProducts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.results = [];
      });
  },
});

export const { setQuery, clearSearch, clearError } = searchSlice.actions;
export default searchSlice.reducer;