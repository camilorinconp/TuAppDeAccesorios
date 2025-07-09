// /frontend/src/types/index.ts

// Enum de categorías de productos
export enum ProductCategory {
  FUNDAS = "fundas",
  CARGADORES = "cargadores", 
  CABLES = "cables",
  AUDIFONOS = "audifonos",
  VIDRIOS = "vidrios_templados",
  SOPORTES = "soportes",
  BATERIAS = "baterias_externas",
  MEMORIAS = "memorias",
  LIMPIEZA = "limpieza",
  VEHICULOS = "vehiculos",
  OTROS = "otros"
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description?: string;
  image_url?: string;
  cost_price: number;
  selling_price: number;
  wholesale_price?: number;
  stock_quantity: number;
  
  // Código de barras
  barcode?: string;
  internal_code?: string;
  
  // Campos de categorización
  category: ProductCategory;
  subcategory?: string;
  brand?: string;
  tags?: string;
  created_at?: string;
  updated_at?: string;
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
  contact_info?: string; // Agregado para compatibilidad
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

// Interfaces para filtros y categorización
export interface ProductFilters {
  search?: string;
  category?: ProductCategory;
  brand?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  tags?: string;
}

export interface CategoryInfo {
  category: ProductCategory;
  name: string;
  count: number;
  description: string;
}

export interface BrandInfo {
  brand: string;
  count: number;
  categories: string[];
}

export interface ProductFiltersResponse {
  categories: CategoryInfo[];
  brands: BrandInfo[];
  price_range: {
    min: number;
    max: number;
    avg: number;
  };
  total_products: number;
}

// Mapeo de nombres amigables para categorías
export const CATEGORY_NAMES: Record<ProductCategory, string> = {
  [ProductCategory.FUNDAS]: "Fundas y Carcasas",
  [ProductCategory.CARGADORES]: "Cargadores",
  [ProductCategory.CABLES]: "Cables",
  [ProductCategory.AUDIFONOS]: "Audífonos",
  [ProductCategory.VIDRIOS]: "Vidrios Templados",
  [ProductCategory.SOPORTES]: "Soportes",
  [ProductCategory.BATERIAS]: "Baterías Externas",
  [ProductCategory.MEMORIAS]: "Memorias",
  [ProductCategory.LIMPIEZA]: "Limpieza",
  [ProductCategory.VEHICULOS]: "Accesorios Vehiculares",
  [ProductCategory.OTROS]: "Otros"
};

// Iconos para categorías
export const CATEGORY_ICONS: Record<ProductCategory, string> = {
  [ProductCategory.FUNDAS]: "📱",
  [ProductCategory.CARGADORES]: "🔌",
  [ProductCategory.CABLES]: "🔌",
  [ProductCategory.AUDIFONOS]: "🎧",
  [ProductCategory.VIDRIOS]: "🛡️",
  [ProductCategory.SOPORTES]: "📱",
  [ProductCategory.BATERIAS]: "🔋",
  [ProductCategory.MEMORIAS]: "💾",
  [ProductCategory.LIMPIEZA]: "🧽",
  [ProductCategory.VEHICULOS]: "🚗",
  [ProductCategory.OTROS]: "📦"
};
