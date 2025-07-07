#!/bin/bash

# Script para configurar pre-commit hooks
echo "🔧 CONFIGURACIÓN DE PRE-COMMIT HOOKS"
echo "===================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verificar que estamos en el directorio correcto
if [ ! -f "package.json" ] && [ ! -f "backend/requirements.txt" ]; then
    echo -e "${RED}Error: Este script debe ejecutarse desde el directorio raíz del proyecto${NC}"
    exit 1
fi

echo "1. INSTALANDO PRE-COMMIT..."
echo "-------------------------"

# Verificar si pre-commit está instalado
if ! command -v pre-commit &> /dev/null; then
    echo "Instalando pre-commit..."
    pip install pre-commit
    echo -e "${GREEN}✓ Pre-commit instalado${NC}"
else
    echo -e "${GREEN}✓ Pre-commit ya está instalado${NC}"
fi

echo ""
echo "2. INSTALANDO DEPENDENCIAS PYTHON..."
echo "----------------------------------"

# Instalar dependencias de formateo para Python
pip install black isort flake8 mypy bandit
pip install flake8-docstrings flake8-bugbear flake8-comprehensions
echo -e "${GREEN}✓ Dependencias Python instaladas${NC}"

echo ""
echo "3. INSTALANDO DEPENDENCIAS FRONTEND..."
echo "------------------------------------"

# Navegar al frontend e instalar dependencias
if [ -d "frontend" ]; then
    cd frontend
    
    # Verificar si npm está disponible
    if command -v npm &> /dev/null; then
        echo "Instalando dependencias de ESLint y Prettier..."
        npm install --save-dev \
            eslint \
            prettier \
            @typescript-eslint/eslint-plugin \
            @typescript-eslint/parser \
            eslint-config-prettier \
            eslint-plugin-prettier \
            eslint-plugin-react \
            eslint-plugin-react-hooks
        echo -e "${GREEN}✓ Dependencias del frontend instaladas${NC}"
    else
        echo -e "${YELLOW}⚠ npm no está disponible, saltando dependencias del frontend${NC}"
    fi
    
    cd ..
else
    echo -e "${YELLOW}⚠ Directorio frontend no encontrado${NC}"
fi

echo ""
echo "4. CONFIGURANDO GIT HOOKS..."
echo "--------------------------"

# Instalar hooks de pre-commit
pre-commit install
pre-commit install --hook-type commit-msg

echo -e "${GREEN}✓ Hooks de Git configurados${NC}"

echo ""
echo "5. CONFIGURANDO BASELINE DE SECRETOS..."
echo "-------------------------------------"

# Crear baseline para detect-secrets
if command -v detect-secrets &> /dev/null; then
    detect-secrets scan --baseline .secrets.baseline
    echo -e "${GREEN}✓ Baseline de secretos creado${NC}"
else
    pip install detect-secrets
    detect-secrets scan --baseline .secrets.baseline
    echo -e "${GREEN}✓ detect-secrets instalado y baseline creado${NC}"
fi

echo ""
echo "6. CONFIGURANDO COMMITIZEN..."
echo "---------------------------"

# Instalar commitizen para mensajes de commit estandarizados
pip install commitizen

# Crear configuración de commitizen
cat > .cz.yaml << 'EOF'
commitizen:
  name: cz_conventional_commits
  version: 1.0.0
  tag_format: v$major.$minor.$patch
  version_files:
    - backend/app/__init__.py
    - frontend/package.json:version
  style:
    - path: cz_conventional_commits/cz_conventional_commits.py
  customize:
    message_template: "{{change_type}}{% if scope %}({{scope}}){% endif %}: {{message}}{% if body %}\n\n{{body}}{% endif %}{% if footer %}\n\n{{footer}}{% endif %}"
    example: "feat(auth): add OAuth2 integration\n\nImplemented OAuth2 authentication with Google and GitHub providers.\n\nCloses #123"
    schema: "<type>(<scope>): <subject>\n\n<body>\n\n<footer>"
    bump_pattern: "^(feat|fix|perf|refactor).*"
    bump_map:
      feat: MINOR
      fix: PATCH
      perf: PATCH
      refactor: PATCH
    change_type_order:
      - feat
      - fix
      - refactor
      - perf
      - style
      - test
      - build
      - ci
      - docs
      - chore
