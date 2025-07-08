from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, schemas, auth, models
from ..dependencies import get_db
from ..config import settings
from ..metrics import business_metrics
from ..logging_config import get_logger
from ..services.audit_service import AuditService
from ..models.audit import AuditActionType, AuditSeverity

router = APIRouter()
logger = get_logger(__name__)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    # Intentar encontrar usuario
    user = None
    failure_reason = None
    
    try:
        user = crud.get_user_by_username(db, username=form_data.username)
        if not user:
            failure_reason = "Usuario no encontrado"
        elif not auth.security.verify_password(form_data.password, user.hashed_password):
            failure_reason = "Contraseña incorrecta"
    except Exception as e:
        failure_reason = f"Error en verificación: {str(e)}"
    
    # Registrar intento de login
    session_id = AuditService.generate_session_id()
    AuditService.log_login_attempt(
        db=db,
        username=form_data.username,
        success=user is not None and failure_reason is None,
        user_id=user.id if user else None,
        session_id=session_id,
        failure_reason=failure_reason,
        request=request
    )
    
    # Si falló el login, lanzar excepción
    if failure_reason:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}
    )
    
    # Configurar cookies seguras
    auth.set_auth_cookies(response, access_token, refresh_token)
    
    # Registrar métricas de login
    business_metrics.record_user_login(user_id=user.id, user_type="user")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/distributor-token", response_model=schemas.Token)
def login_for_distributor_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    # Intentar encontrar distribuidor
    distributor = None
    failure_reason = None

    try:
        distributor = crud.get_distributor_by_name(db, name=form_data.username)
        if not distributor:
            failure_reason = "Distribuidor no encontrado"
        elif not auth.security.verify_password(form_data.password, distributor.access_code):
            failure_reason = "Código de acceso incorrecto"
    except Exception as e:
        failure_reason = f"Error en verificación: {str(e)}"

    # Registrar intento de login de distribuidor
    session_id = AuditService.generate_session_id()
    AuditService.log_login_attempt(
        db=db,
        username=form_data.username,
        success=distributor is not None and failure_reason is None,
        user_id=distributor.id if distributor else None, # Usar ID del distribuidor como user_id en auditoría
        session_id=session_id,
        failure_reason=failure_reason,
        request=request,
        is_distributor=True
    )

    # Si falló el login, lanzar excepción
    if failure_reason:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect distributor name or access code",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": distributor.name, "distributor_id": distributor.id, "role": "distributor"}, 
        expires_delta=access_token_expires
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": distributor.name, "distributor_id": distributor.id, "role": "distributor"}
    )
    
    # Configurar cookies seguras
    auth.set_auth_cookies(response, access_token, refresh_token)
    
    # Registrar métricas de login
    business_metrics.record_user_login(user_id=distributor.id, user_type="distributor")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Endpoint para refrescar el access token usando el refresh token"""
    return await auth.refresh_access_token(request, response, db)

@router.post("/logout")
async def logout(response: Response):
    """Endpoint para cerrar sesión y limpiar cookies"""
    auth.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}

@router.get("/verify")
async def verify_auth(
    request: Request,
    db: Session = Depends(get_db)
):
    """Endpoint para verificar si el usuario está autenticado"""
    try:
        user = await auth.get_current_user(request, db)
        return {"authenticated": True, "user": user.username, "role": user.role.value}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Página de login HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TuAppDeAccesorios - Login</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0; 
                padding: 0; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
            }
            .login-container { 
                background: white; 
                padding: 2rem; 
                border-radius: 10px; 
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 90%;
            }
            .logo { 
                text-align: center; 
                color: #667eea; 
                margin-bottom: 2rem; 
                font-size: 1.5rem;
                font-weight: bold;
            }
            .form-group { 
                margin-bottom: 1rem; 
            }
            label { 
                display: block; 
                margin-bottom: 0.5rem; 
                color: #333;
                font-weight: 500;
            }
            input[type="text"], input[type="password"] { 
                width: 100%; 
                padding: 0.75rem; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                box-sizing: border-box;
                font-size: 1rem;
            }
            input[type="text"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
            }
            .btn { 
                background: #667eea; 
                color: white; 
                padding: 0.75rem 1.5rem; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                width: 100%;
                font-size: 1rem;
                font-weight: 500;
                transition: background 0.3s;
            }
            .btn:hover { 
                background: #5a6fd8; 
            }
            .error { 
                color: #e74c3c; 
                margin-top: 0.5rem; 
                display: none;
            }
            .success { 
                color: #27ae60; 
                margin-top: 0.5rem; 
                display: none;
            }
            .info {
                background: #e8f4fd;
                border: 1px solid #bee5eb;
                color: #0c5460;
                padding: 1rem;
                border-radius: 5px;
                margin-bottom: 1rem;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">🏪 TuAppDeAccesorios</div>
            
            <div class="info">
                <strong>API Endpoints disponibles:</strong><br>
                • <a href="/docs" target="_blank">📖 Documentación API</a><br>
                • <a href="/health" target="_blank">💚 Estado del sistema</a><br>
                • <a href="/" target="_blank">🏠 Página principal</a>
            </div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Usuario:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Contraseña:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn">Iniciar Sesión</button>
                <div id="error" class="error"></div>
                <div id="success" class="success"></div>
            </form>
        </div>

        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const errorDiv = document.getElementById('error');
                const successDiv = document.getElementById('success');
                
                // Limpiar mensajes
                errorDiv.style.display = 'none';
                successDiv.style.display = 'none';
                
                try {
                    const formData = new FormData();
                    formData.append('username', username);
                    formData.append('password', password);
                    
                    const response = await fetch('/token', {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        successDiv.textContent = '¡Login exitoso! Token recibido.';
                        successDiv.style.display = 'block';
                        
                        // Verificar autenticación
                        setTimeout(async () => {
                            try {
                                const verifyResponse = await fetch('/verify', {
                                    credentials: 'include'
                                });
                                if (verifyResponse.ok) {
                                    const userData = await verifyResponse.json();
                                    successDiv.textContent = `¡Bienvenido ${userData.user}! Rol: ${userData.role}`;
                                }
                            } catch (error) {
                                console.error('Error verificando:', error);
                            }
                        }, 1000);
                        
                    } else {
                        const error = await response.json();
                        errorDiv.textContent = error.detail || 'Error en el login';
                        errorDiv.style.display = 'block';
                    }
                } catch (error) {
                    errorDiv.textContent = 'Error de conexión: ' + error.message;
                    errorDiv.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content
