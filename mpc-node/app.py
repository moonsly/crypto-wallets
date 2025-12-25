import os
import json
import hashlib
from flask import Flask, request, jsonify
from hdwallet import HDWallet
from hdwallet.symbols import ETH
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import requests

app = Flask(__name__)

NODE_ID = os.getenv('NODE_ID', '1')
NODE_PORT = int(os.getenv('NODE_PORT', '8001'))
PEER_NODES = os.getenv('PEER_NODES', '').split(',') if os.getenv('PEER_NODES') else []

DATA_DIR = '/app/data'
os.makedirs(DATA_DIR, exist_ok=True)

MASTER_SEED_FILE = os.path.join(DATA_DIR, 'master_seed.json')


def get_or_create_master_seed():
    """
    Получает или создает мастер сид для ноды.
    ВАЖНО: Все ноды должны использовать ОДИН И ТОТ ЖЕ мнемоник!
    В реальном MPC это был бы шард общего ключа.
    """
    # Проверяем переменную окружения
    env_seed = os.getenv('MASTER_SEED')
    if env_seed and env_seed.strip():
        print(f"Node {NODE_ID}: Using MASTER_SEED from environment")
        # Сохраняем в файл для последующего использования
        with open(MASTER_SEED_FILE, 'w') as f:
            json.dump({'seed': env_seed.strip(), 'node_id': NODE_ID, 'source': 'env'}, f)
        return env_seed.strip()
    
    # Проверяем существующий файл
    if os.path.exists(MASTER_SEED_FILE):
        with open(MASTER_SEED_FILE, 'r') as f:
            data = json.load(f)
            print(f"Node {NODE_ID}: Using existing master seed from file")
            return data['seed']
    
    # ОШИБКА: MASTER_SEED обязателен для MPC
    error_msg = (
        f"Node {NODE_ID}: MASTER_SEED not found!\n"
        "All MPC nodes MUST use the SAME master seed.\n"
        "Set MASTER_SEED in .env file before starting nodes."
    )
    print(error_msg)
    raise Exception(error_msg)


def derive_wallet_from_seed(seed: str, hd_path: str):
    """
    Деривация кошелька из мастер сида по HD пути
    """
    hdwallet = HDWallet(symbol=ETH)
    hdwallet.from_mnemonic(seed)
    hdwallet.from_path(hd_path)
    
    return {
        'address': hdwallet.p2pkh_address(),
        'private_key': hdwallet.private_key(),
        'public_key': hdwallet.public_key()
    }


def coordinate_with_peers(endpoint: str, payload: dict):
    """
    Координация с другими MPC нодами
    """
    responses = []
    for peer_url in PEER_NODES:
        if not peer_url.strip():
            continue
        try:
            response = requests.post(
                f"{peer_url.strip()}{endpoint}",
                json=payload,
                timeout=5
            )
            if response.status_code == 200:
                responses.append(response.json())
        except Exception as e:
            print(f"Failed to reach peer {peer_url}: {e}")
    
    return responses


@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья ноды"""
    return jsonify({
        'status': 'healthy',
        'node_id': NODE_ID,
        'port': NODE_PORT
    })


@app.route('/get_shard', methods=['GET'])
def get_shard():
    """
    Возвращает шард этой ноды для сборки полного мнемоника
    """
    try:
        shard = get_node_shard()
        return jsonify({
            'shard': shard,
            'node_id': NODE_ID
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate_wallet():
    """
    Генерация нового кошелька через HD деривацию.
    Собирает шарды от всех 3 нод для получения полного мнемоника.
    """
    try:
        data = request.get_json()
        hd_path = data.get('hd_path')
        
        if not hd_path:
            return jsonify({'error': 'hd_path is required'}), 400
        
        # Получаем свой шард
        my_shard = get_node_shard()
        
        # Собираем шарды от всех нод
        shards = {}
        shards[int(NODE_ID)] = my_shard
        
        # Запрашиваем шарды у peer нод
        for peer_url in PEER_NODES:
            if not peer_url.strip():
                continue
            try:
                response = requests.get(f"{peer_url.strip()}/get_shard", timeout=5)
                if response.status_code == 200:
                    peer_data = response.json()
                    shards[int(peer_data['node_id'])] = peer_data['shard']
            except Exception as e:
                print(f"Failed to get shard from {peer_url}: {e}")
        
        # Проверяем что получили все 3 шарда
        if len(shards) != 3:
            return jsonify({
                'error': f'Need all 3 shards, got {len(shards)}'
            }), 503
        
        # Собираем полный мнемоник в правильном порядке
        full_mnemonic = combine_shards(shards[1], shards[2], shards[3])
        
        # Генерируем кошелек
        wallet = derive_wallet_from_full_mnemonic(full_mnemonic, hd_path)
        
        return jsonify({
            'address': wallet['address'],
            'hd_path': hd_path,
            'node_id': NODE_ID
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/sign', methods=['POST'])
def sign_transaction():
    """
    Подпись транзакции.
    В упрощенной версии каждая нода подписывает своим шардом ключа.
    В реальном MPC это был бы threshold signature.
    """
    try:
        data = request.get_json()
        address = data.get('address')
        to_address = data.get('to')
        amount = data.get('amount')
        
        if not all([address, to_address, amount]):
            return jsonify({'error': 'address, to, and amount are required'}), 400
        
        wallet_db_file = os.path.join(DATA_DIR, 'wallets.json')
        
        if os.path.exists(wallet_db_file):
            with open(wallet_db_file, 'r') as f:
                wallets = json.load(f)
        else:
            wallets = {}
        
        if address not in wallets:
            # Получаем шарды от всех нод
            my_shard = get_node_shard()
            shards = {int(NODE_ID): my_shard}
            
            for peer_url in PEER_NODES:
                if not peer_url.strip():
                    continue
                try:
                    response = requests.get(f"{peer_url.strip()}/get_shard", timeout=5)
                    if response.status_code == 200:
                        peer_data = response.json()
                        shards[int(peer_data['node_id'])] = peer_data['shard']
                except Exception as e:
                    print(f"Failed to get shard from {peer_url}: {e}")
            
            if len(shards) != 3:
                return jsonify({'error': f'Need all 3 shards, got {len(shards)}'}), 503
            
            full_mnemonic = combine_shards(shards[1], shards[2], shards[3])
            
            # Ищем кошелек по HD путям
            for i in range(100):
                hd_path = f"m/44'/60'/0'/0/{i}"
                wallet = derive_wallet_from_full_mnemonic(full_mnemonic, hd_path)
                if wallet['address'] == address:
                    wallets[address] = {
                        'hd_path': hd_path,
                        'private_key': wallet['private_key']
                    }
                    with open(wallet_db_file, 'w') as f:
                        json.dump(wallets, f)
                    break
            else:
                return jsonify({'error': 'Wallet not found'}), 404
        
        private_key = wallets[address]['private_key']
        
        message = f"{address}:{to_address}:{amount}"
        message_hash = hashlib.sha256(message.encode()).hexdigest()
        
        account = Account.from_key(private_key)
        signed_message = account.sign_message(encode_defunct(text=message))
        
        signature = signed_message.signature.hex()
        
        return jsonify({
            'signature': signature,
            'tx_hash': message_hash,
            'node_id': NODE_ID
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"Starting MPC Node {NODE_ID} on port {NODE_PORT}")
    app.run(host='0.0.0.0', port=NODE_PORT, debug=True)