EOF

echo -e "${GREEN}✓ Commitizen configurado${NC}"

echo ""
echo "7. EJECUTANDO PRIMERA VERIFICACIÓN..."
echo "-----------------------------------"

# Ejecutar pre-commit en todos los archivos para verificar configuración
echo "Ejecutando pre-commit en todos los archivos (esto puede tomar unos minutos)..."
pre-commit run --all-files

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Verificación exitosa${NC}"
else
    echo -e "${YELLOW}⚠ Algunos hooks fallaron, pero esto es normal en la primera ejecución${NC}"
    echo "Los hooks han formateado automáticamente los archivos necesarios."
fi

echo ""
echo "8. CREANDO SCRIPTS DE UTILIDAD..."
echo "-------------------------------"

# Script para ejecutar formateo manual
cat > scripts/format-code.sh << 'SCRIPT'
#!/bin/bash

# Script para formatear código manualmente
echo "🎨 FORMATEANDO CÓDIGO"
echo "==================="

echo "Formateando Python..."
cd backend
black .
isort .
cd ..

echo "Formateando TypeScript/JavaScript..."
cd frontend
if command -v npm &> /dev/null; then
    npm run prettier:fix 2>/dev/null || npx prettier --write "src/**/*.{ts,tsx,js,jsx,css,md}"
fi
cd ..

echo "✓ Formateo completado"
SCRIPT

chmod +x scripts/format-code.sh

# Script para verificar código
cat > scripts/lint-code.sh << 'SCRIPT'
#!/bin/bash

# Script para verificar calidad de código
echo "🔍 VERIFICANDO CALIDAD DE CÓDIGO"
echo "==============================="

echo "Verificando Python..."
cd backend
flake8 .
mypy app/
bandit -r app/
cd ..

echo "Verificando TypeScript/JavaScript..."
cd frontend
if command -v npm &> /dev/null; then
    npm run lint 2>/dev/null || npx eslint "src/**/*.{ts,tsx,js,jsx}"
fi
cd ..

echo "✓ Verificación completada"
SCRIPT

chmod +x scripts/lint-code.sh

echo -e "${GREEN}✓ Scripts de utilidad creados${NC}"

echo ""
echo "================================================================"
echo "PRE-COMMIT HOOKS CONFIGURADOS EXITOSAMENTE"
echo "================================================================"
echo ""
echo -e "${GREEN}✓ Pre-commit instalado y configurado${NC}"
echo -e "${GREEN}✓ Hooks de Git activados${NC}"
echo -e "${GREEN}✓ Dependencias de formateo instaladas${NC}"
echo -e "${GREEN}✓ Baseline de secretos configurado${NC}"
echo -e "${GREEN}✓ Commitizen configurado${NC}"
echo ""
echo -e "${BLUE}FUNCIONALIDADES ACTIVADAS:${NC}"
echo "• Formateo automático de código Python (Black, isort)"
echo "• Linting de Python (flake8, mypy, bandit)"
echo "• Formateo de JavaScript/TypeScript (Prettier)"
echo "• Linting de JavaScript/TypeScript (ESLint)"
echo "• Verificación de archivos YAML/JSON"
echo "• Detección de secretos hardcodeados"
echo "• Linting de Dockerfiles"
echo "• Verificación de mensajes de commit"
echo ""
echo -e "${BLUE}COMANDOS ÚTILES:${NC}"
echo "• \`pre-commit run --all-files\` - Ejecutar todos los hooks"
echo "• \`./scripts/format-code.sh\` - Formatear código manualmente"
echo "• \`./scripts/lint-code.sh\` - Verificar calidad de código"
echo "• \`cz commit\` - Crear commit con formato estándar"
echo "• \`pre-commit autoupdate\` - Actualizar versiones de hooks"
echo ""
echo -e "${YELLOW}IMPORTANTE:${NC}"
echo "• Los hooks se ejecutarán automáticamente antes de cada commit"
echo "• Si un hook falla, el commit será rechazado"
echo "• Algunos hooks pueden formatear archivos automáticamente"
echo "• Revisa los cambios antes de hacer commit nuevamente"
echo ""
echo -e "${GREEN}¡Configuración completa! El código ahora se formateará automáticamente.${NC}"