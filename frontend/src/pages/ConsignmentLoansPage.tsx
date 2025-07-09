import React, { useState, useEffect, useCallback } from 'react';
import { ConsignmentLoan, Product, Distributor } from '../types';
import ErrorNotification from '../components/ErrorNotification';
import { useApiError } from '../hooks/useApiError';
import { apiRequest } from '../services/api';

// Estilos modernos
const modernStyles = {
  container: {
    padding: '24px',
    backgroundColor: '#f8fafc',
    minHeight: '100vh',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '32px',
    padding: '0 8px'
  },
  title: {
    fontSize: '2rem',
    fontWeight: '700',
    color: '#1e293b',
    margin: 0,
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  createButton: {
    padding: '12px 24px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  createButtonHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 6px 20px rgba(102, 126, 234, 0.6)'
  },
  formContainer: {
    marginBottom: '32px',
    background: 'white',
    padding: '32px',
    borderRadius: '16px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
    border: '1px solid #e2e8f0'
  },
  formTitle: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '20px'
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px'
  },
  label: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '4px'
  },
  input: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    transition: 'all 0.2s ease',
    backgroundColor: 'white'
  },
  inputFocus: {
    borderColor: '#667eea',
    outline: 'none',
    boxShadow: '0 0 0 3px rgba(102, 126, 234, 0.1)'
  },
  select: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    backgroundColor: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s ease'
  },
  helpText: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '4px'
  },
  submitButton: {
    padding: '12px 24px',
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    gridColumn: '1 / -1',
    justifySelf: 'flex-end',
    width: 'fit-content'
  },
  cancelButton: {
    padding: '12px 24px',
    background: '#6b7280',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    marginRight: '12px'
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
    border: '1px solid #e2e8f0'
  },
  summaryCard: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    padding: '24px',
    borderRadius: '16px',
    marginTop: '20px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    backgroundColor: 'white',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
  },
  tableHeader: {
    backgroundColor: '#f8fafc',
    borderBottom: '1px solid #e2e8f0'
  },
  tableHeaderCell: {
    padding: '16px',
    textAlign: 'left',
    fontWeight: '600',
    color: '#374151',
    fontSize: '14px'
  },
  tableCell: {
    padding: '16px',
    borderBottom: '1px solid #f1f5f9',
    fontSize: '14px',
    color: '#4b5563'
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px'
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
    marginTop: '32px'
  },
  statCard: {
    padding: '20px',
    borderRadius: '12px',
    textAlign: 'center' as const,
    position: 'relative' as const,
    overflow: 'hidden'
  },
  statNumber: {
    fontSize: '2rem',
    fontWeight: '700',
    margin: '8px 0'
  },
  statLabel: {
    fontSize: '14px',
    fontWeight: '600',
    margin: 0
  },
  distributorSection: {
    marginTop: '32px',
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
  },
  distributorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '16px',
    marginTop: '20px'
  },
  distributorCard: {
    padding: '20px',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    backgroundColor: '#f8fafc',
    transition: 'all 0.2s ease'
  },
  distributorCardHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
  }
};

