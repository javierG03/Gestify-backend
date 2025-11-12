# Endpoint para listar inscritos (tickets) de un evento
import os
import hashlib
from decimal import Decimal
from datetime import datetime, date
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import F, Sum
from django.db import transaction

from usuarios.serializers import CustomUserSerializer
from usuarios.permissions import IsAdminGroup

from .serializers import (
    EventSerializer, TicketTypeEventSerializer, TicketSerializer, TicketTypeSerializer, EventInscritoSerializer, TicketValidationRequestSerializer, MyEventsResponseSerializer,
    TicketActionRequestSerializer,
    BuyTicketResponseSerializer,
    PayTicketResponseSerializer
)

from .models import Event, TicketType, TicketTypeEvent, Ticket

from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, OpenApiTypes

class EventInscritosAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        description="Lista los inscritos (tickets) para un evento específico.",
        responses={200: EventInscritoSerializer(many=True)} # ⬅️ Así le dices qué devuelve
    )

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

    @extend_schema(
        tags=["Mis Eventos"],
        description="Lista los eventos para los cuales el usuario autenticado tiene tickets.",
        responses={200: MyEventsResponseSerializer(many=True)}
    )

    def get(self, request):
        user_tickets = Ticket.objects.filter(user=request.user).select_related('event', 'config_type__ticket_type')
        events_dict = {}
        
        for ticket in user_tickets:
            event = ticket.event
            event_id = event.id
            
            #Usar end_datetime → start_datetime → date
            event_date = event.end_datetime or event.start_datetime or event.date
            
            #Cambiar estado a "usada" si el evento ya pasó
            if event_date and ticket.status == 'comprada':
                now = timezone.now()
                
                # Convertir a datetime si es solo una fecha
                if isinstance(event_date, date) and not isinstance(event_date, datetime):
                    # Es solo una fecha, crear un datetime al final del día
                    event_datetime = datetime.combine(event_date, datetime.max.time())
                    event_datetime = timezone.make_aware(event_datetime)
                else:
                    # Ya es datetime
                    event_datetime = event_date if timezone.is_aware(event_date) else timezone.make_aware(event_date)
                
                # Si el evento pasó, cambiar estado a "usada"
                if event_datetime < now:
                    ticket.status = 'usada'
                    ticket.save()
            
            if event_id not in events_dict:
                events_dict[event_id] = {
                    'event': event.event_name,
                    'event_id': event_id,
                    'date': event_date,
                    'city': event.city,
                    'country': event.country,
                    'status': event.status,
                    'image': event.image.url if event.image else None,
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

    @extend_schema(
        description="Cancela un evento y todos sus tickets asociados (solo admin).",
        tags=['Events'],
        responses={
            200: OpenApiResponse( # 👈 Envuelve el ejemplo
                description="Evento cancelado exitosamente.",
                examples=[
                    OpenApiExample(
                        'Respuesta Exitosa',
                        value={'status': 'evento cancelado', 'tickets_cancelados': 50, 'cupos_liberados': 45}
                    )
                ]
            ),
            400: OpenApiResponse( # 👈 Envuelve el ejemplo
                description="Error - El evento no se puede cancelar.",
                examples=[
                    OpenApiExample(
                        'Error - Ya cancelado',
                        value={'error': 'Este evento ya está cancelado.'}
                    )
                ]
            ),
            404: OpenApiResponse(description="No encontrado.") # 👈 Simple para 404
        }
    )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Endpoint para cancelar un evento.
        - Cambia el estado del Event a 'cancelado'.
        - Cambia el estado de todos los Tickets a 'cancelada'.
        - Resta el 'amount' de los tickets 'comprada' del 'capacity_sold' 
          en sus respectivos TicketTypeEvent.
        """
        
        event = self.get_object() 

        if event.status == 'cancelado':
            return Response(
                {'error': 'Este evento ya está cancelado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    
        if event.start_datetime and event.start_datetime < timezone.now():
            return Response(
                {'error': 'No se puede cancelar un evento que ya ha comenzado o finalizado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    
        try:
            with transaction.atomic():
                tickets_a_cancelar = event.tickets.exclude(status='cancelada')
                tickets_comprados = tickets_a_cancelar.filter(status='comprada')

                cupos_a_liberar = tickets_comprados.values(
                    'config_type' 
                ).annotate(
                    total_a_restar=Sum('amount') 
                ).values('config_type', 'total_a_restar') 

                cupos_liberados_total = 0
                for item in cupos_a_liberar:
                    TicketTypeEvent.objects.filter(id=item['config_type']).update(
                        capacity_sold=F('capacity_sold') - item['total_a_restar']
                    )
                    cupos_liberados_total += item['total_a_restar']

                count_tickets_cancelados = tickets_a_cancelar.update(status='cancelada')

                event.status = 'cancelado'
                event.save()

                return Response(
                    {
                        'status': 'evento cancelado',
                        'tickets_cancelados': count_tickets_cancelados,
                        'cupos_liberados': cupos_liberados_total
                    },
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            return Response(
                {'error': f'Error interno al cancelar el evento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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

    
# Endpoint para validar entrada por QR
class TicketValidationView(APIView):
    """
    Recibe el unique_code (escaneado del QR), valida el ticket y actualiza su estado si corresponde.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tickets"],
        description="Valida un ticket usando su código QR (unique_code).",
        request=TicketValidationRequestSerializer, # ⬅️ Esto es lo que recibe
        responses={
            200: OpenApiResponse(description="Ticket válido"),
            400: OpenApiResponse(description="Ticket ya usado o pendiente de pago"),
            404: OpenApiResponse(description="Ticket no encontrado")
        }
    )

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
    """
    API para preparar datos de pago en PayU.
    POST /api/events/{id}/pay/
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Pagos"],
        description="Prepara los datos para la pasarela de pago PayU.",
        request=TicketActionRequestSerializer,
        responses={200: PayTicketResponseSerializer}
    )

    def post(self, request, pk):
        # Obtener evento y tipo de ticket
        event = get_object_or_404(Event, pk=pk)
        config_type_id = request.data.get('config_type_id')
        config_type = get_object_or_404(TicketTypeEvent, id=config_type_id, event=event)
        
        # Validaciones
        if event.status != "activo":
            return Response(
                {"error": "No se puede pagar para evento inactivo."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if config_type.price == 0:
            return Response(
                {"error": "Este tipo de ticket es gratuito."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener credenciales de PayU
        api_key = os.getenv("PAYU_API_KEY")
        merchant_id = os.getenv("PAYU_MERCHANT_ID")
        account_id = os.getenv("PAYU_ACCOUNT_ID")
        sandbox = os.getenv("PAYU_SANDBOX", "1")
        sandbox_bool = str(sandbox).lower() in ["true", "1"]

        # Buscar ticket pendiente
        ticket = Ticket.objects.filter(
            user=request.user,
            event=event,
            config_type=config_type,
            status__in=["pendiente", "comprada"]
        ).order_by('-date_of_purchase').first()
        
        if not ticket:
            return Response(
                {"error": "No existe ticket pendiente para este usuario y tipo."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reference_code = ticket.unique_code

        # ✅ IMPORTANTE: amount es CANTIDAD, no monto
        quantity = int(request.data.get('amount', 1))
        amount = str(int(config_type.price * quantity))
        
        # Generar firma
        signature_str = f"{api_key}~{merchant_id}~{reference_code}~{amount}~COP"
        signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

        # ✅ URLs dinámicas desde settings/env
        from django.conf import settings
        backend_base_url = settings.BACKEND_BASE_URL or request.build_absolute_uri('/')[:-1]
        confirmation_url = f"{backend_base_url}/api/events/payu/confirmation/"
        response_url = f"{settings.FRONTEND_BASE_URL}/pago-exitoso"

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
            "confirmationUrl": confirmation_url,  # ✅ DINÁMICO
            "responseUrl": response_url,          # ✅ DINÁMICO
        }, status=status.HTTP_200_OK)


class BuyTicketAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tickets"],
        description="Inicia el proceso de compra de un ticket.",
        request=TicketActionRequestSerializer,
        responses={201: BuyTicketResponseSerializer}
    )

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
        description="Crea un nuevo tipo de ticket común (solo admins).",
        tags=['Tipos de tickets'],
        request=TicketTypeSerializer,
        responses={
            201: TicketTypeSerializer,
            400: OpenApiResponse( # ⬅️ 1. Envuelve con OpenApiResponse
                description="Error de validación",
                examples=[       # ⬅️ 2. Pasa los ejemplos como una lista
                    OpenApiExample(
                        'Ejemplo de error',
                        value={"nombre": ["Este campo es requerido."]}
                    )
                ]
            )
        },
        examples=[ # ⬅️ 'examples' para el request va aquí
            OpenApiExample(
                'Ejemplo GA',
                value={"nombre": "GA", "descripcion": "Admisión General..."}
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
    Webhook para confirmar pagos de PayU.
    ⚠️ IMPORTANTE: Sin autenticación (PayU no envía token)
    """
    # ✅ QUITAR la autenticación y permisos
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        description="Webhook para confirmación de pagos PayU (sin autenticación).",
        tags=['Pagos'],
        request=None,
        responses={
            200: OpenApiResponse(
                description="Respuesta del servidor a la confirmación de PayU.",
                examples=[
                    OpenApiExample(
                        'Ejemplo: Pago Aprobado',
                        value={
                            "message": "Pago confirmado exitosamente.",
                            "ticket_id": 101,
                            "reference_code": "ref-12345",
                            "transaction_id": "txn-abcde",
                            "status": "comprada"
                        },
                        description="Cuando PayU reporta 'state_pol' = 4."
                    ),
                    OpenApiExample(
                        'Ejemplo: Pago Rechazado',
                        value={
                            "message": "Pago rechazado por PayU.",
                            "reference_code": "ref-67890",
                            "transaction_id": "txn-fghij",
                            "status": "rechazado"
                        },
                        description="Cuando PayU reporta 'state_pol' = 6."
                    )
                ]
            )
        }
    )
    
    def post(self, request):
        """
        Procesa confirmación de PayU SIN requerin autenticación.
        """
        reference_code = request.data.get("reference_sale")
        state_pol = request.data.get("state_pol")
        transaction_id = request.data.get("transaction_id")
        
        print(f"\n🔔 PayU Confirmation recibida:")
        print(f"   Reference: {reference_code}")
        print(f"   State: {state_pol}")
        print(f"   Transaction ID: {transaction_id}\n")
        
        from rest_framework import status as drf_status
        
        response_data = {
            "message": "Pago recibido, pero no se pudo procesar el ticket.",
            "reference_code": reference_code,
            "transaction_id": transaction_id,
            "status": "error"
        }
        
        # ========== PAGO APROBADO (state_pol = 4) ==========
        if state_pol == "4":
            print("✅ Pago APROBADO")
            try:
                ticket = get_object_or_404(Ticket, unique_code=reference_code)
                if ticket.status in ['comprada', 'pendiente']:
                    ticket.status = 'comprada'
                    ticket.save()
                    
                    print(f"✅ Ticket {reference_code} actualizado a COMPRADA\n")
                    
                    response_data = {
                        "message": "Pago confirmado exitosamente.",
                        "ticket_id": ticket.id,
                        "reference_code": reference_code,
                        "transaction_id": transaction_id,
                        "status": ticket.status
                    }
                else:
                    print(f"⚠️ Ticket ya procesado. Status: {ticket.status}\n")
                    response_data = {
                        "message": "El ticket ya fue procesado.",
                        "ticket_id": ticket.id,
                        "reference_code": reference_code,
                        "transaction_id": transaction_id,
                        "status": ticket.status
                    }
            except Ticket.DoesNotExist:
                print(f"❌ Ticket no encontrado: {reference_code}\n")
                response_data = {
                    "message": "No se encontró el ticket.",
                    "reference_code": reference_code,
                    "transaction_id": transaction_id,
                    "status": "error"
                }
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")
                response_data = {
                    "message": f"Error: {str(e)}",
                    "reference_code": reference_code,
                    "transaction_id": transaction_id,
                    "status": "error"
                }
        
        elif state_pol == "6":
            print("❌ Pago RECHAZADO\n")
            response_data["message"] = "Pago rechazado."
            response_data["status"] = "rechazado"
        
        elif state_pol == "7":
            print("⏳ Pago PENDIENTE\n")
            response_data["message"] = "Pago pendiente."
            response_data["status"] = "pendiente"
        
        elif state_pol == "5":
            print("⏱️ Pago EXPIRADO\n")
            response_data["message"] = "Pago expirado."
            response_data["status"] = "expirado"
        
        elif state_pol == "8":
            print("🚫 Pago CANCELADO\n")
            response_data["message"] = "Pago cancelado."
            response_data["status"] = "cancelado"
        
        return Response(response_data, status=drf_status.HTTP_200_OK)