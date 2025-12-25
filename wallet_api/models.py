from django.db import models
from django.utils import timezone
import datetime


class Wallet(models.Model):
    address = models.CharField(max_length=42, unique=True)
    hd_path = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.address


class UsedNonce(models.Model):
    """
    Хранит использованные nonce для защиты от replay атак
    """
    nonce = models.CharField(max_length=255, unique=True, db_index=True)
    timestamp = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['nonce']),
            models.Index(fields=['created_at']),
        ]
    
    @classmethod
    def cleanup_old_nonces(cls):
        """Удаляет nonce старше 10 минут"""
        cutoff = timezone.now() - datetime.timedelta(minutes=10)
        cls.objects.filter(created_at__lt=cutoff).delete()
    
    def __str__(self):
        return f"{self.nonce} - {self.timestamp}"


class Transaction(models.Model):
    """
    Проведенные транзакции через API
    """
    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_OK, 'OK'),
        (STATUS_ERROR, 'Error'),
    ]
    
    tx_hash = models.CharField(max_length=66, db_index=True)
    from_address = models.CharField(max_length=42)
    to_address = models.CharField(max_length=42)
    amount_eth = models.DecimalField(max_digits=32, decimal_places=18)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['from_address']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tx_hash} - {self.status}"
