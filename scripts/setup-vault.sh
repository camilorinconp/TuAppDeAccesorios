#!/bin/bash

# Script para configurar HashiCorp Vault para gestión de secretos
echo "🔐 CONFIGURACIÓN DE HASHICORP VAULT"
echo "=================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Variables
VAULT_VERSION="1.15.2"
VAULT_DIR="/opt/vault"
VAULT_DATA_DIR="/opt/vault/data"
VAULT_CONFIG_DIR="/etc/vault.d"
VAULT_USER="vault"

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script debe ejecutarse como root${NC}"
   exit 1
fi

echo "1. INSTALANDO HASHICORP VAULT..."
echo "-------------------------------"

# Descargar e instalar Vault
if ! command -v vault &> /dev/null; then
    cd /tmp
    wget https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip
    unzip vault_${VAULT_VERSION}_linux_amd64.zip
    mv vault /usr/local/bin/
    chmod +x /usr/local/bin/vault
    echo -e "${GREEN}✓ Vault instalado${NC}"
else
    echo -e "${GREEN}✓ Vault ya está instalado${NC}"
fi

echo ""
echo "2. CONFIGURANDO USUARIO Y DIRECTORIOS..."
echo "---------------------------------------"

# Crear usuario vault
if ! id "$VAULT_USER" &>/dev/null; then
    useradd --system --home $VAULT_DIR --shell /bin/false $VAULT_USER
    echo -e "${GREEN}✓ Usuario vault creado${NC}"
else
    echo -e "${GREEN}✓ Usuario vault ya existe${NC}"
fi

# Crear directorios
mkdir -p $VAULT_DIR $VAULT_DATA_DIR $VAULT_CONFIG_DIR
chown -R $VAULT_USER:$VAULT_USER $VAULT_DIR
chmod 750 $VAULT_DIR $VAULT_DATA_DIR
echo -e "${GREEN}✓ Directorios configurados${NC}"

echo ""
echo "3. CREANDO CONFIGURACIÓN..."
echo "-------------------------"

# Configuración de Vault
cat > $VAULT_CONFIG_DIR/vault.hcl << 'EOF'
# Configuración de Vault para TuAppDeAccesorios

# Configuración de almacenamiento
storage "file" {
  path = "/opt/vault/data"
}

# Configuración de listener
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1
  # Para producción, habilitar TLS:
  # tls_disable = 0
  # tls_cert_file = "/path/to/cert.pem"
  # tls_key_file = "/path/to/key.pem"
}

# Configuración de API
api_addr = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

# Configuración de UI
ui = true

# Configuración de logging
log_level = "INFO"
log_file = "/var/log/vault/vault.log"

# Configuración de PID
pid_file = "/var/run/vault/vault.pid"

# Configuración de sello (seal)
# Para producción, usar auto-unseal con KMS:
# seal "awskms" {
#   region     = "us-east-1"
#   kms_key_id = "alias/vault-key"
# }
EOF

chown $VAULT_USER:$VAULT_USER $VAULT_CONFIG_DIR/vault.hcl
chmod 640 $VAULT_CONFIG_DIR/vault.hcl
echo -e "${GREEN}✓ Configuración creada${NC}"

echo ""
echo "4. CONFIGURANDO SERVICIO SYSTEMD..."
echo "---------------------------------"

# Crear servicio systemd
cat > /etc/systemd/system/vault.service << EOF
[Unit]
Description=HashiCorp Vault
Documentation=https://www.vaultproject.io/docs/
Requires=network-online.target
After=network-online.target
ConditionFileNotEmpty=$VAULT_CONFIG_DIR/vault.hcl
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=notify
User=$VAULT_USER
Group=$VAULT_USER
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=yes
PrivateDevices=yes
SecureBits=keep-caps
AmbientCapabilities=CAP_IPC_LOCK
Capabilities=CAP_IPC_LOCK+ep
CapabilityBoundingSet=CAP_SYSLOG CAP_IPC_LOCK
NoNewPrivileges=yes
ExecStart=/usr/local/bin/vault server -config=$VAULT_CONFIG_DIR/vault.hcl
ExecReload=/bin/kill --signal HUP \$MAINPID
KillMode=process
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
StartLimitInterval=60
StartLimitBurst=3
LimitNOFILE=65536
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
EOF

# Crear directorios para logs y PID
mkdir -p /var/log/vault /var/run/vault
chown $VAULT_USER:$VAULT_USER /var/log/vault /var/run/vault

# Habilitar y iniciar servicio
systemctl daemon-reload
systemctl enable vault
systemctl start vault

echo -e "${GREEN}✓ Servicio Vault configurado${NC}"

