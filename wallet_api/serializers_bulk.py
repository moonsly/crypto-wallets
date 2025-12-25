from rest_framework import serializers


class BulkSendSerializer(serializers.Serializer):
    eth_wallets = serializers.CharField(
        help_text="Comma-separated ETH addresses (e.g., '0xABC...,0xDEF...')"
    )
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=18,
        help_text="Amount in ETH to send to EACH wallet"
    )
    
    def validate_eth_wallets(self, value):
        addresses = [addr.strip() for addr in value.split(',')]
        
        if not addresses:
            raise serializers.ValidationError("At least one address required")
        
        for addr in addresses:
            if not addr.startswith('0x') or len(addr) != 42:
                raise serializers.ValidationError(f"Invalid address: {addr}")
        
        return addresses
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class BulkSendResponseSerializer(serializers.Serializer):
    master_wallet = serializers.CharField()
    total_recipients = serializers.IntegerField()
    amount_per_wallet = serializers.CharField()
    total_amount = serializers.CharField()
    master_balance_before = serializers.CharField()
    master_balance_after = serializers.CharField()
    transactions = serializers.ListField(child=serializers.DictField())
