# Crypto Wallet Service

Сервис для генерации и управления ETH кошельками с использованием MPC (Multi-Party Computation) архитектуры и HD деривации.

## Архитектура

- **Django 5.2 LTS + DRF** - основной API сервис
- **3 MPC ноды** - распределенная генерация и подпись ключей (2 из 3 консенсус)
- **HD деривация** - иерархическая детерминированная генерация кошельков из мастер ключа
- **Infura testnet** - подключение к Ethereum Sepolia testnet

## Требования

- Python 3.12
- Docker и Docker Compose
- Infura API ключ (для testnet)

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repo-url>
cd crypto-wallets
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Конфигурация

Создайте `.env` файл на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
API_SECRET_KEY=your_secret_api_key
INFURA_API_KEY=your_infura_api_key
INFURA_NETWORK=sepolia
MPC_NODE_1_URL=http://localhost:8001
MPC_NODE_2_URL=http://localhost:8002
MPC_NODE_3_URL=http://localhost:8003
DJANGO_SECRET_KEY=your_django_secret_key
```

### 3. Запуск MPC нод

```bash
docker-compose up -d
```

Проверка состояния нод:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### 4. Запуск Django сервиса

```bash
python manage.py migrate
python manage.py createsuperuser  # опционально
python manage.py runserver 8000
```

## API Документация

### Аутентификация

Все запросы требуют заголовок `X-API-Key` с SHA256 хешем вашего API ключа:

```bash
API_KEY="your_secret_api_key"
```

### Эндпоинты

#### 1. Создать новый кошелек

**POST** `/api/wallet/create`

Создает новый ETH кошелек через MPC ноды с автоматической HD деривацией.

**Request:**

```bash
curl -X POST http://localhost:8000/api/wallet/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_api_key" \
  -d '{}'
```

С указанием HD пути:

```bash
curl -X POST http://localhost:8000/api/wallet/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_api_key" \
  -d '{
    "hd_path": "m/44'\'''/60'\'''/0'\'''/0/5"
  }'
```

**Response (201):**

```json
{
  "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "hd_path": "m/44'/60'/0'/0/0",
  "created_at": "2025-12-25T17:00:00Z"
}
```

#### 2. Подписать транзакцию

**POST** `/api/wallet/sign`

Подписывает транзакцию от имени существующего кошелька через MPC ноды.

**Request:**

```bash
curl -X POST http://localhost:8000/api/wallet/sign \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_api_key" \
  -d '{
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "to": "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
    "amount": "0.01"
  }'
```

**Response (200):**

```json
{
  "signature": "0x1234567890abcdef...",
  "tx_hash": "0xabcdef1234567890...",
  "raw_transaction": "{'nonce': 0, 'to': '0x8626...', ...}"
}
```

**Errors:**

- `404` - Кошелек не найден
- `400` - Неверный формат данных
- `503` - Не удалось подключиться к Ethereum сети

#### 3. Список кошельков

**GET** `/api/wallets`

Возвращает список всех созданных кошельков.

**Request:**

```bash
curl -X GET http://localhost:8000/api/wallets \
  -H "X-API-Key: your_secret_api_key"
```

**Response (200):**

```json
[
  {
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "hd_path": "m/44'/60'/0'/0/0",
    "created_at": "2025-12-25T17:00:00Z"
  },
  {
    "address": "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
    "hd_path": "m/44'/60'/0'/0/1",
    "created_at": "2025-12-25T17:05:00Z"
  }
]
```

## MPC Ноды

### Архитектура

Мнемоник разделен на 3 шарда по 8 слов:
- **Node 1**: слова 1-8
- **Node 2**: слова 9-16
- **Node 3**: слова 17-24

Для генерации кошелька или подписи транзакции нужны **ВСЕ 3 ноды** (схема 3-of-3).

### Эндпоинты нод

#### Генерация кошелька

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "hd_path": "m/44'\'''/60'\'''/0'\'''/0/0"
  }'
```

#### Подпись транзакции

```bash
curl -X POST http://localhost:8001/sign \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "to": "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
    "amount": "0.01"
  }'
```

## Интеграционный тест

### Скрипт полного теста

Создайте файл `test_integration.py`:

