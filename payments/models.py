"""
payments/models.py
Modelo principal para transacciones de pago. Clean code y docstrings.
"""
from django.db import models

class PaymentTransaction(models.Model):
    """Modelo para registrar transacciones de pago (auditoría y control)."""
    reference_code = models.CharField(max_length=64, unique=True)
    transaction_id = models.CharField(max_length=64, blank=True, null=True)
    status = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='COP')
    buyer_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    gateway = models.CharField(max_length=32, default='PayU')
    class Meta:
        db_table = "payments_payment_transaction"
    def __str__(self):
        return f"{self.reference_code} - {self.status}"