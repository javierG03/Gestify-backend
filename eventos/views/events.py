"""Vistas de eventos: CRUD, asistentes y compra de tickets."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from usuarios.permissions import IsAdminGroup
from usuarios.serializers import CustomUserSerializer

from ..models import Event, Ticket, TicketTypeEvent
from ..serializers import (
    EventSerializer, 
    TicketSerializer, 
    TicketTypeEventSerializer, 
    AttendeeTicketSerializer, 
    MyEventSerializer, 
    BuyTicketRequestSerializer, 
    BuyTicketResponseSerializer,
)


def _validate_user_age_for_event(user, event) -> Optional[Dict[str, str]]:
    """Devuelve un dict con error si el usuario no cumple la edad mínima."""

    if not event.min_age:
        return None

    if not user.birth_date:
        return {"error": f"Debes registrar tu fecha de nacimiento (mínimo {event.min_age} años)."}

    today = date.today()
    age = today.year - user.birth_date.year - (
        (today.month, today.day) < (user.birth_date.month, user.birth_date.day)
    )
    if age < event.min_age:
        return {"error": f"El evento requiere mínimo {event.min_age} años. Tu edad registrada es {age}."}
    return None


class EventInscritosAPIView(APIView):
    """Lista los asistentes registrados a un evento."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(
            tags=["Eventos"], 
            operation_id="event_attendees", 
            responses=AttendeeTicketSerializer(many=True),
    )

    def get(self, request, pk: int) -> Response:
        event = get_object_or_404(Event, pk=pk)
        tickets = Ticket.objects.filter(event=event).select_related("user", "config_type__ticket_type")
        data: List[Dict[str, object]] = []
        for ticket in tickets:
            data.append(
                {
                    "ticket_id": ticket.id,
                    "user": CustomUserSerializer(ticket.user).data,
                    "ticket_type": ticket.config_type.ticket_type.ticket_name,
                    "amount": ticket.amount,
                    "status": ticket.status,
                    "unique_code": ticket.unique_code,
                    "date_of_purchase": ticket.date_of_purchase,
                    "price_paid": str(ticket.config_type.price),
                }
            )
        return Response(data, status=status.HTTP_200_OK)


