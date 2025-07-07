import React from 'react';

interface DataListItem {
  id: number | string;
  primary: string;
  secondary?: string;
  value: string | number;
  subValue?: string;
  icon?: string;
  badge?: {
    text: string;
    color: 'success' | 'warning' | 'error' | 'info';
  };
}

interface DataListProps {
  title: string;
  subtitle?: string;
  data: DataListItem[];
  onItemClick?: (item: DataListItem) => void;
  showMore?: {
    text: string;
    onClick: () => void;
  };
  emptyMessage?: string;
}

const DataList: React.FC<DataListProps> = ({
  title,
  subtitle,
  data,
  onItemClick,
  showMore,
  emptyMessage = "No hay datos disponibles"
}) => {
  const getBadgeColor = (color: string) => {
    switch (color) {
      case 'success': return 'badge-success';
      case 'warning': return 'badge-warning';
      case 'error': return 'badge-error';
      case 'info': return 'badge-primary';
      default: return 'badge-primary';
    }
  };

  const formatValue = (value: string | number) => {
    if (typeof value === 'number') {
      return value.toLocaleString('es-CO');
    }
    return value;
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
      
      <div className="card-body" style={{ padding: 0 }}>
        {data.length === 0 ? (
          <div style={{ 
            padding: 'var(--spacing-xl)',
            textAlign: 'center',
            color: 'var(--text-tertiary)',
            fontSize: 'var(--text-sm)'
          }}>
            {emptyMessage}
          </div>
        ) : (
          <div>
            {data.map((item, index) => (
              <div
                key={item.id}
                onClick={() => onItemClick?.(item)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: 'var(--spacing-md) var(--spacing-lg)',
                  borderBottom: index < data.length - 1 ? '1px solid var(--border-color)' : 'none',
                  cursor: onItemClick ? 'pointer' : 'default',
                  transition: 'all var(--transition-fast)'
                }}
                className={onItemClick ? 'hover:bg-gray-50 dark:hover:bg-gray-800' : ''}
              >
                {item.icon && (
                  <div style={{ 
                    fontSize: '1.5rem',
                    marginRight: 'var(--spacing-md)',
                    opacity: 0.7
                  }}>
                    {item.icon}
                  </div>
                )}
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-sm)',
                    marginBottom: item.secondary ? 'var(--spacing-xs)' : 0,
                    wordBreak: 'break-word'
                  }}>
                    {item.primary}
                  </div>
                  
                  {item.secondary && (
                    <div style={{ 
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-secondary)',
                      wordBreak: 'break-word'
                    }}>
                      {item.secondary}
                    </div>
                  )}
                  
                  {item.badge && (
                    <span 
                      className={`badge ${getBadgeColor(item.badge.color)}`}
                      style={{ marginTop: 'var(--spacing-xs)' }}
                    >
                      {item.badge.text}
                    </span>
                  )}
                </div>
                
                <div style={{ 
                  textAlign: 'right',
                  marginLeft: 'var(--spacing-md)'
                }}>
                  <div style={{ 
                    fontWeight: '700',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-sm)'
                  }}>
                    {formatValue(item.value)}
                  </div>
                  
                  {item.subValue && (
                    <div style={{ 
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-tertiary)',
                      marginTop: 'var(--spacing-xs)'
                    }}>
                      {item.subValue}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {showMore && data.length > 0 && (
        <div className="card-footer">
          <button 
            onClick={showMore.onClick}
            className="btn btn-outline mobile-full"
            style={{ width: '100%' }}
          >
            {showMore.text}
          </button>
        </div>
      )}
    </div>
  );
};

export default DataList;