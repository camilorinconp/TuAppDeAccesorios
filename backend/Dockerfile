# Multi-stage Dockerfile para optimizar builds de producción y testing

# Stage base con dependencias comunes
FROM python:3.11-slim as base

# Metadatos
LABEL maintainer="TuAppDeAccesorios Team"
LABEL version="1.0"
LABEL description="Backend API para TuAppDeAccesorios"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario no-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

WORKDIR /app

# Stage para dependencias
FROM base as dependencies

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage para desarrollo
FROM dependencies as development

# Instalar dependencias adicionales para desarrollo
RUN pip install pytest pytest-cov pytest-asyncio httpx black flake8 bandit safety

# Copiar código fuente
COPY . .

# Cambiar propietario
RUN chown -R appuser:appuser /app

USER appuser

# Comando por defecto para desarrollo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage para testing
FROM development as test

# Instalar dependencias adicionales para testing
RUN pip install coverage pytest-html pytest-json-report locust

# Configurar variables de entorno para testing
ENV ENVIRONMENT=testing \
    DATABASE_URL=sqlite:///./test.db \
    SECRET_KEY=test-secret-key \
    REDIS_CACHE_ENABLED=false

# Copiar configuración de tests
COPY tests/ tests/
COPY conftest.py .

# Comando para ejecutar tests
CMD ["pytest", "tests/", "-v", "--cov=app", "--cov-report=html", "--cov-report=term-missing"]

# Stage para producción
FROM base as production

# Instalar solo dependencias de producción
COPY --from=dependencies /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=dependencies /usr/local/bin/ /usr/local/bin/

# Instalar gunicorn para producción
RUN pip install gunicorn

# Copiar código fuente
COPY --chown=appuser:appuser . .

# Configurar variables de entorno para producción
ENV ENVIRONMENT=production \
    PYTHONPATH=/app

# Crear script de healthcheck
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /usr/local/bin/healthcheck && \
    chmod +x /usr/local/bin/healthcheck

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/local/bin/healthcheck"]

# Comando por defecto para producción
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--access-logfile", "-", "--error-logfile", "-"]
