"""Vistas relacionadas con tickets: envío, historial y validación."""

from typing import List
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes  
from drf_spectacular.utils import extend_schema, OpenApiTypes
from rest_framework import generics, status, serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import IsStaffOrAdmin
from usuarios.serializers import EmptySerializer, MessageSerializer

from ..models import Ticket, TicketAccessLog
from ..serializers import TicketAccessLogSerializer, TicketSerializer


logger = logging.getLogger(__name__)


class TicketValidationRequestSerializer(serializers.Serializer):
    unique_code = serializers.CharField()

class TicketValidationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    ticket = TicketSerializer() 

class TicketValidationSuccessResponseSerializer(serializers.Serializer):
        valid = serializers.BooleanField()
        message = serializers.CharField()
        ticket_id = serializers.IntegerField()
        event = serializers.CharField()
        event_id = serializers.IntegerField()
        user = serializers.CharField()
        user_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        amount = serializers.IntegerField()
        date_of_purchase = serializers.DateTimeField()
        unique_code = serializers.UUIDField()

class TicketDetailAPIView(RetrieveAPIView):
    """Devuelve el detalle de un ticket por su ID."""

    queryset = Ticket.objects.select_related("user", "event", "config_type__ticket_type")
    serializer_class = TicketSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated and user.groups.filter(name__in={"Administrador", "Staff"}).exists():
            return queryset
        return queryset.filter(user=user)

    def get_object(self):  # type: ignore[override]
        obj = super().get_object()
        user = self.request.user
        if user and user.is_authenticated:
            if obj.user_id == user.id or user.groups.filter(name__in={"Administrador", "Staff"}).exists():
                return obj
        raise PermissionDenied("No estás autorizado para consultar este ticket.")


class ResendTicketEmailAPIView(APIView):
    """Permite reenviar por correo el ticket del usuario autenticado."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tickets"],
        request=EmptySerializer,
        responses=MessageSerializer 
    )
    def post(self, request, pk: int) -> Response:
        ticket = get_object_or_404(
            Ticket.objects.select_related("user", "event", "config_type__ticket_type"),
            pk=pk,
        )
        if ticket.user_id != request.user.id:
            raise PermissionDenied("No estás autorizado para reenviar este ticket.")

        qr_base64 = ticket.get_qr_base64() if hasattr(ticket, "get_qr_base64") else None
        subject = f"Tu ticket para {ticket.event.event_name}"
        message_lines: List[str] = [
            f"Hola {ticket.user.first_name or ticket.user.email}",
            "",
            "Adjuntamos los detalles de tu ticket:",
            f"Evento: {ticket.event.event_name}",
            f"Tipo: {ticket.config_type.ticket_type.ticket_name}",
            f"Código único: {ticket.unique_code}",
        ]
        if qr_base64:
            message_lines.append(f"QR (base64): {qr_base64}")
        message_lines.append("\n¡Te esperamos en el evento!")

        send_mail(
            subject,
            "\n".join(message_lines),
            settings.DEFAULT_FROM_EMAIL,
            [ticket.user.email],
            fail_silently=False,
        )
        return Response({"message": "Ticket enviado al correo."}, status=status.HTTP_200_OK)


class MyTicketsAPIView(APIView):
    """Lista los tickets pertenecientes al usuario autenticado."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tickets"],
        responses=TicketSerializer(many=True) 
    )
    def get(self, request) -> Response:
        tickets = Ticket.objects.filter(user=request.user).select_related(
            "event", "config_type__ticket_type"
        )
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data)


class TicketAccessLogListView(generics.ListAPIView):# Devuelve un 200 OK
    """Auditoría de accesos asociados a un ticket."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TicketAccessLogSerializer

    @extend_schema(tags=["Tickets"], operation_id="ticket_access_log")
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        ticket_id = self.kwargs.get("ticket_id")
        ticket = get_object_or_404(Ticket.objects.select_related("user"), pk=ticket_id)
        user = self.request.user
        if not user.groups.filter(name__in={"Administrador", "Staff"}).exists() and ticket.user_id != user.id:
            raise PermissionDenied("No puedes consultar el historial de este ticket.")
        return TicketAccessLog.objects.filter(ticket=ticket).select_related("accessed_by").order_by(
            "-access_time"
        )


class TicketValidationAPIView(APIView):
    """Valida tickets por código único y registra el acceso."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsStaffOrAdmin]

    @extend_schema(
        tags=["Tickets"], 
        operation_id="validate_ticket", 
        request=TicketValidationRequestSerializer,
        responses=TicketValidationSuccessResponseSerializer,
    )
    def post(self, request) -> Response:
        unique_code = request.data.get("unique_code")
        if not unique_code:
            logger.warning("Validación de ticket sin código por usuario %s", request.user.id)
            return Response({"valid": False, "error": "No se recibió el código."}, status=status.HTTP_400_BAD_REQUEST)

        ticket = get_object_or_404(
            Ticket.objects.select_related("event", "user", "config_type__ticket_type"),
            unique_code=unique_code,
        )

        if ticket.status in {"usada", "cancelada", "pendiente"}:
            error_map = {
                "usada": "Ticket ya fue usada.",
                "cancelada": "Ticket cancelada.",
                "pendiente": "Ticket pendiente de pago.",
            }
            logger.info(
                "Validación rechazada - estado %s para ticket %s por usuario %s",
                ticket.status,
                ticket.id,
                request.user.id,
            )
            return Response({"valid": False, "error": error_map[ticket.status]}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = "usada"
        ticket.save(update_fields=["status"])
        logger.info("Ticket %s validado correctamente por usuario %s", ticket.id, request.user.id)

        TicketAccessLog.objects.create(
            ticket=ticket,
            accessed_by=request.user,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            device_info=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            {
                "valid": True,
                "message": "Ticket válida. Acceso permitido.",
                "ticket_id": ticket.id,
                "event": ticket.event.event_name,
                "event_id": ticket.event.id,
                "user": ticket.user.get_full_name() or ticket.user.email,
                "user_id": ticket.user.id,
                "ticket_type": ticket.config_type.ticket_type.ticket_name,
                "amount": ticket.amount,
                "date_of_purchase": ticket.date_of_purchase,
                "unique_code": ticket.unique_code,
            },
            status=status.HTTP_200_OK,
        )
