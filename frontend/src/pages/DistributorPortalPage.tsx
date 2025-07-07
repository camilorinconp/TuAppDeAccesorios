import React, { useState } from 'react';
import { ConsignmentLoan } from '../types';
import { getDistributorLoansByAccessCode, postConsignmentReport, loginDistributor } from '../services/api';

const DistributorPortalPage: React.FC = () => {
    const [accessCode, setAccessCode] = useState('');
    const [distributorId, setDistributorId] = useState<number | null>(null);
    const [loans, setLoans] = useState<ConsignmentLoan[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState(''); // Para el nombre del distribuidor

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        try {
            // Autenticar al distribuidor para obtener un token
            const authData = await loginDistributor(username, accessCode);
            localStorage.setItem('distributorAuthToken', authData.access_token); // Guardar token

            // Obtener los préstamos usando el token y el ID del distribuidor (que podría venir en el token)
            // Por ahora, asumimos que el ID del distribuidor se puede obtener de alguna manera
            // o que el endpoint de préstamos no requiere el ID si el token lo contiene.
            // Para este ejemplo, asumiremos que el ID del distribuidor es 1 para pruebas.
            // En un escenario real, el token JWT del distribuidor debería contener su ID.
            const fetchedLoans = await getDistributorLoansByAccessCode(accessCode); // Pasamos el accessCode para simular la búsqueda
            setLoans(fetchedLoans.loans);
            setDistributorId(fetchedLoans.distributor.id); // Obtenemos el ID del distribuidor de la respuesta

        } catch (err: any) {
            console.error('❌ Error en login distribuidor:', err);
            setError(err.message || "Código de acceso o nombre de distribuidor inválido.");
            setDistributorId(null);
            setLoans([]);
        }
    };

    if (!distributorId) {
        return (
            <div style={{ padding: '20px' }}>
                <h1>Portal de Distribuidores</h1>
                <form onSubmit={handleLogin}>
                    <div style={{ marginBottom: '10px' }}>
                        <label>Nombre de Distribuidor:</label>
                        <input type="text" value={username} onChange={e => setUsername(e.target.value)} required style={{ marginLeft: '10px' }} />
                    </div>
                    <div style={{ marginBottom: '10px' }}>
                        <label>Código de Acceso:</label>
                        <input type="password" value={accessCode} onChange={e => setAccessCode(e.target.value)} required style={{ marginLeft: '10px' }} />
                    </div>
                    <button type="submit">Ingresar</button>
                    {error && <p style={{ color: 'red' }}>{error}</p>}
                </form>
            </div>
        );
    }

    return (
        <div style={{ padding: '20px' }}>
            <h1>Bienvenido, Distribuidor (ID: {distributorId})</h1>
            <h2>Sus Préstamos Activos</h2>
            {loans.length === 0 ? (
                <p>No tiene préstamos activos.</p>
            ) : (
                loans.filter(loan => loan.status === 'en_prestamo').map(loan => (
                    <LoanReportForm key={loan.id} loan={loan} />
                ))
            )}
        </div>
    );
};

interface LoanFormProps {
    loan: ConsignmentLoan;
}

const LoanReportForm: React.FC<LoanFormProps> = ({ loan }) => {
    const [sold, setSold] = useState(0);
    const [returned, setReturned] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);

        if (sold + returned > loan.quantity_loaned) {
            setError("La cantidad vendida y devuelta no puede superar la cantidad prestada.");
            return;
        }

        try {
            await postConsignmentReport({
                loan_id: loan.id,
                quantity_sold: sold,
                quantity_returned: returned,
                report_date: new Date().toISOString().split('T')[0], // Formato YYYY-MM-DD
            });
            setSuccess("Reporte enviado con éxito.");
            // Opcional: Actualizar el estado del préstamo o recargar la lista
        } catch (err: any) {
            setError(`Error al enviar el reporte: ${err.message}.`);
        }
    };

    return (
        <form onSubmit={handleSubmit} style={{ border: '1px solid #ccc', padding: '15px', margin: '10px 0' }}>
            <h4>Producto: {loan.product?.name || `ID: ${loan.product_id}`}</h4>
            <p>Cantidad Prestada: {loan.quantity_loaned}</p>
            <div>
                <label>Cantidad Vendida: </label>
                <input type="number" value={sold} onChange={e => setSold(parseInt(e.target.value, 10))} min="0" />
            </div>
            <div>
                <label>Cantidad Devuelta: </label>
                <input type="number" value={returned} onChange={e => setReturned(parseInt(e.target.value, 10))} min="0" />
            </div>
            <button type="submit">Enviar Reporte</button>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {success && <p style={{ color: 'green' }}>{success}</p>}
        </form>
    );
};

export default DistributorPortalPage;
