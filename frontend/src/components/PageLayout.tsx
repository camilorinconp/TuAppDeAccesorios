import React from 'react';

interface PageLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  showBackButton?: boolean;
  onBack?: () => void;
}

const PageLayout: React.FC<PageLayoutProps> = ({
  children,
  title,
  subtitle,
  className = '',
  showBackButton = false,
  onBack
}) => {
  return (
    <div className={`container section ${className}`}>
      {(title || showBackButton) && (
        <div className="mobile-center space-y-mobile" style={{ marginBottom: 'var(--spacing-xl)' }}>
          {showBackButton && (
            <button
              onClick={onBack}
              className="btn btn-ghost btn-sm lg:hidden"
              style={{ 
                alignSelf: 'flex-start',
                marginBottom: 'var(--spacing-md)'
              }}
            >
              ← Volver
            </button>
          )}
          
          {title && (
            <div>
              <h1>{title}</h1>
              {subtitle && (
                <p style={{ 
                  color: 'var(--text-secondary)', 
                  marginTop: 'var(--spacing-sm)',
                  fontSize: 'var(--text-lg)'
                }}>
                  {subtitle}
                </p>
              )}
            </div>
          )}
        </div>
      )}
      
      <div className="space-y-mobile">
        {children}
      </div>
    </div>
  );
};

export default PageLayout;