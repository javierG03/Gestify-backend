"""
payments/urls.py
URLs principales del módulo de pagos. Organización y comentarios claros.
"""
from django.urls import path
from .views import PayUConfirmationAPIView, PayUInitPaymentView, UserPaymentHistoryView, PayUWebhookAPIView

urlpatterns = [
    # --- Confirmación de pago PayU ---
    path('payu/confirmation/', PayUConfirmationAPIView.as_view(), name='payu-confirmation'),
    # --- Webhook de PayU ---
    path('payu/webhook/', PayUWebhookAPIView.as_view(), name='payu-webhook'),
    # --- Iniciar pago de ticket ---
    path('ticket/<int:ticket_id>/pay/', PayUInitPaymentView.as_view(), name='ticket-pay'),
    # --- Historial de pagos del usuario ---
    path('user/history/', UserPaymentHistoryView.as_view(), name='user-payment-history'),
]
