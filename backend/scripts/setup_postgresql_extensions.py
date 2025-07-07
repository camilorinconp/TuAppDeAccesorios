#!/usr/bin/env python3
# ==================================================================
# SCRIPT DE CONFIGURACIÓN POSTGRESQL - EXTENSIONES FULL-TEXT
# ==================================================================

"""
Script para configurar extensiones de PostgreSQL necesarias para
búsqueda full-text avanzada
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def setup_postgresql_extensions():
    """Configura las extensiones necesarias de PostgreSQL"""
    
    try:
        # Crear conexión a PostgreSQL
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            logger.info("Configurando extensiones de PostgreSQL...")
            
            # Verificar si es PostgreSQL
            result = conn.execute(text("SELECT version()")).fetchone()
            if not result or 'PostgreSQL' not in str(result[0]):
                logger.warning("La base de datos no es PostgreSQL, saltando configuración de extensiones")
                return False
            
            logger.info(f"Detectado PostgreSQL: {result[0]}")
            
            # Lista de extensiones requeridas
            extensions = [
                ('pg_trgm', 'Búsqueda por similitud y trigrams'),
                ('unaccent', 'Normalización de acentos'),
                ('fuzzystrmatch', 'Búsqueda difusa de cadenas')
            ]
            
            # Instalar cada extensión
            for ext_name, description in extensions:
                try:
                    # Verificar si la extensión ya existe
                    check_query = text("""
                        SELECT EXISTS(
                            SELECT 1 FROM pg_extension 
                            WHERE extname = :ext_name
                        )
                    """)
                    
                    exists = conn.execute(check_query, {"ext_name": ext_name}).fetchone()[0]
                    
                    if exists:
                        logger.info(f"✅ Extensión '{ext_name}' ya está instalada")
                    else:
                        # Instalar extensión
                        install_query = text(f"CREATE EXTENSION IF NOT EXISTS {ext_name}")
                        conn.execute(install_query)
                        conn.commit()
                        logger.info(f"✅ Extensión '{ext_name}' instalada exitosamente ({description})")
                        
                except Exception as e:
                    logger.error(f"❌ Error instalando extensión '{ext_name}': {str(e)}")
                    continue
            
            # Crear índices full-text optimizados
            create_fulltext_indexes(conn)
            
            # Crear funciones auxiliares
            create_helper_functions(conn)
            
            logger.info("✅ Configuración de PostgreSQL completada exitosamente")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error configurando PostgreSQL: {str(e)}")
        return False


def create_fulltext_indexes(conn):
    """Crea índices optimizados para búsqueda full-text"""
    
    try:
        logger.info("Creando índices full-text...")
        
        # Índices para búsqueda full-text en español
        indexes = [
            {
                'name': 'idx_products_fulltext_spanish',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_products_fulltext_spanish 
                    ON products USING gin(
                        to_tsvector('spanish', 
                            COALESCE(name, '') || ' ' || 
                            COALESCE(sku, '') || ' ' || 
                            COALESCE(description, '')
                        )
                    )
                """,
                'description': 'Índice full-text en español para productos'
            },
            {
                'name': 'idx_products_trigram_name',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_products_trigram_name 
                    ON products USING gin(name gin_trgm_ops)
                """,
                'description': 'Índice de trigramas para nombres de productos'
            },
            {
                'name': 'idx_products_trigram_sku',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_products_trigram_sku 
                    ON products USING gin(sku gin_trgm_ops)
                """,
                'description': 'Índice de trigramas para SKUs de productos'
            },
            {
                'name': 'idx_products_similarity_name',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_products_similarity_name 
                    ON products USING gist(name gist_trgm_ops)
                """,
                'description': 'Índice de similitud para nombres de productos'
            }
        ]
        
        for index in indexes:
            try:
                conn.execute(text(index['query']))
                conn.commit()
                logger.info(f"✅ Índice '{index['name']}' creado ({index['description']})")
            except Exception as e:
                logger.warning(f"⚠️  Índice '{index['name']}' no pudo crearse: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"❌ Error creando índices full-text: {str(e)}")


def create_helper_functions(conn):
    """Crea funciones auxiliares para búsqueda"""
    
    try:
        logger.info("Creando funciones auxiliares...")
        
        # Función para normalizar texto de búsqueda
        normalize_function = text("""
            CREATE OR REPLACE FUNCTION normalize_search_text(input_text TEXT)
            RETURNS TEXT AS $$
            BEGIN
                -- Convertir a minúsculas y remover acentos
                RETURN lower(unaccent(input_text));
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)
        
        # Función para búsqueda inteligente de productos
        smart_search_function = text("""
            CREATE OR REPLACE FUNCTION smart_product_search(
                search_query TEXT,
                result_limit INTEGER DEFAULT 10
            )
            RETURNS TABLE(
                product_id INTEGER,
                name TEXT,
                sku TEXT,
                description TEXT,
                relevance_score REAL
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    p.id,
                    p.name,
                    p.sku,
                    p.description,
                    (
                        ts_rank_cd(
                            to_tsvector('spanish', 
                                COALESCE(p.name, '') || ' ' || 
                                COALESCE(p.sku, '') || ' ' || 
                                COALESCE(p.description, '')
                            ), 
                            plainto_tsquery('spanish', search_query)
                        ) * 0.5 +
                        similarity(p.name, search_query) * 0.3 +
                        similarity(p.sku, search_query) * 0.2
                    ) AS relevance_score
                FROM products p
                WHERE (
                    to_tsvector('spanish', 
                        COALESCE(p.name, '') || ' ' || 
                        COALESCE(p.sku, '') || ' ' || 
                        COALESCE(p.description, '')
                    ) @@ plainto_tsquery('spanish', search_query)
                    OR similarity(p.name, search_query) > 0.3
                    OR similarity(p.sku, search_query) > 0.4
                    OR p.name ILIKE '%' || search_query || '%'
                    OR p.sku ILIKE '%' || search_query || '%'
                )
                ORDER BY relevance_score DESC, p.name ASC
                LIMIT result_limit;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        functions = [
            (normalize_function, "normalize_search_text", "Función de normalización de texto"),
            (smart_search_function, "smart_product_search", "Función de búsqueda inteligente")
        ]
        
        for func_query, func_name, description in functions:
            try:
                conn.execute(func_query)
                conn.commit()
                logger.info(f"✅ Función '{func_name}' creada ({description})")
            except Exception as e:
                logger.warning(f"⚠️  Función '{func_name}' no pudo crearse: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"❌ Error creando funciones auxiliares: {str(e)}")


def verify_setup():
    """Verifica que la configuración se haya completado correctamente"""
    
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            logger.info("Verificando configuración...")
            
            # Verificar extensiones
            extensions_query = text("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('pg_trgm', 'unaccent', 'fuzzystrmatch')
                ORDER BY extname
            """)
            
            extensions = conn.execute(extensions_query).fetchall()
            logger.info(f"Extensiones instaladas: {[ext[0] for ext in extensions]}")
            
            # Verificar índices
            indexes_query = text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'products' 
                AND indexname LIKE 'idx_products_%'
                ORDER BY indexname
            """)
            
            indexes = conn.execute(indexes_query).fetchall()
            logger.info(f"Índices creados: {[idx[0] for idx in indexes]}")
            
            # Verificar funciones
            functions_query = text("""
                SELECT proname FROM pg_proc 
                WHERE proname IN ('normalize_search_text', 'smart_product_search')
                ORDER BY proname
            """)
            
            functions = conn.execute(functions_query).fetchall()
            logger.info(f"Funciones creadas: {[func[0] for func in functions]}")
            
            # Probar búsqueda
            test_search_query = text("""
                SELECT COUNT(*) FROM smart_product_search('test', 5)
            """)
            
            try:
                result = conn.execute(test_search_query).fetchone()
                logger.info(f"✅ Prueba de función de búsqueda exitosa")
            except Exception as e:
                logger.warning(f"⚠️  Prueba de función de búsqueda falló: {str(e)}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error verificando configuración: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Configurar extensiones PostgreSQL para full-text search")
    parser.add_argument("--verify-only", action="store_true", help="Solo verificar configuración existente")
    
    args = parser.parse_args()
    
    if args.verify_only:
        logger.info("🔍 Verificando configuración existente...")
        success = verify_setup()
    else:
        logger.info("🚀 Iniciando configuración de PostgreSQL...")
        success = setup_postgresql_extensions()
        if success:
            verify_setup()
    
    if success:
        logger.info("✅ Proceso completado exitosamente")
        sys.exit(0)
    else:
        logger.error("❌ Proceso completado con errores")
        sys.exit(1)