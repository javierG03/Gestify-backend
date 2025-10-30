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
