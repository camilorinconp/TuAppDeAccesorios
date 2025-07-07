import React from 'react';

interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

interface SimpleBarChartProps {
  data: ChartDataPoint[];
  title: string;
  subtitle?: string;
  height?: number;
  showValues?: boolean;
  valueFormatter?: (value: number) => string;
}

const SimpleBarChart: React.FC<SimpleBarChartProps> = ({
  data,
  title,
  subtitle,
  height = 200,
  showValues = true,
  valueFormatter = (value) => value.toLocaleString('es-CO')
}) => {
  const maxValue = Math.max(...data.map(d => d.value));
  
  const getBarColor = (index: number, customColor?: string) => {
    if (customColor) return customColor;
    
    const colors = [
      'var(--primary-500)',
      'var(--secondary-500)', 
      'var(--success-500)',
      'var(--warning-500)',
      'var(--error-500)'
    ];
    return colors[index % colors.length];
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3>{title}</h3>
        {subtitle && (
          <p style={{ 
            color: 'var(--text-secondary)', 
            fontSize: 'var(--text-sm)',
            margin: 0,
            marginTop: 'var(--spacing-xs)'
          }}>
            {subtitle}
          </p>
        )}
      </div>
      
      <div className="card-body">
        <div style={{ 
          display: 'flex', 
          alignItems: 'end', 
          justifyContent: 'space-between',
          height: `${height}px`,
          gap: 'var(--spacing-sm)',
          padding: 'var(--spacing-md) 0'
        }}>
          {data.map((item, index) => {
            const barHeight = (item.value / maxValue) * (height - 60);
            
            return (
              <div 
                key={item.label}
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center',
                  flex: 1,
                  gap: 'var(--spacing-xs)'
                }}
              >
                {showValues && (
                  <div style={{ 
                    fontSize: 'var(--text-xs)', 
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {valueFormatter(item.value)}
                  </div>
                )}
                
                <div
                  style={{
                    width: '100%',
                    maxWidth: '40px',
                    height: `${Math.max(barHeight, 4)}px`,
                    backgroundColor: getBarColor(index, item.color),
                    borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
                    transition: 'all var(--transition-normal)',
                    cursor: 'pointer',
                    position: 'relative'
                  }}
                  className="hover-glow"
                  title={`${item.label}: ${valueFormatter(item.value)}`}
                />
                
                <div style={{ 
                  fontSize: 'var(--text-xs)', 
                  color: 'var(--text-secondary)',
                  textAlign: 'center',
                  wordBreak: 'break-word',
                  lineHeight: '1.2'
                }}>
                  {item.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SimpleBarChart;