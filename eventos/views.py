# Endpoint para listar inscritos (tickets) de un evento
from usuarios.serializers import CustomUserSerializer
from django.shortcuts import render, get_object_or_404
from .serializers import (
    EventSerializer, TicketTypeEventSerializer, TicketSerializer, TicketTypeSerializer
)
from .models import Event, TicketType, TicketTypeEvent, Ticket
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from usuarios.permissions import IsAdminGroup
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, OpenApiTypes
import os
import hashlib
from django.utils import timezone
from decimal import Decimal

class EventInscritosAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        tickets = Ticket.objects.filter(event=event)
        data = []
        for ticket in tickets:
            data.append({
                "ticket_id": ticket.id,
                "user": CustomUserSerializer(ticket.user).data,
                "ticket_type": ticket.config_type.ticket_type.ticket_name,
                "amount": ticket.amount,
                "status": ticket.status,
                "unique_code": ticket.unique_code,
                "date_of_purchase": ticket.date_of_purchase,
                "price_paid": str(ticket.config_type.price)
            })
        return Response(data, status=status.HTTP_200_OK)
class MyEventsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_tickets = Ticket.objects.filter(user=request.user).select_related('event', 'config_type__ticket_type')
        events_dict = {}
        for ticket in user_tickets:
            event_id = ticket.event.id
            if event_id not in events_dict:
                events_dict[event_id] = {
                    'event': ticket.event.event_name,
                    'event_id': event_id,
                    'date': ticket.event.date,
                    'city': ticket.event.city,
                    'country': ticket.event.country,
                    'status': ticket.event.status,
                    'tickets': []
                }
            events_dict[event_id]['tickets'].append({
                'ticket_id': ticket.id,
                'type': ticket.config_type.ticket_type.ticket_name,
                'amount': ticket.amount,
                'status': ticket.status,
                'unique_code': ticket.unique_code,
                'qr_base64': ticket.get_qr_base64(),
                'date_of_purchase': ticket.date_of_purchase,
                'price_paid': ticket.config_type.price if hasattr(ticket.config_type, 'price') else None
            })
        return Response(list(events_dict.values()), status=status.HTTP_200_OK)
class EventViewSet(viewsets.ModelViewSet):
    """
    API para gestionar events con tipos de boletos y compras.
    Soporta listing, creación (admin), y acciones como cancelar, listar tipos de ticket por event y comprar.
    """
    queryset = Event.objects.prefetch_related('tickets__user')
    authentication_classes = [TokenAuthentication]

    def get_serializer_class(self):
        if self.action in ['buy_ticket']:
            return TicketSerializer
        if self.action in ['ticket_types_available', 'pagar']:
            return TicketTypeEventSerializer
        return EventSerializer

    @extend_schema(
        description="Lista o crea events. Requiere admin para creación.",
        tags=['Events'],
        responses={201: EventSerializer, 400: OpenApiExample('Error en validación')}
    )
    def get_permissions(self):
        admin_actions = ["create", "update", "partial_update", "destroy", "cancelar"]
        if self.action in admin_actions:
            permission_classes = [IsAuthenticated, IsAdminGroup]
        elif self.action in ['buy_ticket', 'pagar']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [perm() for perm in permission_classes]