class MyEventsAPIView(APIView):
    """Eventos a los que el usuario autenticado está inscrito."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]



    @extend_schema(
            tags=["Eventos"], 
            operation_id="my_events",
            responses=MyEventSerializer(many=True),
    )
    def get(self, request) -> Response:
        user_tickets = Ticket.objects.filter(user=request.user).select_related(
            "event", "config_type__ticket_type"
        )
        events_data: Dict[int, Dict[str, object]] = {}
        for ticket in user_tickets:
            event = ticket.event
            if event.id not in events_data:
                events_data[event.id] = {
                    "event": event.event_name,
                    "event_id": event.id,
                    "date": event.date,
                    "location": str(event.location) if event.location else None,
                    "country": event.country,
                    "city_text": event.city_text,
                    "department_text": event.department_text,
                    "status": event.status,
                    "tickets": [],
                }
            events_data[event.id]["tickets"].append(
                {
                    "ticket_id": ticket.id,
                    "type": ticket.config_type.ticket_type.ticket_name,
                    "amount": ticket.amount,
                    "status": ticket.status,
                    "unique_code": ticket.unique_code,
                    "qr_base64": ticket.get_qr_base64() if hasattr(ticket, "get_qr_base64") else None,
                    "date_of_purchase": ticket.date_of_purchase,
                    "price_paid": str(ticket.config_type.price),
                }
            )
        return Response(list(events_data.values()), status=status.HTTP_200_OK)


class EventViewSet(viewsets.ModelViewSet):
    """CRUD de eventos con acciones adicionales."""

    queryset = Event.objects.prefetch_related(
        Prefetch("tickets", queryset=Ticket.objects.select_related("user", "config_type__ticket_type"))
    ).select_related("location")
    serializer_class = EventSerializer
    authentication_classes = [TokenAuthentication]
    def perform_create(self, serializer):
        # Guarda el evento asignando el usuario actual como creador
        serializer.save(creator=self.request.user)
    def get_permissions(self):
        admin_actions = {"create", "update", "partial_update", "destroy", "cancelar"}
        if getattr(self, "action", None) in admin_actions:
            permissions = [IsAuthenticated, IsAdminGroup]
        else:
            permissions = [AllowAny]
        return [perm() for perm in permissions]

    @extend_schema(tags=["Eventos"], operation_id="event_list")
    def list(self, request, *args, **kwargs):  # type: ignore[override]
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Eventos"], operation_id="event_create")
    def create(self, request, *args, **kwargs):  # type: ignore[override]
        response = super().create(request, *args, **kwargs)
        # Si el objeto tiene advertencia, la agregamos a la respuesta
        if hasattr(response.data, 'get'):
            event_id = response.data.get('id')
            from ..models import Event
            event = Event.objects.filter(id=event_id).first()
            if event and hasattr(event, '_warning') and event._warning:
                response.data['warning'] = event._warning
        return response

    @extend_schema(tags=["Eventos"], operation_id="event_detail")
    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Eventos"], operation_id="event_update")
    def update(self, request, *args, **kwargs):  # type: ignore[override]
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["Eventos"], operation_id="event_partial_update")
    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=["Eventos"], operation_id="event_delete")
    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    @extend_schema(tags=["Eventos"], operation_id="event_availability")
    def availability(self, request, pk=None):
        event = self.get_object()
        types = TicketTypeEvent.objects.select_related("ticket_type").filter(event=event)
        data = [
            {
                "id": item.id,
                "ticket_type": item.ticket_type.ticket_name,
                "price": item.price,
                "maximun_capacity": item.maximun_capacity,
                "capacity_sold": item.capacity_sold,
                "remaining_capacity": max(0, item.maximun_capacity - item.capacity_sold),
                "is_sold_out": item.capacity_sold >= item.maximun_capacity,
            }
            for item in types
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    @extend_schema(tags=["Eventos"], operation_id="event_ticket_types")
    def ticket_types_available(self, request, pk=None):
        event = self.get_object()
        if event.status != "activo":
            return Response(
                {"error": "No se pueden consultar tipos para eventos inactivos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        types = TicketTypeEvent.objects.select_related("ticket_type").filter(event=event)
        serializer = TicketTypeEventSerializer(types, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminGroup])
    @extend_schema(tags=["Eventos"], operation_id="event_cancel")
    def cancelar(self, request, pk=None):
        event = self.get_object()
        if event.status == "cancelado":
            return Response({"error": "El evento ya está cancelado."}, status=status.HTTP_400_BAD_REQUEST)
        event.status = "cancelado"
        event.save(update_fields=["status"])
        return Response(
            {"id": event.id, "status": event.status, "message": "Evento cancelado exitosamente."},
            status=status.HTTP_200_OK,
        )

    def get_object(self):
        event = super().get_object()
        # Automatización: si la fecha de apertura de ventas ya pasó y el evento está programado, cambiar a activo
        if event.status == "programado" and event.sales_open_datetime:
            if timezone.now() >= event.sales_open_datetime:
                event.status = "activo"
                event.save(update_fields=["status"])
        return event


class BuyTicketAPIView(APIView):
    """Compra o reserva de tickets para un evento."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
            tags=["Pagos"], 
            operation_id="buy_ticket",
            request=BuyTicketRequestSerializer,
        responses={
            201: BuyTicketResponseSerializer,
        },
    )
    def post(self, request, pk: int) -> Response:
        event = get_object_or_404(Event, pk=pk)
        if event.status != "activo":
            return Response(
                {"error": "No se pueden comprar tickets para eventos inactivos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        age_error = _validate_user_age_for_event(request.user, event)
        if age_error:
            return Response(age_error, status=status.HTTP_400_BAD_REQUEST)

        config_type_id = request.data.get("config_type_id")
        if not config_type_id:
            return Response(
                {"error": "Debe especificar config_type_id (ID de TicketTypeEvent)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = int(request.data.get("amount", 1))
        except (TypeError, ValueError):
            return Response({"error": "amount debe ser un entero positivo."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "amount debe ser un entero positivo."}, status=status.HTTP_400_BAD_REQUEST)

        config_type = get_object_or_404(TicketTypeEvent, id=config_type_id, event=event)
        remaining_capacity = config_type.maximun_capacity - config_type.capacity_sold
        if amount > remaining_capacity:
            return Response(
                {"error": f"No hay suficiente aforo disponible. Quedan {remaining_capacity} boletos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketSerializer(
            data={"amount": amount, "status": "comprada" if config_type.price == 0 else "pendiente"},
            context={"config_type": config_type, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(user=request.user)

        if config_type.price == 0:
            return Response(
                {
                    "message": "Ticket gratuita creada exitosamente.",
                    "ticket_id": ticket.id,
                    "unique_code": ticket.unique_code,
                },
                status=status.HTTP_201_CREATED,
            )

        from payments.services import generate_payu_signature, get_payu_config  # Lazy import

        try:
            config = get_payu_config()
        except ImproperlyConfigured as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        total_amount_value = (config_type.price * Decimal(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_amount = format(total_amount_value, ".2f")
        reference_code = ticket.unique_code
        signature = generate_payu_signature(
            config["api_key"],
            config["merchant_id"],
            reference_code,
            total_amount,
            currency=config["currency"],
        )

        payment_data = {
            "sandbox": config["sandbox"],
            "merchantId": config["merchant_id"],
            "accountId": config["account_id"],
            "description": f"{event.event_name} - {config_type.ticket_type.ticket_name}",
            "referenceCode": reference_code,
            "amount": total_amount,
            "currency": config["currency"],
            "signature": signature,
            "buyerEmail": request.user.email,
            "confirmationUrl": config["confirmation_url"],
            "responseUrl": config["response_url"],
        }

        return Response(
            {
                "message": "Ticket creada. Procede al pago.",
                "ticket_id": ticket.id,
                "config_type_id": config_type_id,
                "amount": amount,
                "total_a_pagar": total_amount,
                "payment": payment_data,
            },
            status=status.HTTP_201_CREATED,
        )
# ... (Después de la clase BuyTicketAPIView, al final del archivo)

class MyCreatedEventsAPIView(APIView):
    """
    Eventos CREADOS por el usuario autenticado (Organizador).
    """
    authentication_classes = [TokenAuthentication]
    # NOTA: Decide si es solo IsAuthenticated o IsAdminGroup
    permission_classes = [IsAuthenticated] 

    @extend_schema(
        tags=["Eventos (Organizador)"], # Nuevo tag para claridad
        operation_id="my_created_events",
        responses=MyEventSerializer(many=True), # Reusamos el MyEventSerializer
    )
    def get(self, request) -> Response:
        # Esta es la lógica que buscábamos:
        # Filtra Eventos donde el 'creator' (Paso 1) sea el usuario logueado
        created_events = Event.objects.filter(creator=request.user).order_by('-start_datetime')
        
        # Serializa los eventos
        serializer = EventSerializer(created_events, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)