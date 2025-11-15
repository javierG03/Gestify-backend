"""Vistas principales del módulo de pagos."""

import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from usuarios.serializers import EmptySerializer
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer, PayUDataResponseSerializer
from .services import (
    generate_payu_signature,
    get_payu_config,
    process_payu_notification,
    validate_payu_signature,
)

logger = logging.getLogger("payments")


REQUIRED_PAYU_FIELDS = ("reference_sale", "value", "currency", "state_pol", "sign")


def _handle_payu_notification(request, source: str) -> Response:
    payload = request.data
    missing = [field for field in REQUIRED_PAYU_FIELDS if not payload.get(field)]
    if missing:
        logger.warning("Notificación PayU incompleta (%s): faltan %s", source, ", ".join(missing))
        return Response({'error': 'Datos incompletos'}, status=status.HTTP_400_BAD_REQUEST)

    config = get_payu_config()
    reference_code = payload["reference_sale"]
    value = payload["value"]
    currency = payload["currency"]
    received_signature = payload["sign"]

    if not validate_payu_signature(config, reference_code, value, currency, received_signature):
        logger.warning("Firma inválida PayU (%s) para referencia %s", source, reference_code)
        return Response({'error': 'Firma inválida'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment, ticket, status_label = process_payu_notification(payload, config)
    except Exception as exc:  # pragma: no cover - fallback de seguridad
        logger.error("Error procesando notificación PayU (%s): %s", source, exc, exc_info=True)
        return Response({'error': 'Error procesando la notificación de pago.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    state_pol = str(payload.get("state_pol"))
    if state_pol == "4":
        if not ticket:
            return Response({'error': 'Ticket no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        logger.info(
            "Pago confirmado (%s): referencia=%s, transacción=%s",
            source,
            payment.reference_code,
            payment.transaction_id,
        )
        response_body = {
            'message': 'Pago confirmado y ticket actualizado.',
            'payment_status': status_label,
        }
        if ticket:
            response_body['ticket_id'] = ticket.id
            response_body['ticket_status'] = ticket.status
        return Response(response_body, status=status.HTTP_200_OK)

    logger.info(
        "Notificación PayU (%s) con estado %s para referencia %s",
        source,
        status_label,
        payment.reference_code,
    )
    return Response(
        {
            'message': f'Estado de pago: {status_label}. Ticket no actualizado.',
            'payment_status': status_label,
        },
        status=status.HTTP_200_OK,
    )

class UserPaymentHistoryView(ListAPIView):
    """Endpoint para consultar el historial de pagos del usuario autenticado."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        user = self.request.user
        return PaymentTransaction.objects.filter(buyer_email=user.email).order_by('-id')

class PayUInitPaymentView(APIView):
    """Inicia el proceso de pago con PayU para un ticket específico."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Pagos"],
        request=EmptySerializer,  
        responses=PayUDataResponseSerializer 
    )
    @ratelimit(key='ip', rate='5/m', block=True)
    def post(self, request, ticket_id):
        try:
            from eventos.models import Ticket
            ticket = get_object_or_404(Ticket, id=ticket_id)
            if ticket.user != request.user:
                logger.warning(
                    "Intento de pago no autorizado: ticket %s solicitado por %s",
                    ticket_id,
                    request.user.email,
                )
                return Response({"error": "No tienes permiso para pagar este ticket."}, status=status.HTTP_403_FORBIDDEN)

            if ticket.status == "comprada":
                return Response(
                    {"error": "Este ticket ya fue pagado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if ticket.status in {"cancelada", "usada"}:
                return Response(
                    {"error": f"El ticket tiene un estado inválido para pago ({ticket.status})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            config = get_payu_config()
            reference_code = ticket.unique_code
            # PayU exige montos con dos decimales exactos
            amount_value = (ticket.config_type.price * ticket.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            amount = format(amount_value, ".2f")
            buyer_email = ticket.user.email
            description = f"{ticket.event.event_name} - {ticket.config_type.ticket_type.ticket_name}"
            payment, created = PaymentTransaction.objects.get_or_create(
                reference_code=reference_code,
                defaults={
                    "amount": amount_value,
                    "status": "iniciada",
                    "buyer_email": buyer_email,
                    "currency": config["currency"],
                },
            )

            if not created and payment.status == "aprobado":
                return Response(
                    {"error": "Este ticket ya cuenta con un pago aprobado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not created:
                payment.amount = amount_value
                payment.status = "iniciada"
                payment.currency = config["currency"]
                payment.buyer_email = buyer_email
                payment.transaction_id = None
                payment.updated_at = timezone.now()
                payment.save(update_fields=["amount", "status", "currency", "buyer_email", "transaction_id", "updated_at"])

            signature = generate_payu_signature(
                config['api_key'], config['merchant_id'], reference_code, amount, currency=config['currency']
            )
            logger.info(
                "Transacción iniciada: referencia=%s, usuario=%s, ticket_id=%s",
                reference_code,
                buyer_email,
                ticket_id,
            )
            return Response({
                "sandbox": config['sandbox'],
                "merchantId": config['merchant_id'],
                "accountId": config['account_id'],
                "description": description,
                "referenceCode": reference_code,
                "amount": amount,
                "currency": config['currency'],
                "signature": signature,
                "buyerEmail": buyer_email,
                "confirmationUrl": config['confirmation_url'],
                "responseUrl": config['response_url']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error iniciando pago: {str(e)}", exc_info=True)
            return Response({"error": "No se pudo iniciar el pago. Intente nuevamente."}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class PayUConfirmationAPIView(APIView):
    """Endpoint para recibir confirmación de pago de PayU."""

    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["Pagos - Webhooks"],
        request=EmptySerializer,  
        responses=EmptySerializer  
    )
    def post(self, request):
        return _handle_payu_notification(request, source="confirmation")

@method_decorator(csrf_exempt, name='dispatch')
class PayUWebhookAPIView(APIView):
    """Endpoint para recibir notificaciones automáticas de PayU (webhook)."""

    @extend_schema(
        tags=["Pagos - Webhooks"],
        request=EmptySerializer,  
        responses=EmptySerializer 
    )
    def post(self, request):
        return _handle_payu_notification(request, source="webhook")
