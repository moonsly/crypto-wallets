# История разработки проекта Crypto Wallet Service

## Описание проекта

Сервис для генерации и управления ETH кошельками с использованием MPC (Multi-Party Computation) архитектуры и HD деривации.

**Архитектура:**
- Django 5.2 LTS + DRF - основной API сервис
- 3 MPC ноды (Flask) - распределенное хранение шардов мнемоника
- Разделение мнемоника: 24 слова → 3 шарда по 8 слов (схема 3-of-3)
- Infura testnet (Sepolia) - подключение к Ethereum

## Созданные файлы

### Корень проекта
- `requirements.txt` - Django 5.2, DRF, web3, eth-account, hdwallet
- `.env.example` - шаблон конфигурации
- `.gitignore` - исключения для git
- `docker-compose.yml` - 3 MPC ноды с SSH
- `manage.py` - Django management
- `prepare_shards.sh` - скрипт разделения мнемоника на шарды
- `split_mnemonic.py` - утилита для ручного разделения (опционально)
- `test_integration.py` - интеграционные тесты
- `README.md` - полная документация

### Django проект: crypto_wallet_service/
- `__init__.py`
- `settings.py` - настройки Django + кастомные (API_SECRET_KEY, INFURA, MPC nodes, REQUEST_EXPIRY_SECONDS, REQUIRE_REQUEST_SIGNATURE)
- `urls.py` - роутинг на wallet_api
- `asgi.py`
- `wsgi.py`

### Django app: wallet_api/
- `__init__.py`
- `apps.py`
- `models.py` - Wallet, UsedNonce
- `admin.py` - админка для Wallet и UsedNonce
- `authentication.py` - SHA256Authentication с поддержкой подписи (отключаемой)
- `serializers.py` - WalletSerializer, CreateWalletSerializer, SignTransactionSerializer
- `serializers_bulk.py` - BulkSendSerializer для массовых отправок
- `views.py` - CreateWalletView, SignTransactionView, WalletListView, BulkSendView
- `urls.py` - роуты API
- `mpc_client.py` - клиент для взаимодействия с MPC нодами

### MPC node: mpc-node/
- `requirements.txt` - flask, web3, eth-account, hdwallet
- `app.py` - Flask приложение с эндпоинтами /health, /get_shard, /generate, /sign
- `Dockerfile` - Python 3.12 + SSH сервер
- `entrypoint.sh` - запуск SSH и Flask
- `.dockerignore`

## Ключевые решения и правки

### 1. Изначальная архитектура (FastAPI → Django)
**Проблема:** Начали с FastAPI, потом переделали на Django 5.2 LTS + DRF по требованию.

**Решение:**
- Переписали на Django с полной поддержкой DRF
- Использовали SQLite для простоты MVP

### 2. MPC и разделение мнемоника
**Проблема:** Сначала все 3 ноды хранили ПОЛНЫЙ мнемоник - это псевдо-MPC без реальной защиты.

**Решение:**
- Разделили 24-словный мнемоник на 3 шарда по 8 слов
- Node 1: слова 1-8
- Node 2: слова 9-16  
- Node 3: слова 17-24
- Для генерации/подписи ноды запрашивают шарды друг у друга через `/get_shard`
- Требуются ВСЕ 3 ноды (схема 3-of-3)

**Файлы:**
- `prepare_shards.sh` - автоматически делит MASTER_SEED из .env на шарды
- `mpc-node/app.py` - функции `get_node_shard()`, `combine_shards()`, `derive_wallet_from_full_mnemonic()`

### 3. SSH доступ к нодам
**Проблема:** Нужен раздельный доступ к каждой ноде для разных администраторов.

**Решение:**
- Добавили SSH сервер в каждую Docker ноду
- Уникальные пароли из .env: MPC_NODE_1_SSH_PASSWORD, etc.
- Порты: 2221, 2222, 2223
- Пользователь: mpcadmin (с sudo)

**Файлы:**
- `mpc-node/Dockerfile` - установка openssh-server
- `mpc-node/entrypoint.sh` - установка пароля и запуск sshd
- `docker-compose.yml` - проброс портов SSH

### 4. Защита от replay атак
**Проблема:** Если утечет API_SECRET_KEY, злоумышленник может повторять перехваченные запросы.

**Решение:**
- Расширенная аутентификация: SHA256(key + timestamp + nonce + body)
- Заголовки: X-API-Key, X-Signature, X-Timestamp, X-Nonce
- Проверка timestamp: протухает через REQUEST_EXPIRY_SECONDS (300 сек)
- Проверка nonce: каждый используется только 1 раз (хранится в БД)
- Отключаемая через REQUIRE_REQUEST_SIGNATURE=False (для тестирования)

**Файлы:**
- `wallet_api/authentication.py` - класс SHA256Authentication
- `wallet_api/models.py` - модель UsedNonce с cleanup_old_nonces()
- `.env.example` - REQUIRE_REQUEST_SIGNATURE, REQUEST_EXPIRY_SECONDS

