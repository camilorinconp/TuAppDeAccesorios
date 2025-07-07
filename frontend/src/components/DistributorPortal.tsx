// /frontend/src/components/DistributorPortal.tsx
import React, { useState } from 'react';
import { ConsignmentLoan } from '../types';
import { getDistributorLoansByAccessCode, postConsignmentReport } from '../services/api';

const DistributorPortal: React.FC = () => {
    const [accessCode, setAccessCode] = useState('');
    const [distributorId, setDistributorId] = useState<number | null>(null);
    const [loans, setLoans] = useState<ConsignmentLoan[]>([]);
    const [error, setError] = useState<string | null>(null);

    const handleLogin = async () => {
        try {
            // En una app real, tendrías un endpoint que valide el código
            // y devuelva el ID del distribuidor.
            // Aquí simulamos esa lógica.
            const { loans, distributor } = await getDistributorLoansByAccessCode(accessCode);
            setLoans(loans);
            setDistributorId(distributor.id);
            setError(null);
        } catch (err) {
            setError("Código de acceso inválido o error al cargar los datos.");
            setDistributorId(null);
            setLoans([]);
        }
    };

    if (!distributorId) {
        return (
            <div style={{ padding: '20px' }}>
                <h1>Portal de Distribuidores</h1>
                <input
                    type="password"
                    value={accessCode}
                    onChange={(e) => setAccessCode(e.target.value)}
                    placeholder="Ingrese su código de acceso"
                    style={{ padding: '10px' }}
                />
                <button onClick={handleLogin} style={{ padding: '10px' }}>Ingresar</button>
                {error && <p style={{ color: 'red' }}>{error}</p>}
            </div>
        );
    }

    return (
        <div style={{ padding: '20px' }}>
            <h1>Bienvenido, Distribuidor</h1>
            <h2>Sus Préstamos Activos</h2>
            {loans.filter(loan => loan.status === 'en_prestamo').map(loan => (
                <LoanReportForm key={loan.id} loan={loan} />
            ))}
        </div>
    );
};

// Sub-componente para el formulario de reporte
interface LoanFormProps {
    loan: ConsignmentLoan;
}

const LoanReportForm: React.FC<LoanFormProps> = ({ loan }) => {
    const [sold, setSold] = useState(0);
    const [returned, setReturned] = useState(0);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (sold + returned > loan.quantity_loaned) {
            setError("La cantidad vendida y devuelta no puede superar la cantidad prestada.");
            return;
        }

        try {
            await postConsignmentReport({
                loan_id: loan.id,
                quantity_sold: sold,
                quantity_returned: returned,
                report_date: new Date().toISOString().split('T')[0],
            });
            setSuccess("Reporte enviado con éxito.");
            setError('');
        } catch (err) {
            setError("Error al enviar el reporte.");
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

export default DistributorPortal;
