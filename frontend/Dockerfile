# Usar imagen más reciente de Node.js
FROM node:20-alpine

# Variables de entorno para optimización
ENV NODE_ENV=development \
    CHOKIDAR_USEPOLLING=true

# Instalar dumb-init para manejo seguro de señales
RUN apk add --no-cache dumb-init

# Crear usuario no-root para seguridad
RUN addgroup -g 1001 -S nodejs \
    && adduser -S reactjs -u 1001

WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias (incluyendo dev para compilación)
RUN npm ci && npm cache clean --force

# Copiar código fuente
COPY . .

# Cambiar ownership al usuario no-root
RUN chown -R reactjs:nodejs /app

# Cambiar a usuario no-root
USER reactjs

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Usar dumb-init para manejo correcto de señales
ENTRYPOINT ["dumb-init", "--"]

# Comando optimizado
CMD ["npm", "start"]