# Endpoint para validar entrada por QR
class TicketValidationView(APIView):
    """
    Recibe el unique_code (escaneado del QR), valida el ticket y actualiza su estado si corresponde.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unique_code = request.data.get('unique_code')
        if not unique_code:
            return Response({'valid': False, 'error': 'No se recibió el código.'}, status=400)
        try:
            ticket = Ticket.objects.select_related('event', 'user', 'config_type__ticket_type').get(unique_code=unique_code)
        except Ticket.DoesNotExist:
            return Response({'valid': False, 'error': 'Ticket no encontrado.'}, status=404)
        # Validaciones
        if ticket.status == 'usada':
            return Response({'valid': False, 'error': 'Ticket ya fue usada.'}, status=400)
        if ticket.status == 'cancelada':
            return Response({'valid': False, 'error': 'Ticket cancelada.'}, status=400)
        if ticket.status == 'pendiente':
            return Response({'valid': False, 'error': 'Ticket pendiente de pago.'}, status=400)
        # Marcar como usada
        ticket.status = 'usada'
        ticket.save()
        # Auditoría: registrar acceso
        from .models import TicketAccessLog
        ip = request.META.get('REMOTE_ADDR', '')
        device = request.META.get('HTTP_USER_AGENT', '')
        TicketAccessLog.objects.create(
            ticket=ticket,
            accessed_by=request.user,
            ip_address=ip,
            device_info=device
        )
        return Response({
            'valid': True,
            'message': 'Ticket válida. Acceso permitido.',
            'ticket_id': ticket.id,
            'event': ticket.event.event_name,
            'event_id': ticket.event.id,
            'user': ticket.user.name,
            'user_id': ticket.user.id,
            'ticket_type': ticket.config_type.ticket_type.ticket_name,
            'amount': ticket.amount,
            'date_of_purchase': ticket.date_of_purchase,
            'unique_code': ticket.unique_code
        }, status=200)

    @extend_schema(
        description="Lista tipos de boletos disponibles para un event específico.",
        tags=['Events'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path', description='ID del event')],
        responses={200: TicketTypeEventSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def ticket_types_available(self, request, pk=None):
        event = self.get_object()
        if event.status != "activo":
            return Response({"error": "No se pueden consultar tipos para events inactivos."}, status=status.HTTP_400_BAD_REQUEST)
        types = TicketTypeEvent.objects.select_related('ticket_type').filter(event=event)
        serializer = self.get_serializer(types, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Inicia compra de tickets para un event (crea ticket pendiente o gratuita).",
        tags=['Events'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path')],
        request={
            'application/json': {
                'example': {
                    'config_type_id': 7,
                    'amount': 1
                }
            }
        },
        responses={201: EventSerializer, 400: OpenApiExample('Falta tipos_tickets o validación fallida')}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    

# APIView independiente para pago
class PayTicketAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        config_type_id = request.data.get('config_type_id')
        config_type = get_object_or_404(TicketTypeEvent, id=config_type_id, event=event)
        if event.status != "activo":
            return Response({"error": "No se puede pagar para event inactivo."}, status=status.HTTP_400_BAD_REQUEST)
        if config_type.price == 0:
            return Response({"error": "Este tipo de ticket es gratuito."}, status=status.HTTP_400_BAD_REQUEST)

        # Datos de PayU
        api_key = os.getenv("PAYU_API_KEY")
        merchant_id = os.getenv("PAYU_MERCHANT_ID")
        account_id = os.getenv("PAYU_ACCOUNT_ID")
        sandbox = os.getenv("PAYU_SANDBOX", "1")
        # Convertir sandbox a booleano correctamente
        if str(sandbox).lower() in ["true", "1"]:
            sandbox_bool = True
        else:
            sandbox_bool = False
        # Buscar el ticket pendiente del usuario para este evento y tipo
        ticket = Ticket.objects.filter(
            user=request.user,
            event=event,
            config_type=config_type,
            status__in=["pendiente", "comprada"]
        ).order_by('-date_of_purchase').first()
        if not ticket:
            return Response({"error": "No existe ticket pendiente para este usuario y tipo."}, status=status.HTTP_400_BAD_REQUEST)
        reference_code = ticket.unique_code

        # Firma
        amount = str(config_type.price * int(request.data.get('amount', 1)))  # Multiplica por amount
        signature_str = f"{api_key}~{merchant_id}~{reference_code}~{amount}~COP"
        signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

        return Response({
            "sandbox": sandbox_bool,
            "merchantId": merchant_id,
            "accountId": account_id,
            "description": f"{event.event_name} - {config_type.ticket_type.ticket_name}",
            "referenceCode": reference_code,
            "amount": amount,
            "currency": "COP",
            "signature": signature,
            "buyerEmail": request.user.email,
            "confirmationUrl": "https://tuservidor.com/api/payu/confirmacion/",
            "responseUrl": "https://tu-frontend.com/pago-exitoso"
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Cancela un event y notifica inscritos (actualiza tickets si aplica).",
        tags=['Events'],
        responses={200: OpenApiExample('Event cancelado')}
    )
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        event = self.get_object()
        event.status = "cancelado"
        event.save()
        # Actualizar tickets a canceladas
        event.tickets.update(status='cancelada')
        # Aquí enviar notificaciones
        return Response({'status': 'Evento cancelado'}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        event_name = event.event_name
        event.delete()
        return Response(
            {"message": f"El evento '{event_name}' fue eliminado exitosamente."},
            status=status.HTTP_200_OK
        )

class BuyTicketAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.status != "activo":
            return Response({"error": "No se pueden comprar tickets para events inactivos."}, status=status.HTTP_400_BAD_REQUEST)
        config_type_id = request.data.get('config_type_id')
        amount = request.data.get('amount', 1)
        if not config_type_id:
            return Response({"error": "Debe especificar config_type_id (ID de TicketTypeEvent)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            config_type = TicketTypeEvent.objects.get(id=config_type_id, event=event)
        except TicketTypeEvent.DoesNotExist:
            return Response({"error": "Tipo de ticket inválido para este event."}, status=status.HTTP_400_BAD_REQUEST)
        remaining_capacity = config_type.maximun_capacity - config_type.capacity_sold
        if amount > remaining_capacity:
            return Response({"error": f"No hay suficiente aforo disponible. Quedan {remaining_capacity} boletos."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TicketSerializer(
            data={
                'config_type': config_type.id,
                'amount': amount,
                'status': 'comprada' if config_type.price == 0 else 'pendiente'
            },
            context={'config_type': config_type, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(user=request.user)
        if config_type.price == 0:
            config_type.capacity_sold += amount
            config_type.save()
            return Response({
                "message": "ticket gratuita creada exitosamente.",
                "ticket_id": ticket.id,
                "unique_code": ticket.unique_code
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "boleta creada. Procede al pago.",
            "ticket_id": ticket.id,
            "config_type_id": config_type_id,
            "amount": amount,
            "total_a_pagar": f"{float(config_type.price) * amount:.2f}"
        }, status=status.HTTP_201_CREATED)
class TicketTypeViewSet(viewsets.ModelViewSet):
    """
    API completa para tipos de tickets comunes (templates reutilizables entre events).
    - GET /list: Lista todos (público).
    - POST /create: Crea nuevo (admin only).
    - GET/PUT/PATCH/DELETE por ID: Admin only.
    """
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer
    authentication_classes = [TokenAuthentication]

    def get_permissions(self):
        """
        Permissions dinámicas: Admin para write ops, público para read.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdminGroup]  # O IsAdminGroup
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @extend_schema(
        description="Lista todos los tipos de tickets disponibles para usar en events (público).",
        tags=['Tipos de tickets'],
        responses={
            200: TicketTypeSerializer(many=True)
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
    description="Crea un nuevo tipo de ticket común (solo admins). Use 'nombre' de choices como 'GA', 'VIP', etc.",
    tags=['Tipos de tickets'],
    request=TicketTypeSerializer,
    responses={
        201: TicketTypeSerializer,
        400: OpenApiExample(  # Simplificado: OpenApiExample directo para error 400
            'Ejemplo de error de validación',
            value={
                "nombre": ["Este campo es requerido."],
                "price_base": ["Asegúrate de que este valor tenga como máximo 10 dígitos y 2 decimales."]
            },
            description="Respuesta típica para input inválido (e.g., campos faltantes o tipos incorrectos)."
        )
    },
    examples=[
        OpenApiExample(
            'Ejemplo GA',
            value={
                "nombre": "GA",
                "descripcion": "Admisión General - Acceso básico sin asiento asignado.",
                "price_base": "0.00"
            },
            description="Crear tipo Admisión General (gratuito)."
        )
    ]
)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Recupera un tipo de ticket por ID (público).",
        tags=['Tipos de tickets'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path')],
        responses={200: TicketTypeSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Para update/partial_update/destroy: Usa extend_schema similar si necesitas, pero por defecto DRF-Spectacular lo genera auto
    @extend_schema(
        description="Actualiza un tipo de ticket por ID (solo admin).",
        tags=['Tipos de tickets'],
        request=TicketTypeSerializer,
        responses={200: TicketTypeSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Actualización parcial de un tipo de ticket por ID (solo admin).",
        tags=['Tipos de tickets'],
        request=TicketTypeSerializer,
        responses={200: TicketTypeSerializer}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        description="Elimina un tipo de ticket por ID (solo admin). Cuidado: Puede afectar events existentes.",
        tags=['Tipos de tickets'],
        responses={204: OpenApiResponse(description="No Content")}
    )
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {"message": f"Tipo de ticket eliminada exitosamente."},
            status=status.HTTP_200_OK
        )

class PayUConfirmationView(APIView):
    """
    Vista para confirmar pagos de PayU. Actualiza status de ticket al recibir notificación.
    """
    @extend_schema(
        description="Endpoint para confirmación de pagos PayU (solo POST).",
        tags=['Pagos'],
        request=None,  # PayU envía JSON fijo
        responses={200: OpenApiExample('OK - Pago procesado')}
    )
    def post(self, request):
        reference_code = request.data.get("reference_sale")
        status = request.data.get("state_pol")
        transaction_id = request.data.get("transaction_id")

        from rest_framework import status as drf_status
        response_data = {
            "message": "Pago recibido, pero no se pudo procesar el ticket.",
            "reference_code": reference_code,
            "transaction_id": transaction_id,
            "status": "error"
        }
        if status == "4":  # Aprobado en PayU
            from .models import Ticket
            try:
                ticket = get_object_or_404(Ticket, unique_code=reference_code)
                if ticket.status == 'comprada' or ticket.status == 'pendiente':
                    ticket.status = 'pagada'
                    ticket.save()
                    response_data = {
                        "message": "Pago confirmado exitosamente.",
                        "ticket_id": ticket.id,
                        "reference_code": reference_code,
                        "transaction_id": transaction_id,
                        "status": ticket.status
                    }
                else:
                    response_data = {
                        "message": "El ticket ya fue procesado o no está en estado válido.",
                        "ticket_id": ticket.id,
                        "reference_code": reference_code,
                        "transaction_id": transaction_id,
                        "status": ticket.status
                    }
            except Exception:
                response_data = {
                    "message": "No se encontró el ticket con ese código de referencia.",
                    "reference_code": reference_code,
                    "transaction_id": transaction_id,
                    "status": "error"
                }
        elif status == "6":
            response_data["message"] = "Pago rechazado por PayU."
            response_data["status"] = "rechazado"
        elif status == "7":
            response_data["message"] = "Pago pendiente de aprobación."
            response_data["status"] = "pendiente"
        elif status == "5":
            response_data["message"] = "Pago expirado."
            response_data["status"] = "expirado"
        elif status == "8":
            response_data["message"] = "Pago cancelado."
            response_data["status"] = "cancelado"
        return Response(response_data, status=drf_status.HTTP_200_OK)