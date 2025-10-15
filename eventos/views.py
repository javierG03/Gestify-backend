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
    responses={
        201: OpenApiResponse(description="ticket creada (gratuita o pendiente pago)."),
        400: OpenApiResponse(description="Error: Aforo insuficiente o event inactivo.")
    }
)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated]) 
    def buy_ticket(self, request, pk=None):
        event = self.get_object()
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
        
        # CRÍTICO: Crea serializer y setea usuario automáticamente desde request.user
        # No requiere 'usuario_id' en body
        serializer = self.get_serializer(
            data={
            'config_type': config_type.id,
            'amount': amount,
            'status': 'comprada' if config_type.price == 0 else 'pendiente'  
            },
            context={'config_type': config_type, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Asigna usuario del request (autenticado)
        ticket = serializer.save(user=request.user)  
        
        if config_type.price == 0:
            # Gratuita: Actualiza aforo inmediatamente
            config_type.capacity_sold += amount
            config_type.save()
            return Response({
                "message": "ticket gratuita creada exitosamente.",
                "ticket_id": ticket.id,
                "unique_code": ticket.unique_code 
            }, status=status.HTTP_201_CREATED)
        
        # Pagada: Retorna ID para proceder a /pay/
        return Response({
            "message": "boleta creada. Procede al pago.",
            "ticket_id": ticket.id,
            "config_type_id": config_type_id,
            "amount": amount,
            "total_a_pagar": f"{float(config_type.price) * amount:.2f}"
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
    operation_id='create_event',
    description="Crea un event con al menos un tipo de ticket requerido en 'tipos_tickets'.",
    tags=['Events'],
    request={
        'application/json': {
            'example': {
                'event_name': 'Proyecto X',
                'description': 'fiesta de Locos',
                'date': '2025-10-27',
                'city': 'Neiva',
                'country': 'Colombia',
                'tickets_types': [
                    {
                        'ticket_type_id': 1,  # ID de un TicketType existente (e.g., GA)
                        'price': 50.00,
                        'maximun_capacity': 100
                    },
                    {
                        'ticket_type_id': 2,  # ID de VIP
                        'price': 100.00,
                        'maximun_capacity': 20
                    }
                ]
            }
        }
    },
    responses={201: EventSerializer, 400: OpenApiExample('Falta tipos_tickets o validación fallida')}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        description="Genera datos para pago de ticket con PayU (para tipos pagados).",
        tags=['Pagos'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path'), OpenApiParameter(name='config_type_id', type=int, location='query')],
        responses={200: OpenApiExample('Datos de PayU para formulario'), 400: OpenApiExample('Event gratuito o inactivo')}
    )
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        event = self.get_object()
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
        reference_code = f"ticket-{config_type_id}-USER-{request.user.id}"

        # Firma
        amount = str(config_type.price * int(request.data.get('amount', 1)))  # Multiplica por amount
        signature_str = f"{api_key}~{merchant_id}~{reference_code}~{amount}~COP"
        signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

        return Response({
            "sandbox": bool(int(sandbox)),
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

        if status == "4":  # Aprobado en PayU
            # Extraer ticket_id de reference_code (e.g., ticket-123-...)
            try:
                ticket_id = int(reference_code.split('-')[1])
                ticket = get_object_or_404(ticket, id=ticket_id)
                if ticket.status == 'comprada':  # Pendiente
                    ticket.status = 'usada'  # O 'pagada', ajusta según lógica
                    ticket.save()
                    # Opcional: Enviar email de confirmación
            except (ValueError, IndexError):
                pass  # Referencia inválida

        return Response({"status": "OK"}, status=status.HTTP_200_OK)