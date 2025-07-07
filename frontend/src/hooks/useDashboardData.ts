import { useState, useEffect } from 'react';

export interface DashboardStats {
  totalProducts: number;
  totalInventoryValue: number;
  lowStockProducts: number;
  outOfStockProducts: number;
  totalSales: number;
  totalSalesValue: number;
  topSellingProducts: Array<{
    id: number;
    name: string;
    sku: string;
    salesCount: number;
    revenue: number;
  }>;
  recentSales: Array<{
    id: number;
    date: string;
    total: number;
    itemsCount: number;
  }>;
  monthlyRevenue: Array<{
    month: string;
    revenue: number;
    sales: number;
  }>;
  categoryDistribution: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
}

export const useDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        
        // Simular datos del dashboard por ahora
        // En producción, estas serían llamadas reales a la API
        const mockStats: DashboardStats = {
          totalProducts: 150,
          totalInventoryValue: 12450000, // $12,450,000 COP
          lowStockProducts: 8,
          outOfStockProducts: 3,
          totalSales: 245,
          totalSalesValue: 8750000, // $8,750,000 COP
          topSellingProducts: [
            { id: 1, name: 'Funda iPhone 14', sku: 'CASE001', salesCount: 45, revenue: 1125000 },
            { id: 2, name: 'Cargador Samsung', sku: 'CHAR002', salesCount: 38, revenue: 950000 },
            { id: 3, name: 'Protector Pantalla', sku: 'PROT003', salesCount: 32, revenue: 640000 },
            { id: 4, name: 'Cable USB-C', sku: 'CABL004', salesCount: 28, revenue: 420000 },
            { id: 5, name: 'Audífonos Bluetooth', sku: 'AUDI005', salesCount: 22, revenue: 1100000 }
          ],
          recentSales: [
            { id: 1, date: '2025-01-07', total: 125000, itemsCount: 3 },
            { id: 2, date: '2025-01-07', total: 85000, itemsCount: 2 },
            { id: 3, date: '2025-01-06', total: 190000, itemsCount: 5 },
            { id: 4, date: '2025-01-06', total: 65000, itemsCount: 1 },
            { id: 5, date: '2025-01-05', total: 340000, itemsCount: 8 }
          ],
          monthlyRevenue: [
            { month: 'Ene', revenue: 2450000, sales: 78 },
            { month: 'Dic', revenue: 3200000, sales: 95 },
            { month: 'Nov', revenue: 2800000, sales: 82 },
            { month: 'Oct', revenue: 2100000, sales: 65 },
            { month: 'Sep', revenue: 2650000, sales: 73 },
            { month: 'Ago', revenue: 2950000, sales: 88 }
          ],
          categoryDistribution: [
            { category: 'Fundas', count: 45, percentage: 30 },
            { category: 'Cargadores', count: 38, percentage: 25.3 },
            { category: 'Protectores', count: 28, percentage: 18.7 },
            { category: 'Cables', count: 24, percentage: 16 },
            { category: 'Audífonos', count: 15, percentage: 10 }
          ]
        };

        // Simular delay de red
        await new Promise(resolve => setTimeout(resolve, 800));
        
        setStats(mockStats);
        setError(null);
      } catch (err) {
        setError('Error al cargar los datos del dashboard');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const refreshData = () => {
    setStats(null);
    setIsLoading(true);
    // Re-ejecutar la carga de datos
    // En producción, esto haría una nueva llamada a la API
  };

  return {
    stats,
    isLoading,
    error,
    refreshData
  };
};