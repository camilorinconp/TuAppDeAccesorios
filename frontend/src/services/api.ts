// /frontend/src/services/api.ts
import { Product, SalePayload, ConsignmentReportPayload, Distributor, ConsignmentLoan, ProductFilters, CategoryInfo, BrandInfo, ProductFiltersResponse, ProductCategory } from '../types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Función para obtener headers de autenticación (ahora con cookies)
const getAuthHeaders = () => {
    return {
        'Content-Type': 'application/json',
        // Las cookies se envían automáticamente con credentials: 'include'
    };
};

const getDistributorAuthHeaders = () => {
    return {
        'Content-Type': 'application/json',
        // Las cookies se envían automáticamente con credentials: 'include'
    };
};

// Configuración por defecto para todas las peticiones
const defaultFetchOptions = {
    credentials: 'include' as RequestCredentials, // Incluir cookies en todas las peticiones
};

// Función helper para hacer peticiones a la API con manejo de errores estandarizado
export const apiRequest = async <T = any>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> => {
    const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
    
    const config: RequestInit = {
        ...defaultFetchOptions,
        headers: {
            ...getAuthHeaders(),
            ...options.headers,
        },
        ...options,
    };

    try {
        const response = await fetch(url, config);
        
        // Manejar diferentes códigos de estado
        if (response.status === 401) {
            // Token expirado o inválido
            try {
                await refreshToken();
                // Reintentar la petición original con el token refrescado
                const retryResponse = await fetch(url, config);
                if (!retryResponse.ok) {
                    throw new Error(`Request failed with status ${retryResponse.status}`);
                }
                return retryResponse.json();
            } catch (refreshError) {
                // Si falla el refresh, redirigir al login
                window.location.href = '/login';
                throw new Error('Session expired. Please login again.');
            }
        }
        
        if (response.status === 403) {
            throw new Error('Access forbidden. You do not have permission to perform this action.');
        }
        
        if (response.status === 404) {
            throw new Error('Resource not found.');
        }
        
        if (response.status >= 500) {
            throw new Error('Server error. Please try again later.');
        }
        
        if (!response.ok) {
            // Intentar obtener el mensaje de error del servidor
            try {
                const errorData = await response.json();
                throw new Error(errorData.detail || errorData.message || `Request failed with status ${response.status}`);
            } catch (parseError) {
                throw new Error(`Request failed with status ${response.status}`);
            }
        }
        
        // Si la respuesta está vacía, devolver null
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return null as T;
        }
        
        return response.json();
        
    } catch (error) {
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('Network error. Please check your connection and try again.');
    }
};

// --- Funciones de Autenticación ---
export const loginUser = async (username: string, password: string): Promise<{ access_token: string; token_type: string }> => {
    const details = {
        username: username,
        password: password,
    };
    const formBody = Object.keys(details).map(key => encodeURIComponent(key) + '=' + encodeURIComponent(details[key as keyof typeof details])).join('&');

    const response = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formBody,
        credentials: 'include', // Incluir cookies para recibir el token
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
    }
    return response.json();
};

