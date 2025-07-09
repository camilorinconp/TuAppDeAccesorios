import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageLayout from '../components/PageLayout';
import MetricCard from '../components/Dashboard/MetricCard';
import SimpleBarChart from '../components/Dashboard/SimpleBarChart';
import DataList from '../components/Dashboard/DataList';
import { useDashboardData } from '../hooks/useDashboardData';

const DashboardPage: React.FC = () => {
  const { stats, isLoading, error, refreshData } = useDashboardData();
  const navigate = useNavigate();
  const [selectedTimeframe, setSelectedTimeframe] = useState('today');

  if (isLoading) {
    return (
      <div style={{ 
        padding: '32px',
        backgroundColor: 'var(--bg-secondary)',
        minHeight: '100vh'
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto'
        }}>
          <div style={{ marginBottom: '32px' }}>
            <div style={{ 
              width: '200px', 
              height: '32px', 
              backgroundColor: 'var(--gray-300)', 
              borderRadius: '8px',
              marginBottom: '8px',
              animation: 'pulse 1.5s ease-in-out infinite'
            }}></div>
            <div style={{ 
              width: '300px', 
              height: '20px', 
              backgroundColor: 'var(--gray-300)', 
              borderRadius: '4px',
              animation: 'pulse 1.5s ease-in-out infinite'
            }}></div>
          </div>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
            gap: '24px' 
          }}>
            {[...Array(6)].map((_, i) => (
              <div key={i} style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: '16px',
                padding: '24px',
                height: '140px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                animation: 'pulse 1.5s ease-in-out infinite'
              }}>
                <div style={{ 
                  width: '100%', 
                  height: '20px', 
                  backgroundColor: 'var(--gray-300)', 
                  borderRadius: '4px',
                  marginBottom: '16px'
                }}></div>
                <div style={{ 
                  width: '60%', 
                  height: '32px', 
                  backgroundColor: 'var(--gray-300)', 
                  borderRadius: '4px'
                }}></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div style={{ 
        padding: '32px',
        backgroundColor: 'var(--bg-secondary)',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '16px',
          padding: '48px',
          textAlign: 'center',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
          maxWidth: '500px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--error-600)' }}>Error al cargar el dashboard</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            {error || 'No se pudieron cargar los datos del negocio'}
          </p>
          <button 
            onClick={refreshData} 
            style={{
              backgroundColor: 'var(--primary-500)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              padding: '12px 24px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600'
            }}
          >
            🔄 Reintentar
          </button>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const quickActions = [
    {
      title: 'Nueva Venta',
      description: 'Registrar venta',
      icon: '💰',
      color: 'var(--success-500)',
      path: '/pos',
      priority: 'high'
    },
    {
      title: 'Inventario',
      description: 'Gestionar productos',
      icon: '📦',
      color: 'var(--primary-500)',
      path: '/inventory',
      priority: 'high'
    },
    {
      title: 'Consignaciones',
      description: 'Gestión en Consignación',
      icon: '🏪',
      color: 'var(--secondary-500)',
      path: '/consignments',
      priority: 'medium'
    },
    {
      title: 'Distribuidores',
      description: 'Portal clientes',
      icon: '👥',
      color: 'var(--warning-500)',
      path: '/distributor-portal',
      priority: 'medium'
    }
  ];

  const kpiCards = [
    {
      title: 'Ventas Hoy',
      value: stats.totalSales.toString(),
      subtitle: 'transacciones',
      icon: '📊',
      color: 'var(--success-500)',
      trend: { value: 15.2, isPositive: true },
      onClick: () => navigate('/pos')
    },
    {
      title: 'Ingresos Hoy',
      value: formatCurrency(stats.totalSalesValue),
      subtitle: 'ingresos totales',
      icon: '💰',
      color: 'var(--success-600)',
      trend: { value: 22.1, isPositive: true }
    },
    {
      title: 'Productos',
      value: stats.totalProducts.toString(),
      subtitle: 'en inventario',
      icon: '📦',
      color: 'var(--primary-500)',
      trend: { value: 12, isPositive: true },
      onClick: () => navigate('/inventory')
    },
    {
      title: 'Stock Crítico',
      value: (stats.lowStockProducts + stats.outOfStockProducts).toString(),
      subtitle: 'productos afectados',
      icon: '⚠️',
      color: stats.lowStockProducts + stats.outOfStockProducts > 0 ? 'var(--error-500)' : 'var(--success-500)',
      trend: { value: -5, isPositive: false },
      onClick: () => navigate('/inventory')
    }
  ];

  return (
    <div style={{ 
      backgroundColor: 'var(--bg-secondary)',
      minHeight: '100vh',
      padding: '24px'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto'
      }}>
        {/* Header moderno */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'flex-start',
            marginBottom: '8px'
          }}>
            <div>
              <h1 style={{ 
                margin: 0, 
                fontSize: '32px', 
                fontWeight: '800',
                background: 'var(--gradient-primary)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                marginBottom: '4px'
              }}>
                Dashboard Operacional
              </h1>
              <p style={{ 
                margin: 0, 
                color: 'var(--text-secondary)', 
                fontSize: '16px',
                fontWeight: '400'
              }}>
                Centro de control de TuAppDeAccesorios
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <select 
                value={selectedTimeframe}
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '14px'
                }}
              >
                <option value="today">Hoy</option>
                <option value="week">Esta semana</option>
                <option value="month">Este mes</option>
                <option value="quarter">Trimestre</option>
              </select>
              <button 
                onClick={refreshData}
                style={{
                  padding: '8px 16px',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                  e.currentTarget.style.borderColor = 'var(--text-muted)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-card)';
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                }}
              >
                🔄 Actualizar
              </button>
            </div>
          </div>
        </div>

        {/* Acciones rápidas - Centro de control en la parte superior */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '32px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          border: '2px solid var(--border-color)'
        }}>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ 
              margin: '0 0 4px 0', 
              fontSize: '20px', 
              fontWeight: '700',
              color: 'var(--text-primary)'
            }}>
              🚀 Centro de Control
            </h2>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px' }}>
              Acciones principales para operar tu negocio
            </p>
          </div>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px'
          }}>
            {quickActions.map((action, index) => (
              <Link
                key={index}
                to={action.path}
                style={{
                  textDecoration: 'none',
                  backgroundColor: 'var(--bg-card)',
                  border: `2px solid ${action.color}20`,
                  borderRadius: '12px',
                  padding: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = `0 8px 25px ${action.color}30`;
                  e.currentTarget.style.borderColor = action.color;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                  e.currentTarget.style.borderColor = `${action.color}20`;
                }}
              >
                <div style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '12px',
                  backgroundColor: `${action.color}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px'
                }}>
                  {action.icon}
                </div>
                <div>
                  <h3 style={{ 
                    margin: '0 0 2px 0', 
                    fontSize: '16px', 
                    fontWeight: '600',
                    color: 'var(--text-primary)'
                  }}>
                    {action.title}
                  </h3>
                  <p style={{ 
                    margin: 0, 
                    fontSize: '13px', 
                    color: 'var(--text-secondary)'
                  }}>
                    {action.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* KPIs principales */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
          marginBottom: '32px'
        }}>
          {kpiCards.map((kpi, index) => (
            <div
              key={index}
              onClick={kpi.onClick}
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: '16px',
                padding: '24px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                cursor: kpi.onClick ? 'pointer' : 'default',
                transition: 'all 0.2s ease',
                border: '1px solid var(--border-color)'
              }}
              onMouseEnter={(e) => {
                if (kpi.onClick) {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
                }
              }}
              onMouseLeave={(e) => {
                if (kpi.onClick) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
                }
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '10px',
                  backgroundColor: `${kpi.color}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px'
                }}>
                  {kpi.icon}
                </div>
                {kpi.trend && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 8px',
                    borderRadius: '6px',
                    backgroundColor: kpi.trend.isPositive ? 'var(--success-100)' : 'var(--error-100)',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: kpi.trend.isPositive ? 'var(--success-800)' : 'var(--error-600)'
                  }}>
                    {kpi.trend.isPositive ? '↗️' : '↘️'}
                    {Math.abs(kpi.trend.value)}%
                  </div>
                )}
              </div>
              
              <div>
                <h3 style={{ 
                  margin: '0 0 4px 0', 
                  fontSize: '13px', 
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  {kpi.title}
                </h3>
                <p style={{ 
                  margin: '0 0 4px 0', 
                  fontSize: '24px', 
                  fontWeight: '700',
                  color: 'var(--text-primary)'
                }}>
                  {kpi.value}
                </p>
                <p style={{ 
                  margin: 0, 
                  fontSize: '12px', 
                  color: 'var(--text-tertiary)'
                }}>
                  {kpi.subtitle}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Alertas críticas */}
        {(stats.lowStockProducts > 0 || stats.outOfStockProducts > 0) && (
          <div style={{
            backgroundColor: 'var(--error-50)',
            border: '1px solid var(--error-200)',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '32px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ fontSize: '20px' }}>🚨</div>
              <h3 style={{ margin: 0, color: 'var(--error-600)', fontSize: '16px', fontWeight: '600' }}>
                Alertas de Inventario
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {stats.outOfStockProducts > 0 && (
                <div style={{ 
                  padding: '12px 16px', 
                  backgroundColor: 'var(--error-100)', 
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{ color: 'var(--error-800)', fontSize: '14px', fontWeight: '500' }}>
                    🚫 {stats.outOfStockProducts} productos sin stock
                  </span>
                  <Link 
                    to="/inventory" 
                    style={{ 
                      color: 'var(--error-600)', 
                      textDecoration: 'none', 
                      fontSize: '13px', 
                      fontWeight: '600' 
                    }}
                  >
                    Revisar ahora →
                  </Link>
                </div>
              )}
              
              {stats.lowStockProducts > 0 && (
                <div style={{ 
                  padding: '12px 16px', 
                  backgroundColor: 'var(--warning-100)', 
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{ color: 'var(--warning-800)', fontSize: '14px', fontWeight: '500' }}>
                    ⚠️ {stats.lowStockProducts} productos con stock bajo
                  </span>
                  <Link 
                    to="/inventory" 
                    style={{ 
                      color: 'var(--warning-600)', 
                      textDecoration: 'none', 
                      fontSize: '13px', 
                      fontWeight: '600' 
                    }}
                  >
                    Ver detalles →
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Análisis y gráficos */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: '24px',
          marginBottom: '32px'
        }}>
          {/* Gráfico de ingresos */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            <SimpleBarChart
              title="Ingresos Mensuales"
              subtitle="Evolución de ingresos (millones COP)"
              data={stats.monthlyRevenue.map(item => ({
                label: item.month,
                value: item.revenue / 1000000
              }))}
              valueFormatter={(value) => `$${value.toFixed(1)}M`}
              height={280}
            />
          </div>

          {/* Productos más vendidos */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            <DataList
              title="Top Productos"
              subtitle="Más vendidos este período"
              data={stats.topSellingProducts.slice(0, 5).map(product => ({
                id: product.id,
                primary: product.name,
                secondary: `SKU: ${product.sku}`,
                value: product.salesCount,
                subValue: formatCurrency(product.revenue),
                icon: '📦'
              }))}
              onItemClick={() => navigate('/inventory')}
              showMore={{
                text: "Ver inventario completo",
                onClick: () => navigate('/inventory')
              }}
            />
          </div>
        </div>

        {/* Información adicional */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          textAlign: 'center'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '16px' }}>
            Sistema Actualizado
          </h3>
          <p style={{ margin: 0, color: 'var(--text-tertiary)', fontSize: '14px' }}>
            Última sincronización: {new Date().toLocaleString('es-CO')} • 
            Datos en tiempo real conectados
          </p>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default DashboardPage;