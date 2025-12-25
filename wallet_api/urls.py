from django.urls import path
from .views import CreateWalletView, SignTransactionView, WalletListView, BulkSendView, ConfigView, TransactionListView, HealthView

urlpatterns = [
    path('health', HealthView.as_view(), name='health'),
    path('config', ConfigView.as_view(), name='config'),
    path('wallet/create', CreateWalletView.as_view(), name='create_wallet'),
    path('wallet/sign', SignTransactionView.as_view(), name='sign_transaction'),
    path('wallet/bulk-send', BulkSendView.as_view(), name='bulk_send'),
    path('wallets', WalletListView.as_view(), name='list_wallets'),
    path('transactions', TransactionListView.as_view(), name='list_transactions'),
]
