// ==================================================================
// TIPOS CORE DEL SISTEMA - DEFINICIONES CENTRALIZADAS
// ==================================================================

export interface Product {
  id: number;
  name: string;
  sku: string;
  cost_price: number;
  selling_price: number;
  stock_quantity: number;
  description?: string;
  image_url?: string;
}

export interface CartItem extends Product {
  quantity_in_cart: number;
}

export interface SaleItem {
  product_id: number;
  quantity_sold: number;
  price_at_time_of_sale: number;
}

export interface Sale {
  id?: number;
  user_id: number;
  items: SaleItem[];
  total_amount: number;
  created_at?: string;
}

export interface SalePayload {
  user_id: number;
  items: SaleItem[];
  total_amount: number;
}

// Estados de la aplicación
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface SearchState extends LoadingState {
  query: string;
  results: Product[];
}

export interface SaleState extends LoadingState {
  isProcessing: boolean;
  lastSale: Sale | null;
  successMessage: string | null;
}

// Respuestas de API
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export class ApiError extends Error {
  public code: string | undefined;
  public details: unknown | undefined;

  constructor(message: string, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code ?? undefined;
    this.details = details ?? undefined;
  }
}