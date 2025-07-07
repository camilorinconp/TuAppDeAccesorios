// ==================================================================
// SALE SERVICE - SERVICIOS DE VENTAS
// ==================================================================

import { Sale, SalePayload } from '../types/core';
import { apiClient } from './apiClient';

export class SaleService {
  async create(saleData: SalePayload): Promise<Sale> {
    return apiClient.post<Sale>('/sales', saleData);
  }

  async getById(id: number): Promise<Sale> {
    return apiClient.get<Sale>(`/sales/${id}`);
  }

  async getAll(page: number = 1, limit: number = 50): Promise<Sale[]> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    
    return apiClient.get<Sale[]>(`/sales?${params}`);
  }

  async getByDateRange(startDate: string, endDate: string): Promise<Sale[]> {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    
    return apiClient.get<Sale[]>(`/sales/date-range?${params}`);
  }
}

export const saleService = new SaleService();