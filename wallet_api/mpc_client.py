import requests
from typing import List, Dict
from django.conf import settings
from hdwallet import HDWallet
from hdwallet.symbols import ETH
from eth_account import Account
from eth_account.messages import encode_defunct
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os


class MPCClient:
    """
    Клиент для взаимодействия с MPC нодами
    """
    
    def __init__(self):
        self.nodes = [
            settings.MPC_NODE_1_URL,
            settings.MPC_NODE_2_URL,
            settings.MPC_NODE_3_URL,
        ]
        self.encryption_key = settings.SHARD_ENCRYPTION_KEY
    
    def decrypt_shard(self, encrypted_shard: str) -> str:
        if not self.encryption_key:
            raise Exception('SHARD_ENCRYPTION_KEY not set')
        
        key = hashlib.sha256(self.encryption_key.encode()).digest()
        data = base64.b64decode(encrypted_shard)
        iv = data[:16]
        encrypted = data[16:]
        
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        return decrypted.decode()
    
    def get_shards(self) -> Dict[int, str]:
        """
        Получает шарды от всех 3 нод и расшифровывает их
        """
        shards = {}
        
        for i, node_url in enumerate(self.nodes, 1):
            try:
                response = requests.get(
                    f"{node_url}/get_shard",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    encrypted_shard = data['encrypted_shard']
                    decrypted_shard = self.decrypt_shard(encrypted_shard)
                    shards[i] = decrypted_shard
            except Exception as e:
                print(f"Node {node_url} failed: {e}")
                continue
        
        if len(shards) != 3:
            raise Exception(f"Need all 3 shards, got {len(shards)}")
        
        return shards
    
    def combine_shards(self, shards: Dict[int, str]) -> str:
        """
        Объединяет шарды в полный мнемоник
        """
        return f"{shards[1]} {shards[2]} {shards[3]}"
    
    def derive_wallet(self, mnemonic: str, hd_path: str) -> Dict:
        """
        Деривация кошелька из мнемоника
        """
        hdwallet = HDWallet(symbol=ETH)
        hdwallet.from_mnemonic(mnemonic)
        hdwallet.from_path(hd_path)
        
        return {
            'address': hdwallet.p2pkh_address(),
            'private_key': hdwallet.private_key(),
            'public_key': hdwallet.public_key()
        }
    
    def generate_wallet(self, hd_path: str) -> Dict:
        """
        Генерация кошелька: получает шарды, собирает мнемоник, делает деривацию
        """
        shards = self.get_shards()
        mnemonic = self.combine_shards(shards)
        wallet = self.derive_wallet(mnemonic, hd_path)
        
        return {
            'address': wallet['address'],
            'hd_path': hd_path
        }
    
    def sign_transaction(self, w3, transaction_dict: Dict, from_address: str) -> Dict:
        """
        Подписывает транзакцию: получает шарды, восстанавливает private key, подписывает raw tx
        """
        from .models import Wallet
        
        try:
            wallet_obj = Wallet.objects.get(address=from_address)
            hd_path = wallet_obj.hd_path
        except Wallet.DoesNotExist:
            raise Exception(f"Wallet {from_address} not found in database")
        
        shards = self.get_shards()
        mnemonic = self.combine_shards(shards)
        wallet = self.derive_wallet(mnemonic, hd_path)
        
        account = Account.from_key(wallet['private_key'])
        signed_tx = account.sign_transaction(transaction_dict)
        
        return {
            'raw_transaction': signed_tx.rawTransaction.hex(),
            'tx_hash': signed_tx.hash.hex()
        }
