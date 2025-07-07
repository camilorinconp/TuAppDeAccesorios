// /frontend/src/types/index.ts

export interface Product {
  id: number;
  sku: string;
  name: string;
  description?: string;
  image_url?: string;
  cost_price: number;
  selling_price: number;
  stock_quantity: number;
}

export interface CartItem extends Product {
  quantity_in_cart: number;
}

export interface SaleItem {
  product_id: number;
  quantity_sold: number;
  price_at_time_of_sale: number;
}

export interface SalePayload {
  user_id: number; // Este ID vendría del estado de autenticación
  items: SaleItem[];
  total_amount: number;
}

export interface Distributor {
  id: number;
  name: string;
  contact_person?: string;
  phone_number?: string;
  access_code: string;
}

export interface ConsignmentLoan {
  id: number;
  distributor_id: number;
  product_id: number;
  quantity_loaned: number;
  loan_date: string;
  return_due_date: string;
  status: 'en_prestamo' | 'devuelto';
  product?: Product | null; // Incluir el detalle del producto sería útil
}

export interface ConsignmentReportPayload {
  loan_id: number;
  quantity_sold: number;
  quantity_returned: number;
  report_date: string;
}

// Interfaz para la respuesta paginada de productos
export interface ProductListResponse {
  products: Product[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
}

// Interfaz para la paginación
export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}
