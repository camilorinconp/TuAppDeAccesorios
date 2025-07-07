// k6/script.js
//
// Este es un script de prueba de carga básico para k6.
// Simula una carga de usuarios moderada en los endpoints más comunes.
//
// Para ejecutar: k6 run k6/script.js

import http from 'k6/http';
import { check, sleep, group } from 'k6';

// --- Opciones de la Prueba ---
export const options = {
  stages: [
    { duration: '1m', target: 50 },  // Rampa de 0 a 50 usuarios en 1 minuto
    { duration: '3m', target: 50 },  // Mantener 50 usuarios por 3 minutos
    { duration: '1m', target: 0 },   // Rampa de bajada a 0
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'], // Menos del 1% de las peticiones deben fallar
    http_req_duration: ['p(95)<800'], // El 95% de las peticiones deben ser < 800ms
  },
};

const BASE_URL = __ENV.API_URL || 'https://api.tudominio.com';
const USERNAME = __ENV.TEST_USER || 'admin';
const PASSWORD = __ENV.TEST_PASSWORD || 'password123';

let accessToken;

// --- Flujo de la Prueba ---

export function setup() {
  // 1. Autenticarse para obtener un token
  const res = http.post(`${BASE_URL}/token`, {
    username: USERNAME,
    password: PASSWORD,
  });
  check(res, { 'login successful': (r) => r.status === 200 });
  accessToken = res.json('access_token');
  return { token: accessToken };
}

export default function (data) {
  if (!data.token) {
    return; // No continuar si el login falló
  }

  const params = {
    headers: {
      Authorization: `Bearer ${data.token}`,
    },
  };

  group('API Endpoints', function () {
    // 2. Cargar la lista de productos
    group('Get Products', function () {
      const res = http.get(`${BASE_URL}/products/?limit=20`, params);
      check(res, { 'get products status 200': (r) => r.status === 200 });
    });

    // 3. Realizar una búsqueda de producto
    group('Search Products', function () {
      const res = http.get(`${BASE_URL}/products/search?q=case`, params);
      check(res, { 'search products status 200': (r) => r.status === 200 });
    });

    // 4. Cargar el historial de ventas
    group('Get Sales History', function () {
      const res = http.get(`${BASE_URL}/pos/sales`, params);
      check(res, { 'get sales status 200': (r) => r.status === 200 });
    });
  });

  sleep(1); // Esperar 1 segundo entre iteraciones
}
