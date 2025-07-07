import React from 'react';
import { PaginationProps } from '../types';

const Pagination: React.FC<PaginationProps> = ({ 
    currentPage, 
    totalPages, 
    onPageChange, 
    disabled = false 
}) => {
    const getPageNumbers = () => {
        const pages = [];
        const maxVisiblePages = 5;
        
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        // Ajustar si estamos cerca del final
        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            pages.push(i);
        }
        
        return pages;
    };


    if (totalPages <= 1) {
        return null; // No mostrar paginación si hay solo una página o menos
    }

    return (
        <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            marginTop: '32px',
            gap: '8px'
        }}>
            {/* Botón Primera página */}
            <button
                className={`btn btn-sm ${
                    currentPage === 1 || disabled ? 'btn-ghost' : 'btn-outline'
                }`}
                onClick={() => onPageChange(1)}
                disabled={currentPage === 1 || disabled}
            >
                ««
            </button>

            {/* Botón Página anterior */}
            <button
                className={`btn btn-sm ${
                    currentPage === 1 || disabled ? 'btn-ghost' : 'btn-outline'
                }`}
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1 || disabled}
            >
                ‹
            </button>

            {/* Números de página */}
            {getPageNumbers().map(pageNum => (
                <button
                    key={pageNum}
                    className={`btn btn-sm ${
                        pageNum === currentPage 
                            ? 'btn-primary' 
                            : disabled 
                                ? 'btn-ghost' 
                                : 'btn-outline'
                    }`}
                    onClick={() => onPageChange(pageNum)}
                    disabled={disabled}
                >
                    {pageNum}
                </button>
            ))}

            {/* Botón Página siguiente */}
            <button
                className={`btn btn-sm ${
                    currentPage === totalPages || disabled ? 'btn-ghost' : 'btn-outline'
                }`}
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages || disabled}
            >
                ›
            </button>

            {/* Botón Última página */}
            <button
                className={`btn btn-sm ${
                    currentPage === totalPages || disabled ? 'btn-ghost' : 'btn-outline'
                }`}
                onClick={() => onPageChange(totalPages)}
                disabled={currentPage === totalPages || disabled}
            >
                »»
            </button>

            {/* Información de página */}
            <span style={{ 
                marginLeft: '16px', 
                fontSize: 'var(--text-sm)', 
                color: 'var(--text-tertiary)'
            }}>
                Página {currentPage} de {totalPages}
            </span>
        </div>
    );
};

export default Pagination;