const ConsignmentLoansPage: React.FC = () => {
  const [loans, setLoans] = useState<ConsignmentLoan[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [distributors, setDistributors] = useState<Distributor[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newLoan, setNewLoan] = useState({
    distributor_id: '',
    product_id: '',
    quantity_loaned: '',
    loan_date: new Date().toISOString().split('T')[0],
    return_due_date: new Date().toISOString().split('T')[0], // Fecha por defecto: hoy
    status: 'en_prestamo'
  });
  const [showDistributorForm, setShowDistributorForm] = useState(false);
  const [newDistributor, setNewDistributor] = useState({
    name: '',
    contact_person: '',
    phone_number: '',
    access_code: ''
  });
  const [success, setSuccess] = useState<string | null>(null);
  const [isFetchingData, setIsFetchingData] = useState(false);
  
  const { error, isLoading, clearError, executeWithErrorHandling } = useApiError();

  const fetchData = useCallback(async () => {
    if (isFetchingData) {
      console.log('Fetch already in progress, skipping...');
      return;
    }
    
    setIsFetchingData(true);
    
    try {
      // Hacer peticiones en paralelo para mejor rendimiento
      const [distributorsResponse, productsResponse, loansResponse] = await Promise.all([
        apiRequest<Distributor[]>('/distributors/'),
        apiRequest<{items: Product[]}>('/products/?page=1&per_page=100&in_stock=true').catch(() => 
          apiRequest<{items: Product[]}>('/products/?page=1&per_page=100')
        ),
        apiRequest<ConsignmentLoan[]>('/consignments/loans?skip=0&limit=100')
      ]);
      
      console.log('Distributors loaded:', distributorsResponse?.length || 0);
      console.log('Products loaded:', productsResponse?.items?.length || 0);
      console.log('Loans loaded:', loansResponse?.length || 0);
      
      setDistributors(distributorsResponse || []);
      setProducts(productsResponse?.items || []);
      setLoans(loansResponse || []);
      
    } catch (error) {
      console.error('Error fetching data:', error);
      // Mostrar error más específico
      if (error instanceof Error) {
        console.error('Error details:', error.message);
      }
    } finally {
      setIsFetchingData(false);
    }
  }, [isFetchingData]);

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateLoan = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(null);
    
    const selectedProduct = products.find(p => p.id === parseInt(newLoan.product_id));
    const requestedQuantity = parseInt(newLoan.quantity_loaned);
    
    if (!selectedProduct) {
      clearError();
      return;
    }
    
    if (requestedQuantity > selectedProduct.stock_quantity) {
      alert(`Error: Stock insuficiente. Disponible: ${selectedProduct.stock_quantity}, Solicitado: ${requestedQuantity}`);
      return;
    }

    await executeWithErrorHandling(async () => {
      // Calcular fecha de vencimiento si no se especifica (30 días por defecto)
      const returnDate = newLoan.return_due_date || 
        new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const loanData = {
        distributor_id: parseInt(newLoan.distributor_id),
        product_id: parseInt(newLoan.product_id),
        quantity_loaned: requestedQuantity,
        loan_date: newLoan.loan_date,
        return_due_date: returnDate,
        status: newLoan.status
      };
      
      await apiRequest('/consignments/loans', {
        method: 'POST',
        body: JSON.stringify(loanData)
      });
      
      setSuccess(`Préstamo creado exitosamente. Stock actualizado automáticamente.`);
      setNewLoan({
        distributor_id: '',
        product_id: '',
        quantity_loaned: '',
        loan_date: new Date().toISOString().split('T')[0],
        return_due_date: new Date().toISOString().split('T')[0], // Resetear con fecha actual
        status: 'en_prestamo'
      });
      setShowCreateForm(false);
      // Refrescar datos de forma controlada
      setTimeout(() => {
        fetchData();
      }, 500);
    });
  };

  const getProductInfo = (productId: number) => {
    return products.find(p => p.id === productId);
  };

  const getDistributorInfo = (distributorId: number) => {
    return distributors.find(d => d.id === distributorId);
  };

  const calculateDaysUntilDue = (dueDate: string) => {
    const today = new Date();
    const due = new Date(dueDate);
    const diffTime = due.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'en_prestamo': return '#007bff';
      case 'devuelto': return '#28a745';
      case 'vencido': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const selectedProduct = products.find(p => p.id === parseInt(newLoan.product_id));

  const handleCreateDistributor = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await executeWithErrorHandling(async () => {
      // Generar código de acceso si no se proporciona
      const accessCode = newDistributor.access_code || 
        `DIST${String(Date.now()).slice(-4)}`;
      
      const distributorData = {
        ...newDistributor,
        access_code: accessCode
      };
      
      await apiRequest('/distributors/', {
        method: 'POST',
        body: JSON.stringify(distributorData)
      });
      
      setSuccess('Distribuidor creado exitosamente');
      setNewDistributor({
        name: '',
        contact_person: '',
        phone_number: '',
        access_code: ''
      });
      setShowDistributorForm(false);
      // Refrescar datos de forma controlada
      setTimeout(() => {
        fetchData();
      }, 500);
    });
  };

  return (
    <div style={modernStyles.container}>
      <div style={modernStyles.header}>
        <h1 style={modernStyles.title}>
          🏪 Gestión en Consignación
        </h1>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            onClick={() => setShowDistributorForm(!showDistributorForm)}
            style={{
              ...modernStyles.createButton,
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(245, 158, 11, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.4)';
            }}
          >
            👥 {showDistributorForm ? 'Cancelar' : 'Gestionar Distribuidores'}
          </button>
          <button 
            onClick={() => setShowCreateForm(!showCreateForm)}
            style={modernStyles.createButton}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
            }}
          >
            ➕ {showCreateForm ? 'Cancelar' : 'Crear Préstamo'}
          </button>
          <button 
            onClick={() => fetchData()}
            disabled={isFetchingData}
            style={{
              ...modernStyles.createButton,
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)',
              opacity: isFetchingData ? 0.6 : 1
            }}
            onMouseEnter={(e) => {
              if (!isFetchingData) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(16, 185, 129, 0.6)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isFetchingData) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.4)';
              }
            }}
          >
            {isFetchingData ? '🔄 Cargando...' : '🔄 Actualizar Datos'}
          </button>
        </div>
      </div>
      
      {/* Notificación de error */}
      <ErrorNotification error={error} onClose={clearError} />
      
      {/* Mensaje de éxito */}
      {success && (
        <div style={{ 
          padding: '16px', 
          backgroundColor: '#d1fae5', 
          border: '1px solid #a7f3d0', 
          borderRadius: '12px', 
          color: '#065f46',
          marginBottom: '24px',
          fontSize: '14px',
          fontWeight: '500'
        }}>
          ✅ {success}
        </div>
      )}

      {/* Formulario de creación */}
      {showCreateForm && (
        <div style={modernStyles.formContainer}>
          <h2 style={modernStyles.formTitle}>📝 Crear Nuevo Préstamo</h2>
          <form onSubmit={handleCreateLoan} style={modernStyles.formGrid}>
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>
                Distribuidor:
              </label>
              <select 
                value={newLoan.distributor_id} 
                onChange={e => setNewLoan({...newLoan, distributor_id: e.target.value})}
                required
                style={modernStyles.select}
              >
                <option value="">Seleccionar distribuidor...</option>
                {distributors.map(dist => (
                  <option key={dist.id} value={dist.id}>
                    {dist.name} (Código: {dist.access_code})
                  </option>
                ))}
              </select>
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>
                Producto:
              </label>
              <select 
                value={newLoan.product_id} 
                onChange={e => setNewLoan({...newLoan, product_id: e.target.value})}
                required
                style={modernStyles.select}
                disabled={products.length === 0}
              >
                <option value="">
                  {products.length === 0 ? 'Cargando productos...' : 'Seleccionar producto...'}
                </option>
                {products.filter(product => product.stock_quantity > 0).map(product => (
                  <option key={product.id} value={product.id}>
                    {product.name} - Stock: {product.stock_quantity} (${product.selling_price.toLocaleString('es-CO')})
                  </option>
                ))}
              </select>
              {products.length === 0 && !isFetchingData && (
                <small style={{...modernStyles.helpText, color: '#ef4444'}}>
                  No se pudieron cargar los productos. Por favor, recarga la página.
                </small>
              )}
              {products.length > 0 && products.filter(p => p.stock_quantity > 0).length === 0 && (
                <small style={{...modernStyles.helpText, color: '#ef4444'}}>
                  No hay productos con stock disponible para préstamo.
                </small>
              )}
              {isFetchingData && (
                <small style={{...modernStyles.helpText, color: '#667eea'}}>
                  Cargando productos disponibles...
                </small>
              )}
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>
                Cantidad a Prestar:
              </label>
              <input 
                type="number" 
                value={newLoan.quantity_loaned} 
                onChange={e => setNewLoan({...newLoan, quantity_loaned: e.target.value})}
                min="1"
                max={selectedProduct?.stock_quantity || 999}
                required
                style={modernStyles.input}
              />
              {selectedProduct && (
                <small style={modernStyles.helpText}>
                  Stock disponible: {selectedProduct.stock_quantity} unidades
                </small>
              )}
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>
                Fecha de Préstamo:
              </label>
              <input 
                type="date" 
                value={newLoan.loan_date} 
                onChange={e => setNewLoan({...newLoan, loan_date: e.target.value})}
                required
                style={modernStyles.input}
              />
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>
                Fecha de Vencimiento:
              </label>
              <input 
                type="date" 
                value={newLoan.return_due_date} 
                onChange={e => setNewLoan({...newLoan, return_due_date: e.target.value})}
                style={modernStyles.input}
              />
              <small style={modernStyles.helpText}>
                Opcional: 30 días por defecto desde la fecha de préstamo
              </small>
            </div>
            
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button 
                type="button" 
                onClick={() => setShowCreateForm(false)}
                style={modernStyles.cancelButton}
              >
                Cancelar
              </button>
              <button 
                type="submit" 
                disabled={isLoading}
                style={{
                  ...modernStyles.submitButton,
                  opacity: isLoading ? 0.6 : 1
                }}
              >
                {isLoading ? 'Creando...' : 'Crear Préstamo'}
              </button>
            </div>
          </form>
          
          {selectedProduct && newLoan.quantity_loaned && (
            <div style={modernStyles.summaryCard}>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '1.1rem' }}>📊 Resumen del Préstamo:</h4>
              <p><strong>Producto:</strong> {selectedProduct.name}</p>
              <p><strong>Stock actual:</strong> {selectedProduct.stock_quantity}</p>
              <p><strong>Cantidad a prestar:</strong> {newLoan.quantity_loaned}</p>
              <p><strong>Stock después del préstamo:</strong> {selectedProduct.stock_quantity - parseInt(newLoan.quantity_loaned || '0')}</p>
              <p><strong>Valor total prestado:</strong> ${(selectedProduct.selling_price * parseInt(newLoan.quantity_loaned || '0')).toLocaleString('es-CO')} COP</p>
            </div>
          )}
        </div>
      )}

      {/* Formulario de gestión de distribuidores */}
      {showDistributorForm && (
        <div style={modernStyles.formContainer}>
          <h2 style={modernStyles.formTitle}>👥 Gestionar Distribuidores</h2>
          
          {/* Formulario para crear nuevo distribuidor */}
          <form onSubmit={handleCreateDistributor} style={modernStyles.formGrid}>
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>Nombre del Distribuidor:</label>
              <input
                type="text"
                value={newDistributor.name}
                onChange={(e) => setNewDistributor({...newDistributor, name: e.target.value})}
                required
                style={modernStyles.input}
                placeholder="Ej: Distribuidora ABC"
              />
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>Persona de Contacto:</label>
              <input
                type="text"
                value={newDistributor.contact_person}
                onChange={(e) => setNewDistributor({...newDistributor, contact_person: e.target.value})}
                required
                style={modernStyles.input}
                placeholder="Ej: Juan Pérez"
              />
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>Teléfono:</label>
              <input
                type="tel"
                value={newDistributor.phone_number}
                onChange={(e) => setNewDistributor({...newDistributor, phone_number: e.target.value})}
                required
                style={modernStyles.input}
                placeholder="Ej: +57 300 123 4567"
              />
            </div>
            
            <div style={modernStyles.inputGroup}>
              <label style={modernStyles.label}>Código de Acceso:</label>
              <input
                type="text"
                value={newDistributor.access_code}
                onChange={(e) => setNewDistributor({...newDistributor, access_code: e.target.value})}
                style={modernStyles.input}
                placeholder="Opcional - Se genera automáticamente"
              />
              <small style={modernStyles.helpText}>
                Si se deja vacío, se generará automáticamente
              </small>
            </div>
            
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button 
                type="button" 
                onClick={() => setShowDistributorForm(false)}
                style={modernStyles.cancelButton}
              >
                Cancelar
              </button>
              <button 
                type="submit" 
                disabled={isLoading}
                style={{
                  ...modernStyles.submitButton,
                  opacity: isLoading ? 0.6 : 1
                }}
              >
                {isLoading ? 'Creando...' : 'Crear Distribuidor'}
              </button>
            </div>
          </form>
          
          {/* Lista de distribuidores existentes */}
          <div style={modernStyles.distributorSection}>
            <h3 style={modernStyles.formTitle}>📋 Distribuidores Registrados ({distributors.length})</h3>
            
            {distributors.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                <p>💭 No hay distribuidores registrados</p>
                <p>Crea el primer distribuidor usando el formulario de arriba</p>
              </div>
            ) : (
              <div style={modernStyles.distributorGrid}>
                {distributors.map(distributor => (
                  <div 
                    key={distributor.id} 
                    style={modernStyles.distributorCard}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#1e293b' }}>
                        {distributor.name}
                      </h4>
                      <span style={{
                        ...modernStyles.statusBadge,
                        backgroundColor: '#10b981',
                        color: 'white'
                      }}>
                        ID: {distributor.id}
                      </span>
                    </div>
                    
                    <div style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.5' }}>
                      <p style={{ margin: '4px 0' }}>
                        <strong>👤 Contacto:</strong> {distributor.contact_person}
                      </p>
                      <p style={{ margin: '4px 0' }}>
                        <strong>📞 Teléfono:</strong> {distributor.phone_number}
                      </p>
                      <p style={{ margin: '4px 0' }}>
                        <strong>🔑 Código:</strong> 
                        <span style={{
                          backgroundColor: '#f3f4f6',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontFamily: 'monospace',
                          marginLeft: '8px'
                        }}>
                          {distributor.access_code}
                        </span>
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Lista de préstamos */}
      <div style={modernStyles.card}>
        <h2 style={modernStyles.formTitle}>📋 Préstamos Activos ({loans.length})</h2>
        {isLoading && (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            Cargando préstamos...
          </div>
        )}
        
        <div style={{ overflowX: 'auto' }}>
          <table style={modernStyles.table}>
            <thead>
              <tr style={modernStyles.tableHeader}>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'left'}}>ID</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'left'}}>Distribuidor</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'left'}}>Producto</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'right'}}>Cantidad</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'right'}}>Valor Total</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'center'}}>Fecha Préstamo</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'center'}}>Vencimiento</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'center'}}>Estado</th>
                <th style={{...modernStyles.tableHeaderCell, textAlign: 'center'}}>Días Restantes</th>
              </tr>
            </thead>
            <tbody>
              {loans.map(loan => {
                const product = getProductInfo(loan.product_id);
                const distributor = getDistributorInfo(loan.distributor_id);
                const daysUntilDue = calculateDaysUntilDue(loan.return_due_date);
                const isOverdue = daysUntilDue < 0;
                
                return (
                  <tr key={loan.id} style={{ 
                    backgroundColor: isOverdue ? '#fff3cd' : 'white'
                  }}>
                    <td style={modernStyles.tableCell}>#{loan.id}</td>
                    <td style={modernStyles.tableCell}>
                      {distributor?.name || `ID: ${loan.distributor_id}`}
                      <br />
                      <small style={modernStyles.helpText}>
                        Código: {distributor?.access_code || 'N/A'}
                      </small>
                    </td>
                    <td style={modernStyles.tableCell}>
                      {product?.name || `ID: ${loan.product_id}`}
                      <br />
                      <small style={modernStyles.helpText}>
                        SKU: {product?.sku || 'N/A'}
                      </small>
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'right'}}>
                      {loan.quantity_loaned}
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'right'}}>
                      ${((product?.selling_price || 0) * loan.quantity_loaned).toLocaleString('es-CO')}
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'center'}}>
                      {loan.loan_date}
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'center'}}>
                      {loan.return_due_date}
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'center'}}>
                      <span style={{ 
                        ...modernStyles.statusBadge,
                        color: 'white',
                        backgroundColor: getStatusColor(loan.status)
                      }}>
                        {loan.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td style={{...modernStyles.tableCell, textAlign: 'center'}}>
                      <span style={{ 
                        color: isOverdue ? '#dc3545' : daysUntilDue <= 7 ? '#f59e0b' : '#059669',
                        fontWeight: '600',
                        fontSize: '13px'
                      }}>
                        {isOverdue ? `Vencido ${Math.abs(daysUntilDue)} días` : `${daysUntilDue} días`}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {loans.length === 0 && !isLoading && (
          <div style={{ 
            textAlign: 'center', 
            padding: '40px',
            color: '#666'
          }}>
            <p>📭 No hay préstamos registrados</p>
            <p>Haz clic en &quot;Crear Préstamo&quot; para agregar el primero</p>
          </div>
        )}
      </div>
      
      {/* Resumen estadístico */}
      {loans.length > 0 && (
        <div style={modernStyles.statsGrid}>
          <div style={{
            ...modernStyles.statCard,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white'
          }}>
            <h3 style={modernStyles.statLabel}>📊 Total Préstamos</h3>
            <p style={modernStyles.statNumber}>{loans.length}</p>
          </div>
          
          <div style={{
            ...modernStyles.statCard,
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: 'white'
          }}>
            <h3 style={modernStyles.statLabel}>✅ En Préstamo</h3>
            <p style={modernStyles.statNumber}>
              {loans.filter(l => l.status === 'en_prestamo').length}
            </p>
          </div>
          
          <div style={{
            ...modernStyles.statCard,
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            color: 'white'
          }}>
            <h3 style={modernStyles.statLabel}>⚠️ Por Vencer</h3>
            <p style={modernStyles.statNumber}>
              {loans.filter(l => {
                const days = calculateDaysUntilDue(l.return_due_date);
                return days <= 7 && days >= 0 && l.status === 'en_prestamo';
              }).length}
            </p>
          </div>
          
          <div style={{
            ...modernStyles.statCard,
            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            color: 'white'
          }}>
            <h3 style={modernStyles.statLabel}>🚨 Vencidos</h3>
            <p style={modernStyles.statNumber}>
              {loans.filter(l => calculateDaysUntilDue(l.return_due_date) < 0 && l.status === 'en_prestamo').length}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConsignmentLoansPage;