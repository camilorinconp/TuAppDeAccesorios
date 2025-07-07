// ==================================================================
// PRODUCT SERVICE - SERVICIOS DE PRODUCTOS
// ==================================================================

import { Product } from '../types/core';
import { apiClient } from './apiClient';

export class ProductService {
  async search(query: string, limit: number = 10): Promise<Product[]> {
    const params = new URLSearchParams({
      q: query.trim(),
      limit: limit.toString(),
    });
    
    return apiClient.get<Product[]>(`/products/search?${params}`);
  }

  async getById(id: number): Promise<Product> {
    return apiClient.get<Product>(`/products/${id}`);
  }

  async getAll(page: number = 1, limit: number = 50): Promise<Product[]> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    
    return apiClient.get<Product[]>(`/products?${params}`);
  }

  async create(product: Omit<Product, 'id' | 'created_at' | 'updated_at'>): Promise<Product> {
    return apiClient.post<Product>('/products', product);
  }

  async update(id: number, product: Partial<Product>): Promise<Product> {
    return apiClient.put<Product>(`/products/${id}`, product);
  }

  async delete(id: number): Promise<void> {
    return apiClient.delete<void>(`/products/${id}`);
  }
}

export const productService = new ProductService();