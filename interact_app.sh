#!/bin/bash

echo "🎮 INTERACCIÓN RÁPIDA CON TuAppDeAccesorios"
echo "==========================================="
echo ""

# Función para obtener token
get_token() {
    curl -s -X POST "http://localhost:8000/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=admin&password=admin123" | jq -r .access_token
}

# Función para listar productos
list_products() {
    echo "📦 PRODUCTOS ACTUALES:"
    curl -s http://localhost:8000/products/ | jq '.products[] | {id: .id, sku: .sku, nombre: .name, precio: .selling_price, stock: .stock_quantity}'
    echo ""
}

# Función para crear producto
create_product() {
    TOKEN=$(get_token)
    echo "➕ CREANDO PRODUCTO: $1"
    curl -s -X POST "http://localhost:8000/products/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"sku\": \"$2\",
        \"name\": \"$1\",
        \"description\": \"Producto creado interactivamente\",
        \"cost_price\": $3,
        \"selling_price\": $4,
        \"stock_quantity\": $5
      }" | jq .
    echo ""
}

# Función para buscar producto
get_product() {
    echo "🔍 BUSCANDO PRODUCTO ID: $1"
    curl -s http://localhost:8000/products/$1 | jq .
    echo ""
}

# Función para ver salud del sistema
health_check() {
    echo "🏥 ESTADO DEL SISTEMA:"
    curl -s http://localhost:8000/health | jq .status
    echo ""
}

# Menu interactivo
while true; do
    echo "Selecciona una opción:"
    echo "1. 📦 Listar productos"
    echo "2. ➕ Crear producto"
    echo "3. 🔍 Buscar producto por ID"
    echo "4. 🏥 Ver estado del sistema"
    echo "5. 🌐 Abrir aplicación web"
    echo "6. 📚 Abrir documentación API"
    echo "7. 🚪 Salir"
    echo ""
    read -p "Opción (1-7): " choice

    case $choice in
        1)
            list_products
            ;;
        2)
            read -p "Nombre del producto: " name
            read -p "SKU: " sku
            read -p "Precio de costo: " cost
            read -p "Precio de venta: " price
            read -p "Stock inicial: " stock
            create_product "$name" "$sku" "$cost" "$price" "$stock"
            ;;
        3)
            read -p "ID del producto: " id
            get_product "$id"
            ;;
        4)
            health_check
            ;;
        5)
            echo "🌐 Abriendo aplicación web..."
            open http://localhost:3001 2>/dev/null || echo "Visita: http://localhost:3001"
            ;;
        6)
            echo "📚 Abriendo documentación API..."
            open http://localhost:8000/docs 2>/dev/null || echo "Visita: http://localhost:8000/docs"
            ;;
        7)
            echo "👋 ¡Hasta luego!"
            exit 0
            ;;
        *)
            echo "❌ Opción inválida"
            ;;
    esac
    echo ""
done