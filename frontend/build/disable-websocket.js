// Interceptar y deshabilitar WebSocket completamente
(function() {
    // Guardar el WebSocket original
    const OriginalWebSocket = window.WebSocket;
    
    // Reemplazar WebSocket con una versión que no hace nada
    window.WebSocket = function(url, protocols) {
        console.log('🚫 WebSocket bloqueado:', url);
        
        // Crear un objeto mock que simula WebSocket pero no conecta
        const mockWebSocket = {
            readyState: 3, // CLOSED
            CONNECTING: 0,
            OPEN: 1,
            CLOSING: 2,
            CLOSED: 3,
            close: function() {},
            send: function() {},
            addEventListener: function() {},
            removeEventListener: function() {},
            dispatchEvent: function() { return true; }
        };
        
        // Simular que se cerró inmediatamente
        setTimeout(() => {
            if (mockWebSocket.onclose) {
                mockWebSocket.onclose({ code: 1000, reason: 'Blocked by disable-websocket.js' });
            }
        }, 0);
        
        return mockWebSocket;
    };
    
    // Copiar propiedades estáticas
    window.WebSocket.CONNECTING = 0;
    window.WebSocket.OPEN = 1;
    window.WebSocket.CLOSING = 2;
    window.WebSocket.CLOSED = 3;
    
    console.log('🚫 WebSocket completamente deshabilitado');
})();