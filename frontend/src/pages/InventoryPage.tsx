import React, { useState, useEffect } from 'react';
import { Product, ProductListResponse } from '../types';
import Pagination from '../components/Pagination';
import ErrorNotification from '../components/ErrorNotification';
import ProductNameAutocompleteFixed from '../components/ProductNameAutocompleteFixed';
import PageLayout from '../components/PageLayout';
import { useProductsApi } from '../hooks/useApiError';
import { useSkuValidation } from '../hooks/useSkuValidation';

const InventoryPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [productListData, setProductListData] = useState<ProductListResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [newProduct, setNewProduct] = useState<Partial<Product>>({
    sku: '', name: ''
  });
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Usar el hook de API con manejo de errores
  const {
    error,
    isLoading,
    clearError,
    createProduct,
    updateProduct,
    getProducts
  } = useProductsApi();

  // Hook para validación de SKU en tiempo real
  const skuValidation = useSkuValidation();
  const editSkuValidation = useSkuValidation(editingProduct?.id);

  useEffect(() => {
    fetchProducts();
  }, [currentPage]);

  const fetchProducts = async () => {
    const skip = (currentPage - 1) * itemsPerPage;
    const data = await getProducts(skip, itemsPerPage);
    
    if (data) {
      if (Array.isArray(data)) {
        setProducts(data);
        setProductListData({ products: data, total: data.length, skip: skip, limit: itemsPerPage, has_next: false });
      } else {
        setProductListData(data);
        setProducts(data.products);
      }
    }
  };

  const handleSkuChange = (sku: string) => {
    setNewProduct({ ...newProduct, sku });
    skuValidation.validateSku(sku);
  };

  const handleEditSkuChange = (sku: string) => {
    if (editingProduct) {
      setEditingProduct({ ...editingProduct, sku });
      editSkuValidation.validateSku(sku);
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(null);
    
    // Verificar que el SKU esté disponible antes de crear
    if (skuValidation.isAvailable === false) {
      return; // No permitir crear si el SKU no está disponible
    }
    
    await createProduct(newProduct as Product, () => {
      setSuccess("Producto creado con éxito.");
      setNewProduct({ sku: '', name: '' });
      skuValidation.clearValidation();
      
      // Volver a la primera página después de crear
      if (currentPage !== 1) {
        setCurrentPage(1);
      } else {
        fetchProducts();
      }
    });
  };

  const handleUpdateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(null);
    
    if (!editingProduct) return;
    
    // Verificar que el SKU esté disponible antes de actualizar
    if (editSkuValidation.isAvailable === false) {
      return; // No permitir actualizar si el SKU no está disponible
    }
    
    await updateProduct(editingProduct.id, editingProduct, () => {
      setSuccess("Producto actualizado con éxito.");
      setEditingProduct(null);
      editSkuValidation.clearValidation();
      fetchProducts();
    });
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setEditingProduct(null); // Cerrar edición al cambiar página
    editSkuValidation.clearValidation(); // Limpiar validación al cambiar página
  };

  const totalPages = productListData ? Math.ceil(productListData.total / itemsPerPage) : 1;

  return (
    <PageLayout 
      title="Gestión de Inventario" 
      subtitle="Administra tu inventario con validación SKU en tiempo real"
    >
      
      {/* Notificación de error */}
      <ErrorNotification 
        error={error} 
        onClose={clearError} 
      />
      
      {/* Mensaje de éxito */}
      {success && (
        <div className="alert alert-success">
          ✅ {success}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>Crear Nuevo Producto</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleCreateProduct} className="form-grid">
        <div style={{ position: 'relative' }}>
          <input 
            type="text" 
            placeholder="SKU (ej: CASE001)" 
            value={newProduct.sku} 
            onChange={e => handleSkuChange(e.target.value)}
            className={`input ${
              skuValidation.isValidating ? 'input-warning' : 
              skuValidation.isAvailable === false ? 'input-error' : 
              skuValidation.isAvailable === true ? 'input-success' : ''
            }`}
            required 
          />
          {skuValidation.isValidating && (
            <small style={{ color: '#ffc107', display: 'block', marginTop: '2px' }}>
              🔍 Verificando SKU...
            </small>
          )}
          {skuValidation.isAvailable === false && (
            <small style={{ color: '#dc3545', display: 'block', marginTop: '2px' }}>
              ❌ {skuValidation.message}
            </small>
          )}
          {skuValidation.isAvailable === true && (
            <small style={{ color: '#28a745', display: 'block', marginTop: '2px' }}>
              ✅ {skuValidation.message}
            </small>
          )}
          {skuValidation.error && (
            <small style={{ color: '#dc3545', display: 'block', marginTop: '2px' }}>
              ⚠️ {skuValidation.error}
            </small>
          )}
        </div>
        <ProductNameAutocompleteFixed
          value={newProduct.name || ''}
          onChange={(name) => {
            setNewProduct({ ...newProduct, name });
          }}
          placeholder="Nombre del Producto (ej: Funda iPhone 14)"
          required
        />
        <input className="input" type="number" placeholder="Precio Costo en COP (ej: 15000)" value={newProduct.cost_price || ''} onChange={e => setNewProduct({ ...newProduct, cost_price: e.target.value ? parseFloat(e.target.value) : 0 })} required />
        <input className="input" type="number" placeholder="Precio Venta en COP (ej: 25000)" value={newProduct.selling_price || ''} onChange={e => setNewProduct({ ...newProduct, selling_price: e.target.value ? parseFloat(e.target.value) : 0 })} required />
        <input className="input" type="number" placeholder="Cantidad en Stock (ej: 50)" value={newProduct.stock_quantity || ''} onChange={e => setNewProduct({ ...newProduct, stock_quantity: e.target.value ? parseInt(e.target.value) : 0 })} required />
        <div className="form-grid-full">
          <button 
            type="submit" 
            disabled={isLoading || skuValidation.isAvailable === false || skuValidation.isValidating}
            className={`btn mobile-full ${skuValidation.isAvailable === false ? 'btn-ghost' : 'btn-primary'}`}
          >
            {isLoading ? 'Creando...' : 
             skuValidation.isAvailable === false ? 'SKU no disponible' :
             'Crear Producto'}
          </button>
        </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Lista de Productos</h2>
          {productListData && (
            <div style={{ fontSize: '14px', color: 'var(--text-tertiary)' }}>
              Mostrando {products.length} de {productListData.total} productos
            </div>
          )}
        </div>
        <div className="card-body">
          {isLoading && (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div className="spinner"></div>
              <p>Cargando productos...</p>
            </div>
          )}
          
          <div className="table-responsive">
            <table className="table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Nombre</th>
            <th style={{ textAlign: 'right' }}>Costo (COP)</th>
            <th style={{ textAlign: 'right' }}>Venta (COP)</th>
            <th style={{ textAlign: 'right' }}>Stock</th>
            <th style={{ textAlign: 'right' }}>Valor Stock (COP)</th>
            <th style={{ textAlign: 'center' }}>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {products.map(product => (
            <tr key={product.id} style={{ 
              backgroundColor: product.stock_quantity === 0 ? 'rgba(245, 158, 11, 0.1)' : 'transparent' 
            }}>
              <td>{product.sku}</td>
              <td>
                {product.name}
                {product.stock_quantity === 0 && (
                  <span className="badge badge-warning" style={{ marginLeft: '8px' }}>
                    Sin stock
                  </span>
                )}
              </td>
              <td style={{ textAlign: 'right' }}>
                ${product.cost_price.toLocaleString('es-CO')}
              </td>
              <td style={{ textAlign: 'right' }}>
                ${product.selling_price.toLocaleString('es-CO')}
              </td>
              <td style={{ textAlign: 'right' }}>
                {product.stock_quantity}
              </td>
              <td style={{ textAlign: 'right' }}>
                ${(product.stock_quantity * product.cost_price).toLocaleString('es-CO')}
              </td>
              <td style={{ textAlign: 'center' }}>
                <button 
                  onClick={() => setEditingProduct(product)}
                  className="btn btn-secondary btn-sm"
                  disabled={isLoading}
                >
                  Editar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Componente de paginación */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
        disabled={isLoading}
      />

      {editingProduct && (
        <div className="card fade-in">
          <div className="card-header">
            <h2>Editar Producto: {editingProduct.name}</h2>
          </div>
          <div className="card-body">
            <form onSubmit={handleUpdateProduct} className="form-grid">
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                placeholder="SKU (ej: CASE001)" 
                value={editingProduct.sku} 
                onChange={e => handleEditSkuChange(e.target.value)}
                className={`input ${
                  editSkuValidation.isValidating ? 'input-warning' : 
                  editSkuValidation.isAvailable === false ? 'input-error' : 
                  editSkuValidation.isAvailable === true ? 'input-success' : ''
                }`}
                required 
              />
              {editSkuValidation.isValidating && (
                <small style={{ color: '#ffc107', display: 'block', marginTop: '2px' }}>
                  🔍 Verificando SKU...
                </small>
              )}
              {editSkuValidation.isAvailable === false && (
                <small style={{ color: '#dc3545', display: 'block', marginTop: '2px' }}>
                  ❌ {editSkuValidation.message}
                </small>
              )}
              {editSkuValidation.isAvailable === true && (
                <small style={{ color: '#28a745', display: 'block', marginTop: '2px' }}>
                  ✅ {editSkuValidation.message}
                </small>
              )}
              {editSkuValidation.error && (
                <small style={{ color: '#dc3545', display: 'block', marginTop: '2px' }}>
                  ⚠️ {editSkuValidation.error}
                </small>
              )}
            </div>
            <ProductNameAutocompleteFixed
              value={editingProduct.name}
              onChange={(name) => setEditingProduct({ ...editingProduct, name })}
              placeholder="Nombre del Producto (ej: Funda iPhone 14)"
              required
            />
            <input 
              className="input"
              type="number" 
              step="0.01"
              placeholder="Precio Costo en COP (ej: 15000)" 
              value={editingProduct.cost_price} 
              onChange={e => setEditingProduct({ ...editingProduct, cost_price: parseFloat(e.target.value) })} 
              required 
            />
            <input 
              className="input"
              type="number" 
              step="0.01"
              placeholder="Precio Venta en COP (ej: 25000)" 
              value={editingProduct.selling_price} 
              onChange={e => setEditingProduct({ ...editingProduct, selling_price: parseFloat(e.target.value) })} 
              required 
            />
            <input 
              className="input"
              type="number" 
              placeholder="Cantidad en Stock (ej: 50)" 
              value={editingProduct.stock_quantity} 
              onChange={e => setEditingProduct({ ...editingProduct, stock_quantity: parseInt(e.target.value) })} 
              required 
            />
            <div className="form-grid-full">
              <div className="flex-mobile">
                <button 
                  type="submit" 
                  disabled={isLoading || editSkuValidation.isAvailable === false || editSkuValidation.isValidating}
                  className={`btn mobile-full ${editSkuValidation.isAvailable === false ? 'btn-ghost' : 'btn-success'}`}
                >
                  {isLoading ? 'Guardando...' : 
                   editSkuValidation.isAvailable === false ? 'SKU no disponible' :
                   'Guardar Cambios'}
                </button>
                <button 
                  type="button" 
                  onClick={() => {
                    setEditingProduct(null);
                    editSkuValidation.clearValidation();
                  }}
                  className="btn btn-secondary mobile-full"
                >
                  Cancelar
                </button>
              </div>
            </div>
            </form>
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default InventoryPage;