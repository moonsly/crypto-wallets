from django.contrib import admin
from .models import Wallet, UsedNonce, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['address', 'hd_path', 'created_at']
    search_fields = ['address']
    readonly_fields = ['address', 'hd_path', 'created_at']


@admin.register(UsedNonce)
class UsedNonceAdmin(admin.ModelAdmin):
    list_display = ['nonce', 'timestamp', 'created_at']
    search_fields = ['nonce']
    readonly_fields = ['nonce', 'timestamp', 'created_at']
    list_filter = ['created_at']
    
    def has_add_permission(self, request):
        return False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['tx_hash', 'from_address', 'to_address', 'amount_eth', 'status', 'created_at']
    search_fields = ['tx_hash', 'from_address', 'to_address']
    readonly_fields = ['tx_hash', 'from_address', 'to_address', 'amount_eth', 'status', 'error_message', 'created_at']
    list_filter = ['status', 'created_at']
    
    def has_add_permission(self, request):
        return False
