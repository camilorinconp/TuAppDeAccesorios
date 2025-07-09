#!/usr/bin/env python3
"""
Script para aplicar optimizaciones de base de datos y verificar configuración
"""
import os
import sys
import psycopg2
from sqlalchemy import create_engine, text
from pathlib import Path

# Agregar el directorio backend al path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.app.config import settings
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

def apply_database_indexes():
    """Aplica los índices optimizados a la base de datos"""
    
    try:
        # Crear engine de base de datos
        engine = create_engine(settings.database_url)
        
        # Leer script de índices
        indexes_file = Path(__file__).parent / "database" / "create_indexes.sql"
        
        if not indexes_file.exists():
            logger.error(f"Archivo de índices no encontrado: {indexes_file}")
            return False
        
        with open(indexes_file, 'r', encoding='utf-8') as f:
            indexes_sql = f.read()
        
        # Ejecutar script de índices
        with engine.connect() as conn:
            logger.info("Aplicando índices optimizados...")
            
            # Dividir por declaraciones individuales
            statements = [stmt.strip() for stmt in indexes_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement.upper().startswith(('CREATE INDEX', 'ANALYZE')):
                    try:
                        conn.execute(text(statement))
                        logger.info(f"Ejecutado: {statement[:50]}...")
                    except Exception as e:
                        if "already exists" in str(e):
                            logger.info(f"Índice ya existe: {statement[:50]}...")
                        else:
                            logger.warning(f"Error ejecutando: {statement[:50]}... - {e}")
            
            conn.commit()
            logger.info("✅ Índices aplicados exitosamente")
            return True
            
    except Exception as e:
        logger.error(f"Error aplicando índices: {e}")
        return False

def verify_optimizations():
    """Verifica que las optimizaciones estén funcionando"""
    
    checks = []
    
    # Verificar conexión a Redis
    try:
        from backend.app.cache import cache_manager
        client = cache_manager.get_sync_client()
        client.ping()
        checks.append("✅ Conexión Redis: OK")
    except Exception as e:
        checks.append(f"❌ Conexión Redis: {e}")
    
    # Verificar rate limiting
    try:
        from backend.app.rate_limiter import rate_limiter
        if rate_limiter.enabled:
            checks.append("✅ Rate Limiting: Habilitado")
        else:
            checks.append("⚠️ Rate Limiting: Deshabilitado")
    except Exception as e:
        checks.append(f"❌ Rate Limiting: {e}")
    
    # Verificar configuración de base de datos
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            table_count = result.scalar()
            checks.append(f"✅ Base de datos: {table_count} tablas encontradas")
    except Exception as e:
        checks.append(f"❌ Base de datos: {e}")
    
    # Verificar índices
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'idx_%'
            """))
            index_count = result.scalar()
            checks.append(f"✅ Índices personalizados: {index_count} encontrados")
    except Exception as e:
        checks.append(f"❌ Índices: {e}")
    
    return checks

def main():
    """Función principal"""
    
    print("🚀 Aplicando optimizaciones de TuAppDeAccesorios...")
    print("=" * 60)
    
    # Solo aplicar índices si es PostgreSQL
    if "postgresql" in settings.database_url:
        print("\n📊 Aplicando índices de base de datos...")
        if apply_database_indexes():
            print("✅ Índices aplicados exitosamente")
        else:
            print("❌ Error aplicando índices")
    else:
        print("⚠️ Base de datos no es PostgreSQL, omitiendo índices")
    
    print("\n🔍 Verificando optimizaciones...")
    checks = verify_optimizations()
    
    for check in checks:
        print(f"  {check}")
    
    print("\n" + "=" * 60)
    print("🎯 Optimizaciones completadas")
    
    print("\n📝 Próximos pasos para producción:")
    print("  1. Configurar variables de entorno en Render (ver RENDER_SETUP.md)")
    print("  2. Verificar CORS_ORIGINS con tu dominio real")
    print("  3. Habilitar monitoreo y alertas")
    print("  4. Configurar backups automáticos")

if __name__ == "__main__":
    main()