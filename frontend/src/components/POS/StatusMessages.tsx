// ==================================================================
// STATUS MESSAGES - MENSAJES DE ESTADO Y ERRORES
// ==================================================================

import React from 'react';

interface StatusMessagesProps {
  searchError: string | null;
  saleError: string | null;
  successMessage: string | null;
}

export const StatusMessages: React.FC<StatusMessagesProps> = ({
  searchError,
  saleError,
  successMessage,
}) => {
  return (
    <div className="status-messages">
      {successMessage && (
        <div className="message success">
          ✅ {successMessage}
        </div>
      )}
      
      {saleError && (
        <div className="message error">
          ❌ {saleError}
        </div>
      )}
      
      {searchError && (
        <div className="message error">
          🔍 Error en búsqueda: {searchError}
        </div>
      )}
    </div>
  );
};