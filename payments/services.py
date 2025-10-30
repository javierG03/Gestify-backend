"""Servicios y helpers para la integración con PayU."""

from __future__ import annotations

import hashlib
import logging
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import PaymentTransaction

if TYPE_CHECKING:  # pragma: no cover
    from eventos.models import Ticket


logger = logging.getLogger(__name__)


def _get_config_value(env_key: str, settings_key: str, *, required: bool = False) -> str | None:
    """Obtiene un valor de configuración desde entorno o settings."""
    value = os.getenv(env_key, getattr(settings, settings_key, None))
    if required and not value:
        raise ImproperlyConfigured(f"Falta la configuración requerida '{env_key}'/'{settings_key}' para PayU")
    return value


def _parse_bool(value: str | None, default: bool) -> bool:
    """Convierte cadenas de entorno en booleanos con un valor por defecto."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes"}


def get_payu_config() -> Dict[str, str | bool]:
    """Obtiene y valida la configuración necesaria para PayU."""
    api_key = _get_config_value("PAYU_API_KEY", "PAYU_API_KEY", required=True)
    merchant_id = _get_config_value("PAYU_MERCHANT_ID", "PAYU_MERCHANT_ID", required=True)
    account_id = _get_config_value("PAYU_ACCOUNT_ID", "PAYU_ACCOUNT_ID", required=True)
    confirmation_url = _get_config_value("PAYU_CONFIRMATION_URL", "PAYU_CONFIRMATION_URL", required=True)
    response_url = _get_config_value("PAYU_RESPONSE_URL", "PAYU_RESPONSE_URL", required=True)
    currency = _get_config_value("PAYU_CURRENCY", "PAYU_CURRENCY") or "COP"
    sandbox_flag = os.getenv("PAYU_SANDBOX") or getattr(settings, "PAYU_SANDBOX", "1")

    return {
        "api_key": api_key,
        "merchant_id": merchant_id,
        "account_id": account_id,
        "confirmation_url": confirmation_url,
        "response_url": response_url,
        "currency": currency,
        "sandbox": _parse_bool(sandbox_flag, default=True),
    }


def generate_payu_signature(api_key: str, merchant_id: str, reference_code: str, amount: str, currency: str = "COP") -> str:
    """Genera la firma de seguridad para PayU."""
    signature_str = f"{api_key}~{merchant_id}~{reference_code}~{amount}~{currency}"
    return hashlib.md5(signature_str.encode("utf-8")).hexdigest()


def validate_payu_signature(
    config: Dict[str, str | bool],
    reference_code: str,
    amount: str,
    currency: str,
    received_signature: str,
) -> bool:
    """Valida la firma recibida desde PayU."""

    expected_signature = generate_payu_signature(
        config["api_key"],
        config["merchant_id"],
        reference_code,
        amount,
        currency=currency,
    )
    return expected_signature == received_signature


def normalize_amount(value: object) -> Decimal:
    """Convierte el monto recibido a Decimal con dos decimales."""

    if isinstance(value, Decimal):
        amount = value
    else:
        try:
            amount = Decimal(str(value).replace(",", "."))
        except (InvalidOperation, AttributeError, TypeError):
            logger.warning("Monto inválido recibido desde PayU: %s", value)
            amount = Decimal("0")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


PAYU_STATE_MAP = {
    "4": "aprobado",
    "6": "rechazado",
    "7": "pendiente",
    "104": "error",
}


def map_payu_state(state: object) -> str:
    """Traduce el código de estado de PayU a una etiqueta legible."""

    return PAYU_STATE_MAP.get(str(state), "desconocido")


def update_payment_transaction(
    reference_code: str,
    *,
    amount: Decimal,
    currency: str,
    status: str,
    buyer_email: Optional[str] = None,
    transaction_id: Optional[str] = None,
) -> PaymentTransaction:
    """Crea o actualiza el registro de transacción local con la información recibida."""

    defaults = {
        "amount": amount,
        "currency": currency,
        "status": status,
    }
    if buyer_email:
        defaults["buyer_email"] = buyer_email
    if transaction_id:
        defaults["transaction_id"] = transaction_id

    transaction_obj, _created = PaymentTransaction.objects.update_or_create(
        reference_code=reference_code,
        defaults=defaults,
    )
    return transaction_obj


def update_ticket_status(reference_code: str, state_pol: str) -> Optional["Ticket"]:
    """Sincroniza el estado del ticket asociado según la respuesta de PayU."""

    from eventos.models import Ticket

    ticket = Ticket.objects.select_related("config_type").filter(unique_code=reference_code).first()
    if not ticket:
        logger.warning("Ticket con referencia %s no encontrado al procesar PayU", reference_code)
        return None

    if state_pol == "4" and ticket.status != "comprada":
        ticket.status = "comprada"
        ticket.save(update_fields=["status"])
    elif state_pol in {"6", "104"} and ticket.status == "comprada":
        ticket.status = "cancelada"
        ticket.save(update_fields=["status"])
    return ticket


def process_payu_notification(
    payload: Dict[str, object],
    config: Dict[str, str | bool],
) -> Tuple[PaymentTransaction, Optional["Ticket"], str]:
    """Procesa la notificación de PayU, actualizando la transacción y el ticket."""

    reference_code = str(payload.get("reference_sale") or payload.get("referenceCode"))
    value = payload.get("value") or payload.get("amount") or "0"
    currency = str(payload.get("currency") or config.get("currency", "COP"))
    state_pol = str(payload.get("state_pol", ""))
    buyer_email = payload.get("buyer_email") or payload.get("buyerEmail")
    transaction_id = (
        payload.get("transaction_id")
        or payload.get("transactionId")
        or payload.get("reference_pol")
    )

    amount_decimal = normalize_amount(value)
    status_label = map_payu_state(state_pol)

    payment = update_payment_transaction(
        reference_code,
        amount=amount_decimal,
        currency=currency,
        status=status_label,
        buyer_email=str(buyer_email) if buyer_email else None,
        transaction_id=str(transaction_id) if transaction_id else None,
    )

    ticket = update_ticket_status(reference_code, state_pol)

    return payment, ticket, status_label
