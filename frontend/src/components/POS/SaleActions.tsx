// ==================================================================
// SALE ACTIONS - ACCIONES DE VENTA
// ==================================================================

import React from 'react';

interface SaleActionsProps {
  canFinalizeSale: boolean;
  isProcessing: boolean;
  onFinalizeSale: () => void;
}

export const SaleActions: React.FC<SaleActionsProps> = ({
  canFinalizeSale,
  isProcessing,
  onFinalizeSale,
}) => {
  return (
    <div className="sale-actions">
      <button
        onClick={onFinalizeSale}
        disabled={!canFinalizeSale}
        className={`finalize-sale-button ${canFinalizeSale ? 'enabled' : 'disabled'}`}
      >
        {isProcessing ? 'Procesando venta...' : 'Finalizar Venta'}
      </button>
    </div>
  );
};