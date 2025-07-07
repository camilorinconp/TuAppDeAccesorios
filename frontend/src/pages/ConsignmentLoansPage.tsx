import React, { useState, useEffect } from 'react';
import { ConsignmentLoan, Product, Distributor } from '../types';
import ErrorNotification from '../components/ErrorNotification';
import { useApiError } from '../hooks/useApiError';
import { apiRequest } from '../services/api';

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
    return_due_date: '',
    status: 'en_prestamo'
  });
  const [success, setSuccess] = useState<string | null>(null);
  
  const { error, isLoading, clearError, executeWithErrorHandling } = useApiError();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    await executeWithErrorHandling(async () => {
      const [loansResponse, productsResponse, distributorsResponse] = await Promise.all([
        apiRequest<ConsignmentLoan[]>('/consignments/loans?skip=0&limit=100'),
        apiRequest<{products: Product[]}>('/products/?skip=0&limit=100'),
        apiRequest<Distributor[]>('/distributors/')
      ]);
      
      setLoans(loansResponse || []);
      setProducts(productsResponse?.products || []);
      setDistributors(distributorsResponse || []);
    });
  };

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
        return_due_date: '',
        status: 'en_prestamo'
      });
      setShowCreateForm(false);
      await fetchData(); // Refrescar datos
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

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>🏪 Gestión de Préstamos de Consignación</h1>
        <button 
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{
            padding: '10px 20px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {showCreateForm ? 'Cancelar' : '+ Crear Préstamo'}
        </button>
      </div>
      
      {/* Notificación de error */}
      <ErrorNotification error={error} onClose={clearError} />
      
      {/* Mensaje de éxito */}
      {success && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#d4edda', 
          border: '1px solid #c3e6cb', 
          borderRadius: '4px', 
          color: '#155724',
          marginBottom: '20px'
        }}>
          {success}
        </div>
      )}

      {/* Formulario de creación */}
      {showCreateForm && (
        <div style={{ 
          marginBottom: '30px', 
          border: '1px solid #ddd', 
          padding: '20px',
          borderRadius: '8px',
          backgroundColor: '#f8f9fa'
        }}>
          <h2>📝 Crear Nuevo Préstamo</h2>
          <form onSubmit={handleCreateLoan} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Distribuidor:
              </label>
              <select 
                value={newLoan.distributor_id} 
                onChange={e => setNewLoan({...newLoan, distributor_id: e.target.value})}
                required
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                <option value="">Seleccionar distribuidor...</option>
                {distributors.map(dist => (
                  <option key={dist.id} value={dist.id}>
                    {dist.name} (Código: {dist.access_code})
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Producto:
              </label>
              <select 
                value={newLoan.product_id} 
                onChange={e => setNewLoan({...newLoan, product_id: e.target.value})}
                required
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                <option value="">Seleccionar producto...</option>
                {products.map(product => (
                  <option key={product.id} value={product.id}>
                    {product.name} - Stock: {product.stock_quantity} (${product.selling_price.toLocaleString('es-CO')})
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Cantidad a Prestar:
              </label>
              <input 
                type="number" 
                value={newLoan.quantity_loaned} 
                onChange={e => setNewLoan({...newLoan, quantity_loaned: e.target.value})}
                min="1"
                max={selectedProduct?.stock_quantity || 999}
                required
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
              {selectedProduct && (
                <small style={{ color: '#666' }}>
                  Stock disponible: {selectedProduct.stock_quantity} unidades
                </small>
              )}
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Fecha de Préstamo:
              </label>
              <input 
                type="date" 
                value={newLoan.loan_date} 
                onChange={e => setNewLoan({...newLoan, loan_date: e.target.value})}
                required
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Fecha de Vencimiento:
              </label>
              <input 
                type="date" 
                value={newLoan.return_due_date} 
                onChange={e => setNewLoan({...newLoan, return_due_date: e.target.value})}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
              <small style={{ color: '#666' }}>
                Opcional: 30 días por defecto desde la fecha de préstamo
              </small>
            </div>
            
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button 
                type="button" 
                onClick={() => setShowCreateForm(false)}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancelar
              </button>
              <button 
                type="submit" 
                disabled={isLoading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  opacity: isLoading ? 0.6 : 1
                }}
              >
                {isLoading ? 'Creando...' : 'Crear Préstamo'}
              </button>
            </div>
          </form>
          
          {selectedProduct && newLoan.quantity_loaned && (
            <div style={{ 
              marginTop: '20px', 
              padding: '15px', 
              backgroundColor: '#e3f2fd', 
              borderRadius: '4px',
              border: '1px solid #bbdefb'
            }}>
              <h4>📊 Resumen del Préstamo:</h4>
              <p><strong>Producto:</strong> {selectedProduct.name}</p>
              <p><strong>Stock actual:</strong> {selectedProduct.stock_quantity}</p>
              <p><strong>Cantidad a prestar:</strong> {newLoan.quantity_loaned}</p>
              <p><strong>Stock después del préstamo:</strong> {selectedProduct.stock_quantity - parseInt(newLoan.quantity_loaned || '0')}</p>
              <p><strong>Valor total prestado:</strong> ${(selectedProduct.selling_price * parseInt(newLoan.quantity_loaned || '0')).toLocaleString('es-CO')} COP</p>
            </div>
          )}
        </div>
      )}

      {/* Lista de préstamos */}
      <div>
        <h2>📋 Préstamos Activos ({loans.length})</h2>
        {isLoading && (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            Cargando préstamos...
          </div>
        )}
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8f9fa' }}>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>ID</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>Distribuidor</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>Producto</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>Cantidad</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>Valor Total</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>Fecha Préstamo</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>Vencimiento</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>Estado</th>
                <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>Días Restantes</th>
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
                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>#{loan.id}</td>
                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                      {distributor?.name || `ID: ${loan.distributor_id}`}
                      <br />
                      <small style={{ color: '#666' }}>
                        Código: {distributor?.access_code || 'N/A'}
                      </small>
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                      {product?.name || `ID: ${loan.product_id}`}
                      <br />
                      <small style={{ color: '#666' }}>
                        SKU: {product?.sku || 'N/A'}
                      </small>
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'right' }}>
                      {loan.quantity_loaned}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'right' }}>
                      ${((product?.selling_price || 0) * loan.quantity_loaned).toLocaleString('es-CO')}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                      {loan.loan_date}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                      {loan.return_due_date}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '12px', 
                        color: 'white',
                        backgroundColor: getStatusColor(loan.status),
                        fontSize: '12px'
                      }}>
                        {loan.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                      <span style={{ 
                        color: isOverdue ? '#dc3545' : daysUntilDue <= 7 ? '#ffc107' : '#28a745',
                        fontWeight: 'bold'
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
        <div style={{ 
          marginTop: '30px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '15px'
        }}>
          <div style={{ 
            padding: '15px',
            backgroundColor: '#e3f2fd',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#1976d2' }}>📊 Total Préstamos</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>{loans.length}</p>
          </div>
          
          <div style={{ 
            padding: '15px',
            backgroundColor: '#e8f5e8',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#388e3c' }}>✅ En Préstamo</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
              {loans.filter(l => l.status === 'en_prestamo').length}
            </p>
          </div>
          
          <div style={{ 
            padding: '15px',
            backgroundColor: '#fff3e0',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#f57c00' }}>⚠️ Por Vencer</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
              {loans.filter(l => {
                const days = calculateDaysUntilDue(l.return_due_date);
                return days <= 7 && days >= 0 && l.status === 'en_prestamo';
              }).length}
            </p>
          </div>
          
          <div style={{ 
            padding: '15px',
            backgroundColor: '#ffebee',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#d32f2f' }}>🚨 Vencidos</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
              {loans.filter(l => calculateDaysUntilDue(l.return_due_date) < 0 && l.status === 'en_prestamo').length}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConsignmentLoansPage;