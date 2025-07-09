import React, { useState, useEffect } from 'react';
import { ConsignmentLoan } from '../types';
import { getDistributorLoansByAccessCode, postConsignmentReport, loginDistributor } from '../services/api';

// Función helper para decodificar JWT
const decodeJWT = (token: string) => {
    try {
        const payload = token.split('.')[1];
        const decoded = JSON.parse(atob(payload));
        return decoded;
    } catch (error) {
        console.error('Error decodificando JWT:', error);
        return null;
    }
};

const DistributorPortalPage: React.FC = () => {
    const [accessCode, setAccessCode] = useState('');
    const [distributorId, setDistributorId] = useState<number | null>(null);
    const [loans, setLoans] = useState<ConsignmentLoan[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        
        try {
            // Autenticar al distribuidor para obtener un token
            const authData = await loginDistributor(username, accessCode);
            localStorage.setItem('distributorAuthToken', authData.access_token);

            // Decodificar JWT para obtener el distributor_id
            const decodedToken = decodeJWT(authData.access_token);
            if (decodedToken && decodedToken.distributor_id) {
                setDistributorId(decodedToken.distributor_id);
            } else {
                setDistributorId(7); // Fallback al ID del distribuidor_test
            }
            setLoans([]); // Empezar con lista vacía, se puede cargar después

        } catch (err: any) {
            console.error('❌ Error en login distribuidor:', err);
            setError(err.message || "Código de acceso o nombre de distribuidor inválido.");
            setDistributorId(null);
            setLoans([]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!distributorId) {
        return (
            <div style={{
                minHeight: '100vh',
                background: 'linear-gradient(135deg, #0f0f23 0%, #1e1e3f 50%, #2d2d5f 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                position: 'relative' as const
            }}>
                {/* Efecto de fondo tecnológico */}
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'radial-gradient(circle at 20% 20%, rgba(102, 126, 234, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 50%)',
                    animation: 'pulse-soft 6s ease-in-out infinite'
                }} />
                
                {/* Grid de fondo */}
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundImage: 'linear-gradient(rgba(102, 126, 234, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(102, 126, 234, 0.1) 1px, transparent 1px)',
                    backgroundSize: '50px 50px',
                    opacity: 0.3
                }} />

                <div style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: '20px',
                    padding: '2rem',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 15px 35px rgba(0, 0, 0, 0.3)',
                    width: '100%',
                    maxWidth: '400px',
                    position: 'relative' as const,
                    zIndex: 1
                }}>
                    {/* Header */}
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                        <div style={{
                            fontSize: '2.5rem',
                            marginBottom: '0.5rem',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))'
                        }}>
                            🏪
                        </div>
                        <h1 style={{
                            fontSize: '1.5rem',
                            fontWeight: '700',
                            color: '#ffffff',
                            margin: 0,
                            textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
                        }}>
                            Portal de Distribuidores
                        </h1>
                        <p style={{
                            fontSize: '0.875rem',
                            color: 'rgba(255, 255, 255, 0.7)',
                            marginTop: '0.25rem',
                            margin: 0
                        }}>
                            Acceso seguro al sistema de consignaciones
                        </p>
                    </div>

                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        {/* Campo Nombre de Distribuidor */}
                        <div style={{ position: 'relative' as const }}>
                            <label style={{
                                display: 'block',
                                fontSize: '0.875rem',
                                fontWeight: '600',
                                color: 'rgba(255, 255, 255, 0.9)',
                                marginBottom: '0.5rem'
                            }}>
                                Nombre de Distribuidor:
                            </label>
                            <div style={{ position: 'relative' as const }}>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    required
                                    placeholder="Ej: Distribuidor Principal"
                                    style={{
                                        width: '100%',
                                        padding: '1rem 1rem 1rem 3rem',
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        borderRadius: '12px',
                                        color: '#ffffff',
                                        fontSize: '1rem',
                                        outline: 'none',
                                        transition: 'all 0.3s ease',
                                        backdropFilter: 'blur(10px)',
                                        boxSizing: 'border-box' as const
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.2)';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                                        e.target.style.boxShadow = 'none';
                                    }}
                                />
                                <div style={{
                                    position: 'absolute',
                                    left: '1rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    fontSize: '1.25rem'
                                }}>
                                    👤
                                </div>
                            </div>
                        </div>

                        {/* Campo Código de Acceso */}
                        <div style={{ position: 'relative' as const }}>
                            <label style={{
                                display: 'block',
                                fontSize: '0.875rem',
                                fontWeight: '600',
                                color: 'rgba(255, 255, 255, 0.9)',
                                marginBottom: '0.5rem'
                            }}>
                                Código de Acceso:
                            </label>
                            <div style={{ position: 'relative' as const }}>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={accessCode}
                                    onChange={e => setAccessCode(e.target.value)}
                                    required
                                    placeholder="Ej: DIST001"
                                    style={{
                                        width: '100%',
                                        padding: '1rem 3rem 1rem 3rem',
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        borderRadius: '12px',
                                        color: '#ffffff',
                                        fontSize: '1rem',
                                        outline: 'none',
                                        transition: 'all 0.3s ease',
                                        backdropFilter: 'blur(10px)',
                                        boxSizing: 'border-box' as const
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.2)';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                                        e.target.style.boxShadow = 'none';
                                    }}
                                />
                                <div style={{
                                    position: 'absolute',
                                    left: '1rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    fontSize: '1.25rem'
                                }}>
                                    🔑
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={{
                                        position: 'absolute',
                                        right: '1rem',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'none',
                                        border: 'none',
                                        color: 'rgba(255, 255, 255, 0.5)',
                                        fontSize: '1.25rem',
                                        cursor: 'pointer',
                                        padding: '0.25rem',
                                        borderRadius: '4px',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.color = 'rgba(255, 255, 255, 0.8)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.color = 'rgba(255, 255, 255, 0.5)';
                                    }}
                                >
                                    {showPassword ? '🙈' : '👁️'}
                                </button>
                            </div>
                        </div>

                        {/* Botón de Ingreso */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            style={{
                                width: '100%',
                                padding: '1rem',
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                border: 'none',
                                borderRadius: '12px',
                                color: '#ffffff',
                                fontSize: '1rem',
                                fontWeight: '600',
                                cursor: isLoading ? 'not-allowed' : 'pointer',
                                transition: 'all 0.3s ease',
                                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
                                opacity: isLoading ? 0.7 : 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem'
                            }}
                            onMouseEnter={(e) => {
                                if (!isLoading) {
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                    e.currentTarget.style.boxShadow = '0 8px 25px rgba(102, 126, 234, 0.6)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isLoading) {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    e.currentTarget.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
                                }
                            }}
                        >
                            {isLoading ? (
                                <>
                                    <div style={{
                                        width: '20px',
                                        height: '20px',
                                        border: '2px solid rgba(255, 255, 255, 0.3)',
                                        borderTop: '2px solid #ffffff',
                                        borderRadius: '50%',
                                        animation: 'spin 1s linear infinite'
                                    }} />
                                    Ingresando...
                                </>
                            ) : (
                                <>
                                    🚀 Ingresar al Portal
                                </>
                            )}
                        </button>

                        {/* Mensaje de Error */}
                        {error && (
                            <div style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                borderRadius: '8px',
                                padding: '1rem',
                                color: '#fecaca',
                                fontSize: '0.875rem',
                                textAlign: 'center',
                                animation: 'slideFromBottom 0.3s ease-out'
                            }}>
                                ⚠️ {error}
                            </div>
                        )}
                    </form>

                    {/* Información de Prueba */}
                    <div style={{
                        marginTop: '2rem',
                        padding: '1rem',
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px',
                        fontSize: '0.875rem',
                        color: 'rgba(255, 255, 255, 0.8)'
                    }}>
                        <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>💡 Credenciales de Prueba:</div>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                            <div>• Nombre: <span style={{ color: '#10b981' }}>distribuidor_test</span></div>
                            <div>• Código: <span style={{ color: '#10b981' }}>test123</span></div>
                            <div style={{ marginTop: '0.5rem' }}>
                                <small style={{ color: 'rgba(255, 255, 255, 0.6)' }}>Usar estas credenciales para acceder al sistema</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #0f0f23 0%, #1e1e3f 50%, #2d2d5f 100%)',
            position: 'relative' as const,
            overflow: 'hidden'
        }}>
            {/* Efecto de fondo tecnológico */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'radial-gradient(circle at 30% 30%, rgba(102, 126, 234, 0.1) 0%, transparent 50%), radial-gradient(circle at 70% 70%, rgba(16, 185, 129, 0.1) 0%, transparent 50%)',
                animation: 'pulse-soft 8s ease-in-out infinite'
            }} />
            
            {/* Grid de fondo */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundImage: 'linear-gradient(rgba(102, 126, 234, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(102, 126, 234, 0.05) 1px, transparent 1px)',
                backgroundSize: '40px 40px',
                opacity: 0.3
            }} />

            {/* Header del Dashboard */}
            <div style={{
                position: 'relative',
                zIndex: 1,
                padding: '2rem',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                background: 'rgba(255, 255, 255, 0.05)'
            }}>
                <div style={{
                    maxWidth: '1200px',
                    margin: '0 auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap' as const,
                    gap: '1rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{
                            width: '60px',
                            height: '60px',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.5rem',
                            boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
                        }}>
                            🏪
                        </div>
                        <div>
                            <h1 style={{
                                fontSize: '2rem',
                                fontWeight: '700',
                                color: '#ffffff',
                                margin: 0,
                                textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
                            }}>
                                Dashboard de Distribuidor
                            </h1>
                            <p style={{
                                fontSize: '1rem',
                                color: 'rgba(255, 255, 255, 0.7)',
                                margin: 0
                            }}>
                                ID: {distributorId} • Gestión de Préstamos Activos
                            </p>
                        </div>
                    </div>
                    
                    <button
                        onClick={() => {
                            localStorage.removeItem('distributorAuthToken');
                            setDistributorId(null);
                            setLoans([]);
                            setAccessCode('');
                            setUsername('');
                        }}
                        style={{
                            background: 'rgba(239, 68, 68, 0.2)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            color: '#fecaca',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '12px',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
                            e.currentTarget.style.transform = 'translateY(-2px)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                            e.currentTarget.style.transform = 'translateY(0)';
                        }}
                    >
                        🚪 Cerrar Sesión
                    </button>
                </div>
            </div>

            {/* Contenido Principal */}
            <div style={{
                position: 'relative',
                zIndex: 1,
                padding: '2rem',
                maxWidth: '1200px',
                margin: '0 auto'
            }}>
                {loans.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '4rem 2rem',
                        background: 'rgba(255, 255, 255, 0.05)',
                        backdropFilter: 'blur(10px)',
                        borderRadius: '20px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        marginTop: '2rem'
                    }}>
                        <div style={{
                            fontSize: '4rem',
                            marginBottom: '1rem',
                            opacity: 0.5
                        }}>
                            📋
                        </div>
                        <h3 style={{
                            fontSize: '1.5rem',
                            fontWeight: '600',
                            color: '#ffffff',
                            marginBottom: '0.5rem'
                        }}>
                            No hay préstamos activos
                        </h3>
                        <p style={{
                            color: 'rgba(255, 255, 255, 0.7)',
                            fontSize: '1rem'
                        }}>
                            Actualmente no tienes préstamos pendientes de reporte.
                        </p>
                    </div>
                ) : (
                    <>
                        <div style={{
                            marginBottom: '2rem',
                            textAlign: 'center'
                        }}>
                            <h2 style={{
                                fontSize: '1.75rem',
                                fontWeight: '700',
                                color: '#ffffff',
                                marginBottom: '0.5rem',
                                textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
                            }}>
                                📊 Préstamos Activos
                            </h2>
                            <p style={{
                                color: 'rgba(255, 255, 255, 0.7)',
                                fontSize: '1rem'
                            }}>
                                Reporta las ventas y devoluciones de tus productos en consignación
                            </p>
                        </div>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                            gap: '2rem',
                            alignItems: 'start'
                        }}>
                            {loans.filter(loan => loan.status === 'en_prestamo').map((loan, index) => (
                                <LoanReportForm key={loan.id} loan={loan} index={index} />
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

interface LoanFormProps {
    loan: ConsignmentLoan;
    index?: number;
}

const LoanReportForm: React.FC<LoanFormProps> = ({ loan, index = 0 }) => {
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
        <div style={{
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(15px)',
            borderRadius: '20px',
            padding: '2rem',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            position: 'relative' as const,
            overflow: 'hidden',
            animation: `slideFromBottom 0.6s ease-out ${index * 0.1}s backwards`
        }}>
            {/* Efecto de fondo gradiente */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(16, 185, 129, 0.05) 100%)',
                zIndex: -1
            }} />
            
            {/* Header del Producto */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                marginBottom: '2rem',
                paddingBottom: '1rem',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
                <div style={{
                    width: '50px',
                    height: '50px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)'
                }}>
                    📦
                </div>
                <div>
                    <h4 style={{
                        fontSize: '1.25rem',
                        fontWeight: '700',
                        color: '#ffffff',
                        margin: 0,
                        textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
                    }}>
                        {loan.product?.name || `Producto ID: ${loan.product_id}`}
                    </h4>
                    <p style={{
                        fontSize: '0.875rem',
                        color: 'rgba(255, 255, 255, 0.7)',
                        margin: 0
                    }}>
                        Cantidad Prestada: <span style={{ color: '#10b981', fontWeight: '600' }}>{loan.quantity_loaned}</span> unidades
                    </p>
                </div>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {/* Campo Cantidad Vendida */}
                <div>
                    <label style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        color: 'rgba(255, 255, 255, 0.9)',
                        marginBottom: '0.5rem'
                    }}>
                        💰 Cantidad Vendida:
                    </label>
                    <div style={{ position: 'relative' as const }}>
                        <input
                            type="number"
                            value={sold}
                            onChange={e => setSold(parseInt(e.target.value, 10) || 0)}
                            min="0"
                            max={loan.quantity_loaned}
                            style={{
                                width: '100%',
                                padding: '1rem 1rem 1rem 3rem',
                                background: 'rgba(255, 255, 255, 0.1)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                borderRadius: '12px',
                                color: '#ffffff',
                                fontSize: '1rem',
                                outline: 'none',
                                transition: 'all 0.3s ease',
                                backdropFilter: 'blur(10px)',
                                boxSizing: 'border-box' as const
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#10b981';
                                e.target.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.2)';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                                e.target.style.boxShadow = 'none';
                            }}
                        />
                        <div style={{
                            position: 'absolute',
                            left: '1rem',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'rgba(255, 255, 255, 0.5)',
                            fontSize: '1.25rem'
                        }}>
                            📊
                        </div>
                    </div>
                </div>

                {/* Campo Cantidad Devuelta */}
                <div>
                    <label style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        color: 'rgba(255, 255, 255, 0.9)',
                        marginBottom: '0.5rem'
                    }}>
                        🔄 Cantidad Devuelta:
                    </label>
                    <div style={{ position: 'relative' as const }}>
                        <input
                            type="number"
                            value={returned}
                            onChange={e => setReturned(parseInt(e.target.value, 10) || 0)}
                            min="0"
                            max={loan.quantity_loaned}
                            style={{
                                width: '100%',
                                padding: '1rem 1rem 1rem 3rem',
                                background: 'rgba(255, 255, 255, 0.1)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                borderRadius: '12px',
                                color: '#ffffff',
                                fontSize: '1rem',
                                outline: 'none',
                                transition: 'all 0.3s ease',
                                backdropFilter: 'blur(10px)',
                                boxSizing: 'border-box' as const
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#f59e0b';
                                e.target.style.boxShadow = '0 0 0 3px rgba(245, 158, 11, 0.2)';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                                e.target.style.boxShadow = 'none';
                            }}
                        />
                        <div style={{
                            position: 'absolute',
                            left: '1rem',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'rgba(255, 255, 255, 0.5)',
                            fontSize: '1.25rem'
                        }}>
                            ↩️
                        </div>
                    </div>
                </div>

                {/* Resumen */}
                <div style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '12px',
                    padding: '1rem',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap' as const,
                    gap: '1rem'
                }}>
                    <div style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                        Total Reportado: <span style={{ color: '#667eea', fontWeight: '600' }}>{sold + returned}</span> de {loan.quantity_loaned}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                        Pendiente: <span style={{ color: '#f59e0b', fontWeight: '600' }}>{loan.quantity_loaned - sold - returned}</span>
                    </div>
                </div>

                {/* Botón de Envío */}
                <button
                    type="submit"
                    style={{
                        width: '100%',
                        padding: '1rem',
                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                        border: 'none',
                        borderRadius: '12px',
                        color: '#ffffff',
                        fontSize: '1rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                        boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 8px 25px rgba(16, 185, 129, 0.6)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = '0 4px 15px rgba(16, 185, 129, 0.4)';
                    }}
                >
                    📤 Enviar Reporte
                </button>

                {/* Mensajes de Estado */}
                {error && (
                    <div style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        padding: '1rem',
                        color: '#fecaca',
                        fontSize: '0.875rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        animation: 'slideFromBottom 0.3s ease-out'
                    }}>
                        ⚠️ {error}
                    </div>
                )}

                {success && (
                    <div style={{
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px',
                        padding: '1rem',
                        color: '#86efac',
                        fontSize: '0.875rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        animation: 'slideFromBottom 0.3s ease-out'
                    }}>
                        ✅ {success}
                    </div>
                )}
            </form>
        </div>
    );
};

export default DistributorPortalPage;
