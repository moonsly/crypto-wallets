#!/usr/bin/env python
"""
Интеграционный тест:
1. Создать новый кошелек через MPC ноды
2. Подписать транзакцию на Ethereum testnet (Sepolia)
3. Проверить список кошельков
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "your_secret_api_key"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}


def check_mpc_nodes():
    """Проверка доступности MPC нод"""
    print("0. Проверка MPC нод...")
    
    nodes = [
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003"
    ]
    
    available_nodes = 0
    for node_url in nodes:
        try:
            response = requests.get(f"{node_url}/health", timeout=2)
            if response.status_code == 200:
                node_data = response.json()
                print(f"   Node {node_data['node_id']}: OK")
                available_nodes += 1
            else:
                print(f"   {node_url}: FAILED")
        except Exception as e:
            print(f"   {node_url}: UNAVAILABLE - {e}")
    
    if available_nodes < 2:
        print(f"\n   Ошибка: Нужно минимум 2 из 3 нод. Доступно: {available_nodes}")
        print("   Запустите ноды: docker-compose up -d")
        sys.exit(1)
    
    print(f"   Доступно {available_nodes}/3 нод (требуется минимум 2)")


def test_create_wallet():
    """Тест 1: Создание нового кошелька"""
    print("\n1. Создание нового кошелька...")
    
    response = requests.post(
        f"{BASE_URL}/api/wallet/create",
        headers=headers,
        json={}
    )
    
    if response.status_code != 201:
        print(f"   Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text}")
        sys.exit(1)
    
    wallet = response.json()
    
    print(f"   Адрес: {wallet['address']}")
    print(f"   HD путь: {wallet['hd_path']}")
    print(f"   Создан: {wallet['created_at']}")
    
    return wallet['address']


def test_sign_transaction(wallet_address):
    """Тест 2: Подпись транзакции"""
    print("\n2. Подпись транзакции...")
    
    test_recipient = "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199"
    test_amount = "0.001"
    
    print(f"   От: {wallet_address}")
    print(f"   Кому: {test_recipient}")
    print(f"   Сумма: {test_amount} ETH")
    
    response = requests.post(
        f"{BASE_URL}/api/wallet/sign",
        headers=headers,
        json={
            "address": wallet_address,
            "to": test_recipient,
            "amount": test_amount
        }
    )
    
    if response.status_code != 200:
        print(f"   Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text}")
        sys.exit(1)
    
    result = response.json()
    
    print(f"   Подпись: {result['signature'][:30]}...")
    print(f"   TX Hash: {result['tx_hash']}")
    
    return result


def test_list_wallets():
    """Тест 3: Список всех кошельков"""
    print("\n3. Список всех кошельков...")
    
    response = requests.get(
        f"{BASE_URL}/api/wallets",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"   Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text}")
        sys.exit(1)
    
    wallets = response.json()
    
    print(f"   Всего кошельков: {len(wallets)}")
    for wallet in wallets:
        print(f"   - {wallet['address']} ({wallet['hd_path']})")
    
    return wallets


def test_create_wallet_with_custom_path():
    """Тест 4: Создание кошелька с пользовательским HD путем"""
    print("\n4. Создание кошелька с пользовательским HD путем...")
    
    custom_path = "m/44'/60'/0'/0/999"
    
    response = requests.post(
        f"{BASE_URL}/api/wallet/create",
        headers=headers,
        json={"hd_path": custom_path}
    )
    
    if response.status_code != 201:
        print(f"   Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text}")
        sys.exit(1)
    
    wallet = response.json()
    
    print(f"   Адрес: {wallet['address']}")
    print(f"   HD путь: {wallet['hd_path']}")
    
    assert wallet['hd_path'] == custom_path, "HD путь не совпадает"
    
    return wallet


def test_invalid_wallet():
    """Тест 5: Попытка подписи с несуществующим кошельком"""
    print("\n5. Тест обработки ошибок (несуществующий кошелек)...")
    
    fake_address = "0x0000000000000000000000000000000000000000"
    
    response = requests.post(
        f"{BASE_URL}/api/wallet/sign",
        headers=headers,
        json={
            "address": fake_address,
            "to": "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
            "amount": "0.001"
        }
    )
    
    if response.status_code == 404:
        print(f"   Ожидаемая ошибка 404: Кошелек не найден")
    else:
        print(f"   Неожиданный ответ: {response.status_code}")
        print(f"   {response.text}")


if __name__ == "__main__":
    print("=" * 70)
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ CRYPTO WALLET SERVICE")
    print("=" * 70)
    
    try:
        check_mpc_nodes()
        
        wallet_address = test_create_wallet()
        time.sleep(1)
        
        sign_result = test_sign_transaction(wallet_address)
        time.sleep(1)
        
        wallets = test_list_wallets()
        time.sleep(1)
        
        custom_wallet = test_create_wallet_with_custom_path()
        time.sleep(1)
        
        test_invalid_wallet()
        
        print("\n" + "=" * 70)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 70)
        
        print("\nИтоги:")
        print(f"  - Создано кошельков: 2")
        print(f"  - Подписано транзакций: 1")
        print(f"  - Всего кошельков в системе: {len(wallets) + 1}")
        
    except requests.exceptions.ConnectionError:
        print("\nОшибка подключения!")
        print("Убедитесь что сервер запущен: python manage.py runserver 8000")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nНепредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
