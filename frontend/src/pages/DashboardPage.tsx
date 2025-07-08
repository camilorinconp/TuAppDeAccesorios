import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageLayout from '../components/PageLayout';
import MetricCard from '../components/Dashboard/MetricCard';
import SimpleBarChart from '../components/Dashboard/SimpleBarChart';
import DataList from '../components/Dashboard/DataList';
import { useDashboardData } from '../hooks/useDashboardData';

const DashboardPage: React.FC = () => {
  const { stats, isLoading, error, refreshData } = useDashboardData();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <PageLayout title="Dashboard" subtitle="Cargando información del negocio...">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-mobile">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card" style={{ height: '120px' }}>
              <div className="card-body mobile-center">
                <div className="spinner"></div>
              </div>
            </div>
          ))}
        </div>
      </PageLayout>
    );
  }

  if (error || !stats) {
    return (
      <PageLayout title="Dashboard" subtitle="Panel de control de TuAppDeAccesorios">
        <div className="alert alert-error">
          <span>⚠️ {error || 'Error al cargar los datos'}</span>
          <button onClick={refreshData} className="btn btn-outline btn-sm">
            Reintentar
          </button>
        </div>
      </PageLayout>
    );
  }

  const formatCurrency = (amount: number) => {
    return `$${amount.toLocaleString('es-CO')} COP`;
  };

  const topSellingProductsData = stats.topSellingProducts.map(product => ({
    id: product.id,
    primary: product.name,
    secondary: `SKU: ${product.sku}`,
    value: product.salesCount,
    subValue: formatCurrency(product.revenue),
    icon: '📦'
  }));

  const recentSalesData = stats.recentSales.map(sale => ({
    id: sale.id,
    primary: `Venta #${sale.id}`,
    secondary: new Date(sale.date).toLocaleDateString('es-CO'),
    value: formatCurrency(sale.total),
    subValue: `${sale.itemsCount} productos`,
    icon: '💰'
  }));

  const monthlyRevenueChartData = stats.monthlyRevenue.map(item => ({
    label: item.month,
    value: item.revenue / 1000000, // Convertir a millones para el gráfico
  }));

  const categoryChartData = stats.categoryDistribution.map((category) => ({
    label: category.category,
    value: category.count,
  }));

  return (
    <PageLayout 
      title="Dashboard" 
      subtitle="Panel de control de TuAppDeAccesorios"
    >
      {/* Botón de actualización */}
      <div className="flex-mobile" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
          Última actualización: {new Date().toLocaleTimeString('es-CO')}
        </div>
        <button onClick={refreshData} className="btn btn-outline btn-sm">
          🔄 Actualizar
        </button>
      </div>

      {/* Métricas principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-mobile">
        <MetricCard
          title="Total Productos"
          value={stats.totalProducts}
          subtitle="en inventario"
          icon="📦"
          color="primary"
          trend={{ value: 12, isPositive: true, period: "mes anterior" }}
          onClick={() => navigate('/inventory')}
        />
        
        <MetricCard
          title="Valor Inventario"
          value={formatCurrency(stats.totalInventoryValue)}
          subtitle="valor total en stock"
          icon="💎"
          color="success"
          trend={{ value: 8.5, isPositive: true, period: "mes anterior" }}
        />
        
        <MetricCard
          title="Stock Bajo"
          value={stats.lowStockProducts}
          subtitle="productos con poco stock"
          icon="⚠️"
          color="warning"
          onClick={() => navigate('/inventory')}
        />
        
        <MetricCard
          title="Sin Stock"
          value={stats.outOfStockProducts}
          subtitle="productos agotados"
          icon="🚫"
          color="error"
          onClick={() => navigate('/inventory')}
        />
      </div>

      {/* Métricas de ventas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-mobile">
        <MetricCard
          title="Ventas del Mes"
          value={stats.totalSales}
          subtitle="transacciones completadas"
          icon="🛒"
          color="info"
          trend={{ value: 15.2, isPositive: true, period: "mes anterior" }}
          onClick={() => navigate('/pos-test')}
        />
        
        <MetricCard
          title="Ingresos del Mes"
          value={formatCurrency(stats.totalSalesValue)}
          subtitle="ingresos por ventas"
          icon="💰"
          color="success"
          trend={{ value: 22.1, isPositive: true, period: "mes anterior" }}
        />
        
        <MetricCard
          title="Venta Promedio"
          value={formatCurrency(Math.round(stats.totalSalesValue / stats.totalSales))}
          subtitle="por transacción"
          icon="📊"
          color="primary"
        />
        
        <MetricCard
          title="Margen Estimado"
          value="45%"
          subtitle="margen de ganancia"
          icon="📈"
          color="success"
          trend={{ value: 3.2, isPositive: true, period: "mes anterior" }}
        />
      </div>

      {/* Gráficos y listas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-mobile">
        {/* Ingresos mensuales */}
        <SimpleBarChart
          title="Ingresos por Mes"
          subtitle="Últimos 6 meses (en millones COP)"
          data={monthlyRevenueChartData}
          valueFormatter={(value) => `$${value.toFixed(1)}M`}
          height={250}
        />

        {/* Distribución por categorías */}
        <SimpleBarChart
          title="Productos por Categoría"
          subtitle="Distribución del inventario"
          data={categoryChartData}
          height={250}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-mobile">
        {/* Productos más vendidos */}
        <DataList
          title="Productos Más Vendidos"
          subtitle="Top 5 del mes actual"
          data={topSellingProductsData}
          onItemClick={() => navigate('/inventory')}
          showMore={{
            text: "Ver todos los productos",
            onClick: () => navigate('/inventory')
          }}
        />

        {/* Ventas recientes */}
        <DataList
          title="Ventas Recientes"
          subtitle="Últimas 5 transacciones"
          data={recentSalesData}
          onItemClick={() => navigate('/pos-test')}
          showMore={{
            text: "Ver historial completo",
            onClick: () => navigate('/pos-test')
          }}
        />
      </div>

      {/* Acciones rápidas */}
      <div className="card">
        <div className="card-header">
          <h3>🚀 Acciones Rápidas</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', margin: 0, marginTop: 'var(--spacing-xs)' }}>
            Accede rápidamente a las funciones principales
          </p>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-mobile">
            <Link to="/inventory" className="btn btn-primary mobile-full" style={{ textDecoration: 'none' }}>
              📦 Gestionar Inventario
            </Link>
            <Link to="/pos-test" className="btn btn-success mobile-full" style={{ textDecoration: 'none' }}>
              💰 Nueva Venta
            </Link>
            <Link to="/consignments" className="btn btn-secondary mobile-full" style={{ textDecoration: 'none' }}>
              🏪 Préstamos
            </Link>
            <Link to="/distributor-portal" className="btn btn-outline mobile-full" style={{ textDecoration: 'none' }}>
              👤 Portal Distribuidores
            </Link>
          </div>
        </div>
      </div>

      {/* Alertas y notificaciones */}
      {(stats.lowStockProducts > 0 || stats.outOfStockProducts > 0) && (
        <div className="card" style={{ borderLeft: '4px solid var(--warning-500)' }}>
          <div className="card-header">
            <h3>⚠️ Alertas de Inventario</h3>
          </div>
          <div className="card-body">
            <div className="space-y-mobile">
              {stats.outOfStockProducts > 0 && (
                <div className="alert alert-error">
                  🚫 Tienes {stats.outOfStockProducts} productos sin stock. 
                  <Link to="/inventory" style={{ marginLeft: 'var(--spacing-sm)', color: 'inherit', textDecoration: 'underline' }}>
                    Revisar ahora
                  </Link>
                </div>
              )}
              
              {stats.lowStockProducts > 0 && (
                <div className="alert alert-warning">
                  ⚠️ {stats.lowStockProducts} productos tienen stock bajo. 
                  <Link to="/inventory" style={{ marginLeft: 'var(--spacing-sm)', color: 'inherit', textDecoration: 'underline' }}>
                    Ver detalles
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default DashboardPage;