### 5. API эндпоинты

#### POST /api/wallet/create
Создает новый ETH кошелек через HD деривацию, запрашивая шарды у всех 3 нод.

#### POST /api/wallet/sign
Подписывает транзакцию от имени существующего кошелька.

#### GET /api/wallets
Возвращает список всех созданных кошельков.

#### POST /api/wallet/bulk-send
**Добавлен позже** - массовая отправка ETH с мастер кошелька (m/44'/60'/0'/0/0).
- Параметры: eth_wallets (csv), amount
- Проверка баланса ПЕРЕД отправкой
- Если не хватает → 500 статус с деталями

**Файлы:**
- `wallet_api/views.py` - все view классы
- `wallet_api/serializers_bulk.py` - сериализаторы для bulk-send

### 6. Конфигурация через .env

```env
API_SECRET_KEY=your_secret_key_here
INFURA_API_KEY=your_infura_api_key_here
INFURA_NETWORK=sepolia
REQUEST_EXPIRY_SECONDS=300
REQUIRE_REQUEST_SIGNATURE=False

# Мастер мнемоник - автоматически делится на шарды
MASTER_SEED=abandon abandon abandon ... (24 words)

# SSH пароли для каждой ноды
MPC_NODE_1_SSH_PASSWORD=pass1
MPC_NODE_2_SSH_PASSWORD=pass2
MPC_NODE_3_SSH_PASSWORD=pass3
```

После настройки запустить:
```bash
./prepare_shards.sh
```

Это создаст в .env:
```env
MPC_NODE_1_SHARD="word1 word2 ... word8"
MPC_NODE_2_SHARD="word9 word10 ... word16"
MPC_NODE_3_SHARD="word17 word18 ... word24"
```

## Workflow запуска

1. Установить зависимости:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Настроить .env:
```bash
cp .env.example .env
# Отредактировать .env
```

3. Сгенерировать мнемоник (24 слова):
```bash
pip install mnemonic
python -c "from mnemonic import Mnemonic; print(Mnemonic('english').generate(strength=256))"
```

4. Разделить на шарды:
```bash
./prepare_shards.sh
```

5. Запустить MPC ноды:
```bash
docker-compose up -d
docker-compose ps
curl http://localhost:8001/health
```

6. Миграции и запуск Django:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 8000
```

7. Тестирование:
```bash
python test_integration.py
```

## Известные ограничения

1. **Схема 3-of-3** - если 1 нода упала, сервис не работает. Для threshold 2-of-3 нужен Shamir Secret Sharing или TSS.

2. **Открытые порты API нод** - сейчас 8001-8003 доступны извне. Для продакшена нужно закрыть и оставить только SSH.

3. **SQLite** - для продакшена нужна PostgreSQL.

4. **Нет автоотправки транзакций** - /wallet/sign только подписывает, не отправляет в сеть.

5. **Простая авторизация** - для продакшена включить REQUIRE_REQUEST_SIGNATURE=True.

## Безопасность

- Каждая нода хранит только 8 слов из 24 (бесполезно без других)
- SSH изоляция с разными паролями
- Защита от replay атак через nonce + timestamp
- Приватные ключи не хранятся в главном API, только в MPC нодах
- `.env` в `.gitignore`

## Структура файлов

```
crypto-wallets/
├── manage.py
├── requirements.txt
├── .env.example
├── .env (создается пользователем)
├── .gitignore
├── docker-compose.yml
├── prepare_shards.sh
├── split_mnemonic.py
├── test_integration.py
├── README.md
├── WARP.md (этот файл)
├── crypto_wallet_service/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── wallet_api/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py (Wallet, UsedNonce)
│   ├── admin.py
│   ├── authentication.py (SHA256Authentication)
│   ├── serializers.py
│   ├── serializers_bulk.py
│   ├── views.py (4 эндпоинта)
│   ├── urls.py
│   └── mpc_client.py
├── mpc-node/
│   ├── app.py (Flask)
│   ├── requirements.txt
│   ├── Dockerfile (Python 3.12 + SSH)
│   ├── entrypoint.sh
│   └── .dockerignore
└── data/ (создается Docker volumes)
    ├── node1/
    ├── node2/
    └── node3/
```

## Что можно улучшить

1. **Threshold 2-of-3** - Shamir Secret Sharing
2. **Закрыть API порты нод** - оставить только SSH
3. **PostgreSQL** вместо SQLite
4. **Celery** для асинхронной обработки транзакций
5. **Мониторинг** - Prometheus + Grafana
6. **Rate limiting** - для защиты от DDoS
7. **Логирование** - структурированные логи
8. **CI/CD** - автоматическое тестирование и деплой

## Контакты и версии

- Python: 3.12
- Django: 5.2
- DRF: 3.15.2
- Web3: 6.11.3
- Flask: 3.0.0 (MPC ноды)
- Docker Compose: 3.8

---

**Дата создания:** 2025-12-25  
**Статус:** MVP готов к тестированию  
**Автор:** AI Assistant (джун режим) + zak
