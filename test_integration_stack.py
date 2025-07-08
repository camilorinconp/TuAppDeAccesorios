#!/usr/bin/env python3
"""
Script para probar la integración completa del stack
"""
import requests
import psycopg2
import redis
import json
import sys

def test_postgresql():
    """Probar conexión PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="tuapp_db",
            user="tuapp_user",
            password="TjsgqypkqFJ1xS2024"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✅ PostgreSQL: {count} usuarios encontrados")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        return False

def test_redis():
    """Probar conexión Redis"""
    try:
        # Probar conexión con URL completa
        r = redis.from_url('redis://:UwWHHhZehbZg5h2024@localhost:6379/0', decode_responses=True)
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        r.delete('test_key')
        
        if value == 'test_value':
            print("✅ Redis: Funcionando correctamente")
            return True
        else:
            print("❌ Redis: Error en operaciones")
            return False
    except Exception as e:
        print(f"❌ Redis: {e}")
        return False

def test_backend():
    """Probar backend API"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend: API funcionando")
            return True
        else:
            print(f"❌ Backend: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend: {e}")
        return False

def test_frontend():
    """Probar frontend"""
    try:
        response = requests.get("http://localhost:3001", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend: Aplicación funcionando")
            return True
        else:
            print(f"❌ Frontend: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend: {e}")
        return False

def test_authentication():
    """Probar autenticación"""
    try:
        # Login
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        response = requests.post(
            "http://localhost:8000/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if access_token:
                # Probar endpoint protegido
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get("http://localhost:8000/verify", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    print("✅ Autenticación: Login y verificación funcionando")
                    return True
                else:
                    print(f"❌ Autenticación: Error verificando token ({response.status_code})")
                    return False
            else:
                print("❌ Autenticación: No se recibió access_token")
                return False
        else:
            print(f"❌ Autenticación: Error en login ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Autenticación: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Probando integración completa del stack")
    print("=" * 50)
    
    tests = [
        ("PostgreSQL", test_postgresql),
        ("Redis", test_redis),
        ("Backend API", test_backend),
        ("Frontend", test_frontend),
        ("Autenticación", test_authentication)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🔍 Probando {name}...")
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:15} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El stack está funcionando correctamente.")
        return 0
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa la configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())