```python
#!/usr/bin/env python
"""
Интеграционный тест:
1. Создать новый кошелек
2. Подписать транзакцию на testnet
"""

import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "your_secret_api_key"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def test_create_wallet():
    print("1. Создание нового кошелька...")
    response = requests.post(
        f"{BASE_URL}/api/wallet/create",
        headers=headers,
        json={}
    )
    
    assert response.status_code == 201, f"Failed: {response.text}"
    wallet = response.json()
    
    print(f"   Адрес: {wallet['address']}")
    print(f"   HD путь: {wallet['hd_path']}")
    
    return wallet['address']

def test_sign_transaction(wallet_address):
    print("\n2. Подпись транзакции...")
    response = requests.post(
        f"{BASE_URL}/api/wallet/sign",
        headers=headers,
        json={
            "address": wallet_address,
            "to": "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
            "amount": "0.001"
        }
    )
    
    assert response.status_code == 200, f"Failed: {response.text}"
    result = response.json()
    
    print(f"   Подпись: {result['signature'][:20]}...")
    print(f"   TX Hash: {result['tx_hash']}")
    
    return result

def test_list_wallets():
    print("\n3. Список всех кошельков...")
    response = requests.get(
        f"{BASE_URL}/api/wallets",
        headers=headers
    )
    
    assert response.status_code == 200, f"Failed: {response.text}"
    wallets = response.json()
    
    print(f"   Всего кошельков: {len(wallets)}")
    for wallet in wallets:
        print(f"   - {wallet['address']}")
    
    return wallets

if __name__ == "__main__":
    print("Запуск интеграционного теста...\n")
    print("=" * 60)
    
    try:
        wallet_address = test_create_wallet()
        time.sleep(1)
        
        sign_result = test_sign_transaction(wallet_address)
        time.sleep(1)
        
        wallets = test_list_wallets()
        
        print("\n" + "=" * 60)
        print("Все тесты пройдены успешно")
        
    except AssertionError as e:
        print(f"\nОшибка теста: {e}")
    except Exception as e:
        print(f"\nНепредвиденная ошибка: {e}")
```

### Запуск теста

```bash
# Убедитесь что все сервисы запущены
docker-compose ps
python manage.py runserver 8000  # в отдельном терминале

# Запустите тест
python test_integration.py
```

### Ожидаемый вывод

```
Запуск интеграционного теста...

============================================================
1. Создание нового кошелька...
   Адрес: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
   HD путь: m/44'/60'/0'/0/0

2. Подпись транзакции...
   Подпись: 0x1234567890abcdef...
   TX Hash: 0xabcdef1234567890...

3. Список всех кошельков...
   Всего кошельков: 1
   - 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

============================================================
Все тесты пройдены успешно
```

## Структура проекта

```
crypto-wallets/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── crypto_wallet_service/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── wallet_api/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── authentication.py
│   └── mpc_client.py
└── mpc-node/
    ├── app.py
    ├── requirements.txt
    ├── Dockerfile
    └── .dockerignore
```

## Безопасность

- Приватные ключи хранятся только в MPC нодах
- API аутентификация через SHA256
- Консенсус 2 из 3 нод для любой операции
- SSH доступ с уникальными паролями для каждой ноды
- В продакшене используйте HTTPS и переменные окружения для секретов

**⚠️ Особенности реализации:**

Текущая реализация - **MPC с разделением мнемоника (3 из 3)**:
- Каждая нода хранит ТОЛЬКО СВОЙ шард (8 слов из 24)
- Доступ к 1 ноде = бесполезно (нужны все 3)
- Для генерации/подписи ноды запрашивают шарды друг у друга
- Если 1 нода упала - сервис не работает
- Для threshold 2-of-3 нужен Shamir Secret Sharing или TSS

## Разработка

### Миграции базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### Админ панель

```bash
python manage.py createsuperuser
# Доступ: http://localhost:8000/admin
```

### Логи MPC нод

```bash
docker-compose logs -f mpc-node-1
docker-compose logs -f mpc-node-2
docker-compose logs -f mpc-node-3
```

## Troubleshooting

### MPC ноды не отвечают

```bash
docker-compose restart
docker-compose ps
```

### Ошибка "MASTER_SEED not found"

Все 3 ноды требуют один общий мнемоник:

```bash
# Сгенерируйте новый
python -c "from mnemonic import Mnemonic; print(Mnemonic('english').generate())"

# Добавьте в .env
MASTER_SEED=your 24 word mnemonic here

# Пересоздайте ноды
docker-compose down
rm -rf data/
docker-compose up -d
```

### Ошибка подключения к Infura

Проверьте API ключ и сеть в `.env`:

```bash
curl "https://sepolia.infura.io/v3/YOUR_API_KEY" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### База данных заблокирована

```bash
rm db.sqlite3
python manage.py migrate
```

## Лицензия

MIT
