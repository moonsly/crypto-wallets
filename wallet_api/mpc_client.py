import requests
from typing import List, Dict
from django.conf import settings


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
    
    def generate_wallet(self, hd_path: str) -> Dict:
        """
        Генерация кошелька через MPC ноды
        Требует согласование минимум 2 из 3 нод
        """
        responses = []
        
        for node_url in self.nodes:
            try:
                response = requests.post(
                    f"{node_url}/generate",
                    json={"hd_path": hd_path},
                    timeout=10
                )
                if response.status_code == 200:
                    responses.append(response.json())
            except Exception as e:
                print(f"Node {node_url} failed: {e}")
                continue
        
        if len(responses) < 2:
            raise Exception("Failed to reach consensus from MPC nodes (need 2 of 3)")
        
        address = responses[0]['address']
        for resp in responses[1:]:
            if resp['address'] != address:
                raise Exception("MPC nodes returned inconsistent addresses")
        
        return {
            'address': address,
            'hd_path': hd_path
        }
    
    def sign_transaction(self, address: str, to_address: str, amount: str) -> Dict:
        """
        Подпись транзакции через MPC ноды
        """
        responses = []
        
        for node_url in self.nodes:
            try:
                response = requests.post(
                    f"{node_url}/sign",
                    json={
                        "address": address,
                        "to": to_address,
                        "amount": amount
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    responses.append(response.json())
            except Exception as e:
                print(f"Node {node_url} failed: {e}")
                continue
        
        if len(responses) < 2:
            raise Exception("Failed to reach consensus from MPC nodes (need 2 of 3)")
        
        signature = responses[0]['signature']
        for resp in responses[1:]:
            if resp['signature'] != signature:
                raise Exception("MPC nodes returned inconsistent signatures")
        
        return {
            'signature': signature,
            'tx_hash': responses[0].get('tx_hash')
        }
