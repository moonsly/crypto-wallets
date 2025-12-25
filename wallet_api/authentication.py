import hashlib
import time
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from django.conf import settings
from django.db import IntegrityError


class SHA256Authentication(BaseAuthentication):
    """
    Аутентификация через:
    1. X-API-Key заголовок
    2. X-Signature - SHA256(key + timestamp + nonce + body) - опционально
    3. X-Timestamp - время запроса
    4. X-Nonce - уникальное значение (защита от replay)
    """
    
    def authenticate(self, request):
        from .models import UsedNonce
        
        api_key = request.META.get('HTTP_X_API_KEY')
        
        # Проверка API ключа
        if not api_key:
            raise exceptions.AuthenticationFailed('X-API-Key header is required')
        
        if api_key != settings.API_SECRET_KEY:
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        # Проверка подписи (если включена)
        require_signature = getattr(settings, 'REQUIRE_REQUEST_SIGNATURE', False)
        
        if not require_signature:
            # Простая аутентификация только по API key
            return (None, None)
        
        # Расширенная аутентификация с подписью
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')
        nonce = request.META.get('HTTP_X_NONCE')
        
        if not signature:
            raise exceptions.AuthenticationFailed('X-Signature header is required')
        
        if not timestamp:
            raise exceptions.AuthenticationFailed('X-Timestamp header is required')
        
        if not nonce:
            raise exceptions.AuthenticationFailed('X-Nonce header is required')
        
        # Проверка timestamp
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            expiry_seconds = settings.REQUEST_EXPIRY_SECONDS
            
            if abs(current_time - request_time) > expiry_seconds:
                raise exceptions.AuthenticationFailed(
                    f'Request timestamp expired (max {expiry_seconds}s)'
                )
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid timestamp format')
        
        # Проверка nonce (защита от replay)
        if UsedNonce.objects.filter(nonce=nonce).exists():
            raise exceptions.AuthenticationFailed('Nonce already used - replay attack detected')
        
        # Получаем тело запроса
        try:
            body = request.body.decode('utf-8') if request.body else ''
        except Exception:
            body = ''
        
        # Вычисляем ожидаемую подпись: SHA256(key + timestamp + nonce + body)
        message = f"{api_key}{timestamp}{nonce}{body}"
        expected_signature = hashlib.sha256(message.encode()).hexdigest()
        
        # Проверяем подпись
        if signature != expected_signature:
            raise exceptions.AuthenticationFailed('Invalid signature')
        
        # Сохраняем nonce
        try:
            UsedNonce.objects.create(nonce=nonce, timestamp=request_time)
            # Чистка старых nonce
            if int(time.time()) % 60 == 0:
                UsedNonce.cleanup_old_nonces()
        except IntegrityError:
            raise exceptions.AuthenticationFailed('Nonce already used - replay attack detected')
        
        return (None, None)
