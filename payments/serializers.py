"""
payments/serializers.py
Serializador principal para transacciones de pago. Clean code y docstrings.
"""
from rest_framework import serializers
from .models import PaymentTransaction

class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializador para el modelo PaymentTransaction."""
    class Meta:
        model = PaymentTransaction
        fields = '__all__'

class PayUDataResponseSerializer(serializers.Serializer):
    """Datos que se devuelven al front-end para iniciar el pago en PayU."""
    sandbox = serializers.BooleanField()
    merchantId = serializers.CharField()
    accountId = serializers.CharField()
    description = serializers.CharField()
    referenceCode = serializers.CharField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    signature = serializers.CharField()
    buyerEmail = serializers.EmailField()
    confirmationUrl = serializers.URLField()
    responseUrl = serializers.URLField()