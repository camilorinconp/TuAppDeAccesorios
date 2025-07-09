import React from 'react';

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ isDark, onToggle }) => {
  return (
    <button
      onClick={onToggle}
      className="theme-toggle"
      title={isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '20px',
        padding: '8px 12px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        color: 'var(--text-primary)',
        fontSize: '14px',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-tertiary)';
        e.currentTarget.style.transform = 'scale(1.05)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'var(--bg-secondary)';
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      <span
        style={{
          fontSize: '16px',
          transition: 'transform 0.3s ease',
          transform: isDark ? 'rotate(0deg)' : 'rotate(180deg)'
        }}
      >
        {isDark ? '🌙' : '☀️'}
      </span>
      <span style={{ fontWeight: '500' }}>
        {isDark ? 'Oscuro' : 'Claro'}
      </span>
    </button>
  );
};

export default ThemeToggle;