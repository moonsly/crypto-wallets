from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Wallet, Transaction
from .serializers import (
    WalletSerializer,
    CreateWalletSerializer,
    SignTransactionSerializer,
    SignTransactionResponseSerializer
)
from .authentication import SHA256Authentication
from .mpc_client import MPCClient
from web3 import Web3
from django.conf import settings
from decimal import Decimal


class CreateWalletView(APIView):
    """
    POST /api/wallet/create
    
    Создает новый ETH кошелек через MPC ноды с HD деривацией
    """
    authentication_classes = [SHA256Authentication]
    
    def post(self, request):
        serializer = CreateWalletSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        hd_path = serializer.validated_data.get('hd_path')
        
        if not hd_path:
            wallet_count = Wallet.objects.count()
            hd_path = f"m/44'/60'/0'/0/{wallet_count}"
        
        try:
            mpc_client = MPCClient()
            wallet_data = mpc_client.generate_wallet(hd_path)
            
            wallet = Wallet.objects.create(
                address=wallet_data['address'],
                hd_path=wallet_data['hd_path']
            )
            
            response_serializer = WalletSerializer(wallet)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SignTransactionView(APIView):
    """
    POST /api/wallet/sign
    
    Подписывает транзакцию через MPC ноды и отправляет в Infura testnet
    """
    authentication_classes = [SHA256Authentication]
    
    def post(self, request):
        serializer = SignTransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        address = serializer.validated_data['address']
        to_address = serializer.validated_data['to']
        amount = serializer.validated_data['amount']
        
        try:
            wallet = Wallet.objects.get(address=address)
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'Wallet not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            w3 = Web3(Web3.HTTPProvider(
                f"https://{settings.INFURA_NETWORK}.infura.io/v3/{settings.INFURA_API_KEY}"
            ))
            
            if not w3.is_connected():
                return Response(
                    {'error': 'Failed to connect to Ethereum network'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            amount_wei = w3.to_wei(float(amount), 'ether')
            
            nonce = w3.eth.get_transaction_count(address)
            gas_price = w3.eth.gas_price
            
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': w3.eth.chain_id
            }
            
            mpc_client = MPCClient()
            sign_result = mpc_client.sign_transaction(
                address=address,
                to_address=to_address,
                amount=str(amount)
            )
            
            tx_hash = sign_result.get('tx_hash', '')
            
            try:
                Transaction.objects.create(
                    tx_hash=tx_hash if tx_hash else 'N/A',
                    from_address=address,
                    to_address=to_address,
                    amount_eth=Decimal(str(amount)),
                    status=Transaction.STATUS_OK
                )
            except Exception:
                pass
            
            response_serializer = SignTransactionResponseSerializer(data={
                'signature': sign_result['signature'],
                'tx_hash': tx_hash,
                'raw_transaction': str(transaction)
            })
            
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    response_serializer.errors,
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            try:
                Transaction.objects.create(
                    tx_hash='ERROR',
                    from_address=address,
                    to_address=to_address,
                    amount_eth=Decimal(str(amount)),
                    status=Transaction.STATUS_ERROR,
                    error_message=str(e)
                )
            except Exception:
                pass
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WalletListView(APIView):
    """
    GET /api/wallets
    
    Возвращает список всех созданных кошельков
    """
    authentication_classes = [SHA256Authentication]
    
    def get(self, request):
        wallets = Wallet.objects.all()
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConfigView(APIView):
    """
    GET /api/config
    
    Возвращает текущую конфигурацию Django (без авторизации)
    """
    authentication_classes = []
    
    def get(self, request):
        import django
        import sys
        
        config = {
            'django_version': django.get_version(),
            'python_version': sys.version,
            'debug': settings.DEBUG,
            'infura_network': settings.INFURA_NETWORK,
            'require_signature': settings.REQUIRE_REQUEST_SIGNATURE,
            'request_expiry_seconds': settings.REQUEST_EXPIRY_SECONDS,
            'mpc_nodes': [
                settings.MPC_NODE_1_URL,
                settings.MPC_NODE_2_URL,
                settings.MPC_NODE_3_URL
            ]
        }
        return Response(config, status=status.HTTP_200_OK)


class BulkSendView(APIView):
    """
    POST /api/wallet/bulk-send
    
    Отправляет ETH с мастер кошелька (m/44'/60'/0'/0/0) на несколько адресов
    """
    authentication_classes = [SHA256Authentication]
    
    def post(self, request):
        from .serializers_bulk import BulkSendSerializer, BulkSendResponseSerializer
        from decimal import Decimal
        
        serializer = BulkSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        recipient_addresses = serializer.validated_data['eth_wallets']
        amount_per_wallet = serializer.validated_data['amount']
        
        try:
            # Подключение к Ethereum
            w3 = Web3(Web3.HTTPProvider(
                f"https://{settings.INFURA_NETWORK}.infura.io/v3/{settings.INFURA_API_KEY}"
            ))
            
            if not w3.is_connected():
                return Response(
                    {'error': 'Failed to connect to Ethereum network'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Получаем мастер кошелек (первый из мнемоника)
            master_hd_path = "m/44'/60'/0'/0/0"
            
            # Запрашиваем адрес мастер кошелька через MPC
            mpc_client = MPCClient()
            master_wallet_data = mpc_client.generate_wallet(master_hd_path)
            master_address = master_wallet_data['address']
            
            # Проверяем баланс мастер кошелька
            master_balance_wei = w3.eth.get_balance(master_address)
            master_balance_eth = w3.from_wei(master_balance_wei, 'ether')
            
            # Рассчитываем общую сумму (amount * количество получателей + gas)
            total_recipients = len(recipient_addresses)
            amount_wei_per_wallet = w3.to_wei(float(amount_per_wallet), 'ether')
            gas_price = w3.eth.gas_price
            gas_per_tx = 21000
            
            total_amount_wei = amount_wei_per_wallet * total_recipients
            total_gas_wei = gas_price * gas_per_tx * total_recipients
            total_needed_wei = total_amount_wei + total_gas_wei
            
            # Проверка баланса
            if master_balance_wei < total_needed_wei:
                total_needed_eth = w3.from_wei(total_needed_wei, 'ether')
                return Response({
                    'error': 'Insufficient balance on master wallet',
                    'master_wallet': master_address,
                    'balance': str(master_balance_eth),
                    'required': str(total_needed_eth),
                    'recipients': total_recipients,
                    'amount_per_wallet': str(amount_per_wallet)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Генерируем и подписываем транзакции
            transactions = []
            nonce = w3.eth.get_transaction_count(master_address)
            
            for i, recipient in enumerate(recipient_addresses):
                # Подписываем через MPC
                sign_result = mpc_client.sign_transaction(
                    address=master_address,
                    to_address=recipient,
                    amount=str(amount_per_wallet)
                )
                
                transactions.append({
                    'recipient': recipient,
                    'amount': str(amount_per_wallet),
                    'signature': sign_result['signature'][:20] + '...',
                    'tx_hash': sign_result.get('tx_hash', 'N/A'),
                    'nonce': nonce + i
                })
            
            # Баланс после отправки (теоретический)
            balance_after_wei = master_balance_wei - total_needed_wei
            balance_after_eth = w3.from_wei(balance_after_wei, 'ether')
            
            response_data = {
                'master_wallet': master_address,
                'total_recipients': total_recipients,
                'amount_per_wallet': str(amount_per_wallet),
                'total_amount': str(w3.from_wei(total_amount_wei, 'ether')),
                'master_balance_before': str(master_balance_eth),
                'master_balance_after': str(balance_after_eth),
                'transactions': transactions
            }
            
            response_serializer = BulkSendResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
