from rest_framework import serializers
from .models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['address', 'hd_path', 'created_at']
        read_only_fields = ['address', 'created_at']


class CreateWalletSerializer(serializers.Serializer):
    hd_path = serializers.CharField(
        required=False,
        help_text="HD derivation path (optional, auto-generated if not provided)"
    )


class SignTransactionSerializer(serializers.Serializer):
    address = serializers.CharField(
        max_length=42,
        help_text="Wallet address to sign from"
    )
    to = serializers.CharField(
        max_length=42,
        help_text="Recipient address"
    )
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=18,
        help_text="Amount in ETH"
    )
    send_tx = serializers.IntegerField(
        required=False,
        default=0,
        help_text="1 to broadcast transaction to network, 0 to only sign"
    )
    
    def validate_address(self, value):
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid Ethereum address format")
        return value
    
    def validate_to(self, value):
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid Ethereum address format")
        return value
    
    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative")
        return value


class SignTransactionResponseSerializer(serializers.Serializer):
    signature = serializers.CharField()
    tx_hash = serializers.CharField(required=False)
    raw_transaction = serializers.CharField(required=False)