export const loginDistributor = async (username: string, accessCode: string): Promise<{ access_token: string; token_type: string }> => {
    const details = {
        username: username,
        password: accessCode, // Usamos password para el access_code en el formulario
    };
    const formBody = Object.keys(details).map(key => encodeURIComponent(key) + '=' + encodeURIComponent(details[key as keyof typeof details])).join('&');

    const response = await fetch(`${API_URL}/distributor-token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formBody,
        credentials: 'include', // Incluir cookies para recibir el token
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Distributor login failed');
    }
    return response.json();
};

// Función para refrescar el token
export const refreshToken = async (): Promise<{ access_token: string; token_type: string }> => {
    const response = await fetch(`${API_URL}/refresh`, {
        method: 'POST',
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Failed to refresh token');
    }
    return response.json();
};

// Función para cerrar sesión
export const logoutUser = async (): Promise<void> => {
    await fetch(`${API_URL}/logout`, {
        method: 'POST',
        credentials: 'include',
    });
};

// --- Funciones de la API ---

// Productos
// Interfaz para la respuesta paginada de productos
interface ProductListResponse {
    products: Product[];
    total: number;
    skip: number;
    limit: number;
    has_next: boolean;
}

export const getProducts = async (
    skip: number = 0, 
    limit: number = 20, 
    filters?: ProductFilters
): Promise<ProductListResponse> => {
    const params = new URLSearchParams();
    params.append('page', Math.floor(skip / limit + 1).toString());
    params.append('per_page', limit.toString());
    
    if (filters?.search) params.append('search', filters.search);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.brand) params.append('brand', filters.brand);
    if (filters?.min_price !== undefined) params.append('min_price', filters.min_price.toString());
    if (filters?.max_price !== undefined) params.append('max_price', filters.max_price.toString());
    if (filters?.in_stock !== undefined) params.append('in_stock', filters.in_stock.toString());
    if (filters?.tags) params.append('tags', filters.tags);
    
    return apiRequest<ProductListResponse>(`/products/?${params.toString()}`);
};

// Mantener la función anterior para compatibilidad
export const getAllProducts = async (): Promise<Product[]> => {
    const response = await getProducts(0, 1000); // Obtener muchos productos
    return response.products;
};

export const createProduct = async (product: Product): Promise<Product> => {
    return apiRequest<Product>('/products/', {
        method: 'POST',
        body: JSON.stringify(product),
    });
};

export const updateProduct = async (productId: number, product: Partial<Product>): Promise<Product> => {
    return apiRequest<Product>(`/products/${productId}`, {
        method: 'PUT',
        body: JSON.stringify(product),
    });
};

// Ventas
export const postSale = async (saleData: SalePayload): Promise<any> => {
    return apiRequest('/pos/sales', {
        method: 'POST',
        body: JSON.stringify(saleData),
    });
};

// Consignación
export const getDistributorLoansByAccessCode = async (accessCode: string): Promise<{ loans: ConsignmentLoan[], distributor: Distributor }> => {
    // Ahora usamos el endpoint específico para distribuidores autenticados
    const loansResponse = await fetch(`${API_URL}/my-loans`, {
        headers: getDistributorAuthHeaders(),
        ...defaultFetchOptions,
    });
    if (!loansResponse.ok) throw new Error('Failed to fetch loans');
    const loans: ConsignmentLoan[] = await loansResponse.json();
    
    // Obtener información de productos
    const productsResponse = await fetch(`${API_URL}/products/`, {
        headers: getDistributorAuthHeaders(),
        ...defaultFetchOptions,
    });
    if (!productsResponse.ok) throw new Error('Failed to fetch products');
    const productData = await productsResponse.json();
    const products: Product[] = Array.isArray(productData) ? productData : productData.products || [];
    
    const loansWithProducts = loans.map(loan => ({
        ...loan,
        product: products.find(p => p.id === loan.product_id) || null
    }));

    // Como el distribuidor ya está autenticado, creamos un objeto distribuidor placeholder
    // En un escenario real, podrías obtener la información del distribuidor desde el token JWT o un endpoint específico
    const distributor: Distributor = {
        id: 1, // Este valor será el correcto desde el token JWT
        name: "Distribuidor Autenticado",
        access_code: accessCode,
        contact_info: ""
    };

    return { loans: loansWithProducts, distributor };
};

export const postConsignmentReport = async (reportData: ConsignmentReportPayload): Promise<any> => {
    return apiRequest('/consignments/reports', {
        method: 'POST',
        headers: getDistributorAuthHeaders(),
        body: JSON.stringify(reportData),
    });
};

// Función para buscar productos
export const searchProducts = async (query: string): Promise<Product[]> => {
    return apiRequest<Product[]>(`/products/search?q=${encodeURIComponent(query)}`);
};

// Función para eliminar producto
export const deleteProduct = async (productId: number): Promise<void> => {
    return apiRequest<void>(`/products/${productId}`, {
        method: 'DELETE',
    });
};

// Función para obtener un producto específico
export const getProduct = async (productId: number): Promise<Product> => {
    return apiRequest<Product>(`/products/${productId}`);
};

// Función para buscar producto por código de barras
export const searchProductByBarcode = async (barcode: string): Promise<Product> => {
    return apiRequest<Product>(`/products/search/barcode/${encodeURIComponent(barcode)}`);
};

// Función para buscar producto por código interno
export const searchProductByInternalCode = async (internalCode: string): Promise<Product> => {
    return apiRequest<Product>(`/products/search/internal-code/${encodeURIComponent(internalCode)}`);
};

// Función para validar disponibilidad de código de barras
export const validateBarcodeAvailability = async (barcode: string): Promise<{
    barcode: string;
    available: boolean;
    exists: boolean;
    message: string;
    existing_product?: {
        id: number;
        name: string;
        sku: string;
        barcode: string;
    };
}> => {
    return apiRequest(`/products/validate-barcode`, {
        method: 'POST',
        body: JSON.stringify({ barcode })
    });
};

// Función para verificar disponibilidad de SKU
export const checkSkuAvailability = async (sku: string): Promise<{
    sku: string;
    available: boolean;
    exists: boolean;
    message: string;
}> => {
    return apiRequest(`/products/check-sku/${encodeURIComponent(sku)}`);
};

// Función para obtener sugerencias de nombres de productos
export const getProductNameSuggestions = async (query: string, limit: number = 8): Promise<{
    search_term: string;
    suggestions: string[];
    count: number;
}> => {
    return apiRequest(`/products/suggest-names?q=${encodeURIComponent(query)}&limit=${limit}`);
};

// Función para obtener estadísticas
export const getStats = async (): Promise<any> => {
    return apiRequest('/stats');
};

// Función para obtener distribuidores
export const getDistributors = async (): Promise<Distributor[]> => {
    return apiRequest<Distributor[]>('/distributors/');
};

// Función para crear distribuidor
export const createDistributor = async (distributor: Omit<Distributor, 'id'>): Promise<Distributor> => {
    return apiRequest<Distributor>('/distributors/', {
        method: 'POST',
        body: JSON.stringify(distributor),
    });
};

// Función para actualizar distribuidor
export const updateDistributor = async (distributorId: number, distributor: Partial<Distributor>): Promise<Distributor> => {
    return apiRequest<Distributor>(`/distributors/${distributorId}`, {
        method: 'PUT',
        body: JSON.stringify(distributor),
    });
};

// Función para obtener préstamos de un distribuidor
export const getDistributorLoans = async (distributorId: number): Promise<ConsignmentLoan[]> => {
    return apiRequest<ConsignmentLoan[]>(`/distributors/${distributorId}/loans`);
};

// Función para crear préstamo de consignación
export const createConsignmentLoan = async (loan: Omit<ConsignmentLoan, 'id'>): Promise<ConsignmentLoan> => {
    return apiRequest<ConsignmentLoan>('/consignments/loans', {
        method: 'POST',
        body: JSON.stringify(loan),
    });
};

// Función para verificar estado de autenticación
export const verifyAuth = async (): Promise<{ username: string; role: string }> => {
    return apiRequest<{ username: string; role: string }>('/verify');
};

// Función para obtener perfil de usuario
export const getUserProfile = async (): Promise<any> => {
    return apiRequest('/users/me');
};

// Funciones para categorización y filtros

// Obtener información de categorías
export const getProductCategories = async (): Promise<CategoryInfo[]> => {
    return apiRequest<CategoryInfo[]>('/products/categories');
};

// Obtener información de marcas
export const getProductBrands = async (category?: ProductCategory): Promise<BrandInfo[]> => {
    const params = category ? `?category=${category}` : '';
    return apiRequest<BrandInfo[]>(`/products/brands${params}`);
};

// Obtener todos los filtros disponibles
export const getProductFilters = async (): Promise<ProductFiltersResponse> => {
    return apiRequest<ProductFiltersResponse>('/products/filters');
};

// Obtener productos por categoría específica
export const getProductsByCategory = async (
    category: ProductCategory,
    page: number = 1,
    per_page: number = 20,
    filters?: {
        brand?: string;
        min_price?: number;
        max_price?: number;
    }
): Promise<ProductListResponse> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('per_page', per_page.toString());
    
    if (filters?.brand) params.append('brand', filters.brand);
    if (filters?.min_price !== undefined) params.append('min_price', filters.min_price.toString());
    if (filters?.max_price !== undefined) params.append('max_price', filters.max_price.toString());
    
    return apiRequest<ProductListResponse>(`/products/by-category/${category}?${params.toString()}`);
};

// Función helper para manejo de errores de red
export const handleApiError = (error: Error): string => {
    if (error.message.includes('Network error')) {
        return 'Error de conexión. Verifica tu conexión a internet e intenta nuevamente.';
    }
    if (error.message.includes('Session expired')) {
        return 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.';
    }
    if (error.message.includes('Access forbidden')) {
        return 'No tienes permisos para realizar esta acción.';
    }
    if (error.message.includes('Server error')) {
        return 'Error del servidor. Por favor, intenta más tarde.';
    }
    return error.message || 'Ha ocurrido un error inesperado.';
};

// --- Funciones adicionales para Gestión de Distribuidores ---

export const deleteDistributor = async (id: number): Promise<{success: boolean, message: string}> => {
    return apiRequest<{success: boolean, message: string}>(`/distributors/${id}`, {
        method: 'DELETE'
    });
};

export const getAccessCodeStatistics = async (): Promise<{
    total_capacity: number;
    total_used: number;
    total_available: number;
    usage_percentage: number;
    highest_number_used: number;
    next_available: string;
    prefix: string;
}> => {
    return apiRequest<any>('/distributors/access-codes/statistics');
};

export const getNextAccessCode = async (): Promise<{next_code: string}> => {
    return apiRequest<{next_code: string}>('/distributors/access-codes/next');
};

export const validateAccessCode = async (code: string): Promise<{
    access_code: string;
    is_valid_format: boolean;
    is_available: boolean;
    is_usable: boolean;
}> => {
    return apiRequest<any>(`/distributors/access-codes/validate?access_code=${code}`, {
        method: 'POST'
    });
};
