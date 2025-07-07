/**
 * Sistema de caché del lado del cliente
 */

interface CacheItem {
  data: any;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

interface CacheConfig {
  defaultTTL: number;
  maxSize: number;
  storageKey: string;
}

class ClientCacheManager {
  private cache: Map<string, CacheItem> = new Map();
  private config: CacheConfig;

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = {
      defaultTTL: 5 * 60 * 1000, // 5 minutos por defecto
      maxSize: 100, // Máximo 100 elementos
      storageKey: 'app_cache',
      ...config
    };

    this.loadFromStorage();
    this.startCleanupTimer();
  }

  /**
   * Almacena un elemento en el caché
   */
  set(key: string, data: any, ttl?: number): void {
    const expireTime = ttl || this.config.defaultTTL;
    const item: CacheItem = {
      data,
      timestamp: Date.now(),
      ttl: expireTime
    };

    // Si el caché está lleno, eliminar el elemento más antiguo
    if (this.cache.size >= this.config.maxSize) {
      this.evictOldest();
    }

    this.cache.set(key, item);
    this.saveToStorage();
  }

  /**
   * Obtiene un elemento del caché
   */
  get(key: string): any | null {
    const item = this.cache.get(key);
    
    if (!item) {
      return null;
    }

    // Verificar si el elemento ha expirado
    if (this.isExpired(item)) {
      this.cache.delete(key);
      this.saveToStorage();
      return null;
    }

    return item.data;
  }

  /**
   * Verifica si un elemento existe en el caché y no ha expirado
   */
  has(key: string): boolean {
    const item = this.cache.get(key);
    return item ? !this.isExpired(item) : false;
  }

  /**
   * Elimina un elemento del caché
   */
  delete(key: string): boolean {
    const result = this.cache.delete(key);
    if (result) {
      this.saveToStorage();
    }
    return result;
  }

  /**
   * Elimina elementos que coincidan con un patrón
   */
  deletePattern(pattern: string): number {
    const regex = new RegExp(pattern);
    let deletedCount = 0;

    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
        deletedCount++;
      }
    }

    if (deletedCount > 0) {
      this.saveToStorage();
    }

    return deletedCount;
  }

  /**
   * Limpia todo el caché
   */
  clear(): void {
    this.cache.clear();
    this.saveToStorage();
  }

  /**
   * Obtiene estadísticas del caché
   */
  getStats(): {
    size: number;
    maxSize: number;
    hitRate: number;
    totalRequests: number;
    hits: number;
    misses: number;
  } {
    // Estas estadísticas se podrían mejorar con un tracking más detallado
    return {
      size: this.cache.size,
      maxSize: this.config.maxSize,
      hitRate: 0, // TODO: Implementar tracking de hits/misses
      totalRequests: 0,
      hits: 0,
      misses: 0
    };
  }

  /**
   * Verifica si un elemento ha expirado
   */
  private isExpired(item: CacheItem): boolean {
    return Date.now() - item.timestamp > item.ttl;
  }

  /**
   * Elimina el elemento más antiguo del caché
   */
  private evictOldest(): void {
    let oldestKey: string | null = null;
    let oldestTimestamp = Date.now();

    for (const [key, item] of this.cache.entries()) {
      if (item.timestamp < oldestTimestamp) {
        oldestTimestamp = item.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey);
    }
  }

  /**
   * Limpia elementos expirados
   */
  private cleanup(): void {
    const expiredKeys: string[] = [];

    for (const [key, item] of this.cache.entries()) {
      if (this.isExpired(item)) {
        expiredKeys.push(key);
      }
    }

    if (expiredKeys.length > 0) {
      for (const key of expiredKeys) {
        this.cache.delete(key);
      }
      this.saveToStorage();
    }
  }

  /**
   * Inicia el timer de limpieza periódica
   */
  private startCleanupTimer(): void {
    setInterval(() => {
      this.cleanup();
    }, 60000); // Limpiar cada minuto
  }

  /**
   * Guarda el caché en localStorage
   */
  private saveToStorage(): void {
    try {
      const serializedCache = Array.from(this.cache.entries());
      localStorage.setItem(this.config.storageKey, JSON.stringify(serializedCache));
    } catch (error) {
      console.warn('Error saving cache to localStorage:', error);
    }
  }

  /**
   * Carga el caché desde localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.config.storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        this.cache = new Map(parsed);
        // Limpiar elementos expirados al cargar
        this.cleanup();
      }
    } catch (error) {
      console.warn('Error loading cache from localStorage:', error);
      this.cache.clear();
    }
  }
}

// Configuraciones específicas para diferentes tipos de datos
export const CacheSettings = {
  PRODUCTS: {
    TTL: 2 * 60 * 1000, // 2 minutos
    PREFIX: 'products'
  },
  PRODUCT_SEARCH: {
    TTL: 30 * 1000, // 30 segundos
    PREFIX: 'search'
  },
  USER_SESSION: {
    TTL: 15 * 60 * 1000, // 15 minutos
    PREFIX: 'session'
  },
  STATIC_DATA: {
    TTL: 30 * 60 * 1000, // 30 minutos
    PREFIX: 'static'
  }
};

// Instancia global del caché
export const clientCache = new ClientCacheManager({
  defaultTTL: 5 * 60 * 1000,
  maxSize: 200,
  storageKey: 'tuapp_cache'
});

// Funciones de utilidad para caché específico

export function cacheProductsList(products: any[], skip: number = 0, limit: number = 20): void {
  const key = `${CacheSettings.PRODUCTS.PREFIX}:list:${skip}:${limit}`;
  clientCache.set(key, products, CacheSettings.PRODUCTS.TTL);
}

export function getCachedProductsList(skip: number = 0, limit: number = 20): any[] | null {
  const key = `${CacheSettings.PRODUCTS.PREFIX}:list:${skip}:${limit}`;
  return clientCache.get(key);
}

export function cacheProductSearch(query: string, results: any[]): void {
  const key = `${CacheSettings.PRODUCT_SEARCH.PREFIX}:${query}`;
  clientCache.set(key, results, CacheSettings.PRODUCT_SEARCH.TTL);
}

export function getCachedProductSearch(query: string): any[] | null {
  const key = `${CacheSettings.PRODUCT_SEARCH.PREFIX}:${query}`;
  return clientCache.get(key);
}

export function invalidateProductsCache(): void {
  clientCache.deletePattern(`${CacheSettings.PRODUCTS.PREFIX}:.*`);
  clientCache.deletePattern(`${CacheSettings.PRODUCT_SEARCH.PREFIX}:.*`);
}

export function cacheUserSession(userId: number, sessionData: any): void {
  const key = `${CacheSettings.USER_SESSION.PREFIX}:${userId}`;
  clientCache.set(key, sessionData, CacheSettings.USER_SESSION.TTL);
}

export function getCachedUserSession(userId: number): any | null {
  const key = `${CacheSettings.USER_SESSION.PREFIX}:${userId}`;
  return clientCache.get(key);
}

// Hook para usar caché en React
export function useClientCache() {
  const setCache = (key: string, data: any, ttl?: number) => {
    clientCache.set(key, data, ttl);
  };

  const getCache = (key: string) => {
    return clientCache.get(key);
  };

  const hasCache = (key: string) => {
    return clientCache.has(key);
  };

  const deleteCache = (key: string) => {
    return clientCache.delete(key);
  };

  const clearCache = () => {
    clientCache.clear();
  };

  const getStats = () => {
    return clientCache.getStats();
  };

  return {
    setCache,
    getCache,
    hasCache,
    deleteCache,
    clearCache,
    getStats
  };
}