echo ""
echo "5. INICIALIZANDO VAULT..."
echo "-----------------------"

# Esperar a que Vault esté listo
sleep 5

# Verificar estado
if systemctl is-active --quiet vault; then
    echo -e "${GREEN}✓ Vault está ejecutándose${NC}"
    
    # Configurar variable de entorno
    export VAULT_ADDR='http://127.0.0.1:8200'
    
    # Verificar si Vault ya está inicializado
    if vault status 2>/dev/null | grep -q "Initialized.*true"; then
        echo -e "${YELLOW}⚠ Vault ya está inicializado${NC}"
    else
        echo "Inicializando Vault..."
        vault operator init -key-shares=5 -key-threshold=3 > /tmp/vault-init.txt
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Vault inicializado${NC}"
            echo -e "${YELLOW}⚠ IMPORTANTE: Guarda las claves de sellado y el token root:${NC}"
            cat /tmp/vault-init.txt
            echo ""
            echo -e "${RED}CRÍTICO: Guarda estas claves en un lugar seguro y luego elimina /tmp/vault-init.txt${NC}"
        else
            echo -e "${RED}✗ Error inicializando Vault${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Error: Vault no está ejecutándose${NC}"
    systemctl status vault --no-pager
fi

echo ""
echo "6. CONFIGURACIÓN DE APPROL..."
echo "---------------------------"

# Script para configurar AppRole después de la inicialización manual
cat > /tmp/configure-vault-approle.sh << 'EOF'
#!/bin/bash

# Este script debe ejecutarse DESPUÉS de haber desbloqueado Vault manualmente
# y configurado el token root

echo "Configurando AppRole para TuAppDeAccesorios..."

# Verificar que estamos autenticados
if ! vault auth -method=token &>/dev/null; then
    echo "Error: No estás autenticado en Vault"
    echo "Ejecuta: vault auth -method=token"
    echo "Y proporciona el token root"
    exit 1
fi

# Habilitar AppRole auth method
vault auth enable approle

# Crear política para la aplicación
vault policy write tuapp-policy - << 'POLICY'
# Política para TuAppDeAccesorios
path "secret/data/tuapp/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/tuapp/*" {
  capabilities = ["list"]
}
POLICY

# Crear rol AppRole
vault write auth/approle/role/tuapp \
    token_policies="tuapp-policy" \
    token_ttl=1h \
    token_max_ttl=4h \
    bind_secret_id=true

# Obtener Role ID
ROLE_ID=$(vault read -field=role_id auth/approle/role/tuapp/role-id)

# Generar Secret ID
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/tuapp/secret-id)

echo ""
echo "CONFIGURACIÓN COMPLETADA:"
echo "========================"
echo "Role ID: $ROLE_ID"
echo "Secret ID: $SECRET_ID"
echo ""
echo "Agrega estas variables a tu .env.prod:"
echo "VAULT_URL=http://127.0.0.1:8200"
echo "VAULT_ROLE_ID=$ROLE_ID"
echo "VAULT_SECRET_ID=$SECRET_ID"
echo ""
echo "Para inicializar secretos básicos, ejecuta:"
echo "python -c \"from backend.app.vault import init_vault_secrets; init_vault_secrets()\""
EOF

chmod +x /tmp/configure-vault-approle.sh

echo ""
echo "================================================================"
echo "CONFIGURACIÓN DE VAULT COMPLETADA"
echo "================================================================"
echo ""
echo -e "${GREEN}✓ Vault instalado y configurado${NC}"
echo -e "${GREEN}✓ Servicio systemd creado${NC}"
echo -e "${GREEN}✓ Vault inicializado (si no lo estaba antes)${NC}"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASOS MANUALES:${NC}"
echo "1. Si Vault fue inicializado, desbloquéalo con las claves:"
echo "   vault operator unseal [CLAVE_1]"
echo "   vault operator unseal [CLAVE_2]"
echo "   vault operator unseal [CLAVE_3]"
echo ""
echo "2. Autentícate con el token root:"
echo "   export VAULT_ADDR='http://127.0.0.1:8200'"
echo "   vault auth -method=token"
echo ""
echo "3. Configura AppRole:"
echo "   /tmp/configure-vault-approle.sh"
echo ""
echo "4. Habilita el motor de secretos KV v2:"
echo "   vault secrets enable -path=secret kv-v2"
echo ""
echo -e "${RED}SEGURIDAD IMPORTANTE:${NC}"
echo "- Elimina /tmp/vault-init.txt después de guardar las claves"
echo "- En producción, usar auto-unseal con KMS"
echo "- Habilitar TLS en la configuración"
echo "- Configurar backups regulares de los datos"