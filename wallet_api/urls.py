from django.urls import path
from .views import CreateWalletView, SignTransactionView, WalletListView, BulkSendView, ConfigView

urlpatterns = [
    path('config', ConfigView.as_view(), name='config'),
    path('wallet/create', CreateWalletView.as_view(), name='create_wallet'),
    path('wallet/sign', SignTransactionView.as_view(), name='sign_transaction'),
    path('wallet/bulk-send', BulkSendView.as_view(), name='bulk_send'),
    path('wallets', WalletListView.as_view(), name='list_wallets'),
]
