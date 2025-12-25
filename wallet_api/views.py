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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
import logging

logger = logging.getLogger(__name__)


class CreateWalletView(APIView):
    """
    POST /api/wallet/create
    
    Создает новый ETH кошелек через MPC ноды с HD деривацией
    """
    authentication_classes = [SHA256Authentication]
    
    @extend_schema(
        request=CreateWalletSerializer,
        responses={201: WalletSerializer},
        description="Create new ETH wallet using MPC nodes with HD derivation"
    )
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
    
    @extend_schema(
        request=SignTransactionSerializer,
        responses={200: SignTransactionResponseSerializer},
        description="Sign and send ETH transaction. Set amount=0 to send max balance minus gas.",
        examples=[
            OpenApiExample(
                'Example request',
                value={
                    'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
                    'to': '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199',
                    'amount': '0.01'
                },
            ),
        ]
    )
    def post(self, request):
        serializer = SignTransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        address = serializer.validated_data['address']
        to_address = serializer.validated_data['to']
        amount = serializer.validated_data['amount']
        send_tx = serializer.validated_data.get('send_tx', 0)
        
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
            
            nonce = w3.eth.get_transaction_count(address)
            gas_price = w3.eth.gas_price
            gas_limit = 21000
            
            if float(amount) == 0:
                balance_wei = w3.eth.get_balance(address)
                gas_cost = gas_price * gas_limit
                
                if balance_wei <= gas_cost:
                    return Response(
                        {'error': 'Insufficient balance for gas fees',
                         'balance': str(w3.from_wei(balance_wei, 'ether')),
                         'gas_cost': str(w3.from_wei(gas_cost, 'ether'))},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                amount_wei = balance_wei - gas_cost
                amount = w3.from_wei(amount_wei, 'ether')
            else:
                amount_wei = w3.to_wei(float(amount), 'ether')
            
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': w3.eth.chain_id
            }
            
            mpc_client = MPCClient()
            sign_result = mpc_client.sign_transaction(w3, transaction, address)
            
            raw_tx = sign_result['raw_transaction']
            tx_hash = sign_result['tx_hash']
            
            if send_tx == 1:
                logger.info(f"Broadcasting transaction {tx_hash} to network")
                w3.eth.send_raw_transaction(raw_tx)
                logger.info(f"Transaction {tx_hash} sent successfully")
            
            try:
                Transaction.objects.create(
                    tx_hash=tx_hash if tx_hash else 'N/A',
                    from_address=address,
                    to_address=to_address,
                    amount_eth=Decimal(str(amount)),
                    status=Transaction.STATUS_OK,
                    broadcasted=(send_tx == 1)
                )
            except Exception:
                pass
            
            response_serializer = SignTransactionResponseSerializer(data={
                'signature': raw_tx,
                'tx_hash': tx_hash,
                'raw_transaction': raw_tx
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
                    error_message=str(e),
                    broadcasted=False
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
    
    @extend_schema(
        responses={200: WalletSerializer(many=True)},
        description="List all created wallets"
    )
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
    
    @extend_schema(
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'django_version': {'type': 'string'},
                    'python_version': {'type': 'string'},
                    'debug': {'type': 'boolean'},
                    'infura_network': {'type': 'string'},
                    'require_signature': {'type': 'boolean'},
                    'request_expiry_seconds': {'type': 'integer'},
                    'mpc_nodes': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        },
        description="Get service configuration (no auth required)"
    )
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
    
    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {
            'eth_wallets': {'type': 'string', 'description': 'Comma-separated addresses'},
            'amount': {'type': 'string', 'description': 'ETH amount per wallet'}
        }}},
        responses={200: {'type': 'object'}},
        description="Bulk send ETH from master wallet to multiple addresses"
    )
    def post(self, request):
        from .serializers_bulk import BulkSendSerializer, BulkSendResponseSerializer
        from decimal import Decimal
        
        serializer = BulkSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        recipient_addresses = serializer.validated_data['eth_wallets']
        amount_per_wallet = serializer.validated_data['amount']
        send_tx = serializer.validated_data.get('send_tx', 0)
        
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
                try:
                    logger.info(f"Bulk-send [{i+1}/{total_recipients}]: {master_address} -> {recipient}, amount: {amount_per_wallet} ETH")
                    
                    transaction = {
                        'nonce': nonce + i,
                        'to': recipient,
                        'value': amount_wei_per_wallet,
                        'gas': gas_per_tx,
                        'gasPrice': gas_price,
                        'chainId': w3.eth.chain_id
                    }
                    
                    sign_result = mpc_client.sign_transaction(w3, transaction, master_address)
                    raw_tx = sign_result['raw_transaction']
                    tx_hash = sign_result['tx_hash']
                    
                    if send_tx == 1:
                        logger.info(f"Broadcasting transaction {tx_hash}")
                        w3.eth.send_raw_transaction(raw_tx)
                        logger.info(f"Transaction {tx_hash} sent")
                    
                    try:
                        Transaction.objects.create(
                            tx_hash=tx_hash,
                            from_address=master_address,
                            to_address=recipient,
                            amount_eth=Decimal(str(amount_per_wallet)),
                            status=Transaction.STATUS_OK,
                            broadcasted=(send_tx == 1)
                        )
                    except Exception as db_err:
                        logger.warning(f"Failed to save transaction to DB: {db_err}")
                    
                    logger.info(f"Bulk-send [{i+1}/{total_recipients}]: SUCCESS, tx_hash: {tx_hash}")
                    
                    transactions.append({
                        'recipient': recipient,
                        'amount': str(amount_per_wallet),
                        'signature': raw_tx[:20] + '...',
                        'tx_hash': tx_hash,
                        'nonce': nonce + i,
                        'sent': send_tx == 1
                    })
                except Exception as tx_error:
                    logger.error(f"Bulk-send [{i+1}/{total_recipients}]: FAILED - {tx_error}")
                    
                    try:
                        Transaction.objects.create(
                            tx_hash='ERROR',
                            from_address=master_address,
                            to_address=recipient,
                            amount_eth=Decimal(str(amount_per_wallet)),
                            status=Transaction.STATUS_ERROR,
                            error_message=str(tx_error),
                            broadcasted=False
                        )
                    except Exception:
                        pass
                    
                    transactions.append({
                        'recipient': recipient,
                        'amount': str(amount_per_wallet),
                        'signature': 'ERROR',
                        'tx_hash': 'ERROR',
                        'nonce': nonce + i,
                        'error': str(tx_error)
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
