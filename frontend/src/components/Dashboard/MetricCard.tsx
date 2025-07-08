import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  trend?: {
    value: number;
    isPositive: boolean;
    period: string;
  };
  color?: 'primary' | 'success' | 'warning' | 'error' | 'info';
  onClick?: () => void;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = 'primary',
  onClick
}) => {
  // const getColorClasses = () => {
  //   switch (color) {
  //     case 'success': return 'border-l-4 border-l-green-500';
  //     case 'warning': return 'border-l-4 border-l-yellow-500';
  //     case 'error': return 'border-l-4 border-l-red-500';
  //     case 'info': return 'border-l-4 border-l-blue-400';
  //     default: return 'border-l-4 border-l-blue-500';
  //   }
  // };

  return (
    <div 
      className={`card hover-lift ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      style={{ 
        borderLeft: `4px solid var(--${color}-500)`,
        transition: 'all var(--transition-fast)'
      }}
    >
      <div className="card-body">
        <div className="flex-mobile" style={{ alignItems: 'flex-start', gap: 'var(--spacing-md)' }}>
          <div style={{ 
            fontSize: '2.5rem',
            opacity: 0.8,
            minWidth: '60px',
            textAlign: 'center'
          }}>
            {icon}
          </div>
          
          <div style={{ flex: 1 }}>
            <div style={{ 
              fontSize: 'var(--text-sm)', 
              color: 'var(--text-secondary)',
              marginBottom: 'var(--spacing-xs)',
              fontWeight: '500'
            }}>
              {title}
            </div>
            
            <div style={{ 
              fontSize: 'var(--text-2xl)', 
              fontWeight: '700',
              color: 'var(--text-primary)',
              marginBottom: subtitle ? 'var(--spacing-xs)' : '0'
            }}>
              {typeof value === 'number' ? value.toLocaleString('es-CO') : value}
            </div>
            
            {subtitle && (
              <div style={{ 
                fontSize: 'var(--text-xs)', 
                color: 'var(--text-tertiary)',
                marginBottom: trend ? 'var(--spacing-sm)' : '0'
              }}>
                {subtitle}
              </div>
            )}
            
            {trend && (
              <div className="flex-mobile" style={{ 
                alignItems: 'center', 
                gap: 'var(--spacing-xs)',
                fontSize: 'var(--text-xs)'
              }}>
                <span style={{
                  color: trend.isPositive ? 'var(--success-500)' : 'var(--error-500)',
                  fontWeight: '600'
                }}>
                  {trend.isPositive ? '↗' : '↘'} {trend.value}%
                </span>
                <span style={{ color: 'var(--text-tertiary)' }}>
                  vs {trend.period}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;