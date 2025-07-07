// ==================================================================
// POINT OF SALE PAGE - ARQUITECTURA EMPRESARIAL
// ==================================================================

import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../hooks/useAppDispatch';
import { useDebounce } from '../hooks/useDebounce';
import { SearchSection } from '../components/POS/SearchSection';
import { CartSection } from '../components/POS/CartSection';
import { SaleActions } from '../components/POS/SaleActions';
import { StatusMessages } from '../components/POS/StatusMessages';
import { searchProducts, setQuery, clearSearch } from '../store/slices/searchSlice';
import { addToCart, removeFromCart, clearCart } from '../store/slices/cartSlice';
import { processSale, clearSuccessMessage } from '../store/slices/saleSlice';

const POSPageEnterprise: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Selectores de estado
  const { query, results, isLoading: searchLoading, error: searchError } = useAppSelector(state => state.search);
  const { items: cartItems, totalAmount, totalItems } = useAppSelector(state => state.cart);
  const { isProcessing, error: saleError, successMessage } = useAppSelector(state => state.sale);
  
  // Debounce para optimizar búsquedas
  const debouncedQuery = useDebounce(query, 300);
  
  // Efecto para búsqueda automática
  useEffect(() => {
    if (debouncedQuery.trim()) {
      dispatch(searchProducts(debouncedQuery));
    } else {
      dispatch(clearSearch());
    }
  }, [debouncedQuery, dispatch]);
  
  // Limpiar mensaje de éxito después de 3 segundos
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        dispatch(clearSuccessMessage());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage, dispatch]);
  
  // Handlers
  const handleSearchChange = (newQuery: string) => {
    dispatch(setQuery(newQuery));
  };
  
  const handleAddToCart = (product: any) => {
    dispatch(addToCart(product));
  };
  
  const handleRemoveFromCart = (productId: number) => {
    dispatch(removeFromCart(productId));
  };
  
  const handleFinalizeSale = async () => {
    if (cartItems.length === 0) return;
    
    const saleData = {
      user_id: 1, // TODO: Obtener del contexto de autenticación
      items: cartItems.map(item => ({
        product_id: item.id,
        quantity_sold: item.quantity_in_cart,
        price_at_time_of_sale: item.selling_price,
      })),
      total_amount: totalAmount,
    };
    
    const result = await dispatch(processSale(saleData));
    
    // Si la venta fue exitosa, limpiar carrito y búsqueda
    if (processSale.fulfilled.match(result)) {
      dispatch(clearCart());
      dispatch(setQuery(''));
      dispatch(clearSearch());
    }
  };
  
  return (
    <div className="pos-page">
      <h1>Punto de Venta</h1>
      
      <div className="pos-layout">
        <div className="pos-left-panel">
          <SearchSection
            query={query}
            results={results}
            isLoading={searchLoading}
            onQueryChange={handleSearchChange}
            onProductSelect={handleAddToCart}
          />
        </div>
        
        <div className="pos-right-panel">
          <CartSection
            items={cartItems}
            totalAmount={totalAmount}
            totalItems={totalItems}
            onRemoveItem={handleRemoveFromCart}
          />
          
          <SaleActions
            canFinalizeSale={cartItems.length > 0 && !isProcessing}
            isProcessing={isProcessing}
            onFinalizeSale={handleFinalizeSale}
          />
          
          <StatusMessages
            searchError={searchError}
            saleError={saleError}
            successMessage={successMessage}
          />
        </div>
      </div>
    </div>
  );
};

export default POSPageEnterprise;