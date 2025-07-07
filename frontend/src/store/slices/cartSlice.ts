// ==================================================================
// CART SLICE - GESTIÓN DEL CARRITO DE COMPRAS
// ==================================================================

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { CartItem, Product } from '../../types/core';

interface CartState {
  items: CartItem[];
  totalAmount: number;
  totalItems: number;
}

const initialState: CartState = {
  items: [],
  totalAmount: 0,
  totalItems: 0,
};

const calculateTotals = (items: CartItem[]) => {
  const totalAmount = items.reduce(
    (sum, item) => sum + (item.selling_price * item.quantity_in_cart),
    0
  );
  const totalItems = items.reduce(
    (sum, item) => sum + item.quantity_in_cart,
    0
  );
  return { totalAmount, totalItems };
};

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    addToCart: (state, action: PayloadAction<Product>) => {
      const product = action.payload;
      
      const existingItem = state.items.find(item => item.id === product.id);

      if (existingItem) {
        existingItem.quantity_in_cart += 1;
      } else {
        state.items.push({
          ...product,
          quantity_in_cart: 1,
        });
      }

      const totals = calculateTotals(state.items);
      state.totalAmount = totals.totalAmount;
      state.totalItems = totals.totalItems;
    },

    removeFromCart: (state, action: PayloadAction<number>) => {
      const productId = action.payload;
      state.items = state.items.filter(item => item.id !== productId);

      const totals = calculateTotals(state.items);
      state.totalAmount = totals.totalAmount;
      state.totalItems = totals.totalItems;
    },

    updateQuantity: (state, action: PayloadAction<{ id: number; quantity: number }>) => {
      const { id, quantity } = action.payload;
      const item = state.items.find(item => item.id === id);

      if (item && quantity > 0) {
        item.quantity_in_cart = quantity;
      } else if (item && quantity <= 0) {
        state.items = state.items.filter(item => item.id !== id);
      }

      const totals = calculateTotals(state.items);
      state.totalAmount = totals.totalAmount;
      state.totalItems = totals.totalItems;
    },

    clearCart: (state) => {
      state.items = [];
      state.totalAmount = 0;
      state.totalItems = 0;
    },
  },
});

export const { addToCart, removeFromCart, updateQuantity, clearCart } = cartSlice.actions;
export default cartSlice.reducer;