from django.shortcuts import render, get_object_or_404
from .serializers import (
    EventoSerializer, TipoBoletaEventoSerializer, BoletaSerializer, TipoBoletaSerializer
)
from .models import Evento, TipoBoleta, TipoBoletaEvento, Boleta
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


class EventoViewSet(viewsets.ModelViewSet):
    """
    API para gestionar eventos con tipos de boletos y compras.
    Soporta listing, creación (admin), y acciones como cancelar, listar tipos de boleta por evento y comprar.
    """
    queryset = Evento.objects.prefetch_related('boletas__usuario')
    authentication_classes = [TokenAuthentication]

    def get_serializer_class(self):
        if self.action in ['comprar_boleta']:
            return BoletaSerializer
        if self.action in ['tipos_disponibles', 'pagar']:
            return TipoBoletaEventoSerializer
        return EventoSerializer

    @extend_schema(
        description="Lista o crea eventos. Requiere admin para creación.",
        tags=['Eventos'],
        responses={201: EventoSerializer, 400: OpenApiExample('Error en validación')}
    )
    def get_permissions(self):
        admin_actions = ["create", "update", "partial_update", "destroy", "cancelar"]
        if self.action in admin_actions:
            permission_classes = [IsAuthenticated, IsAdminGroup]
        elif self.action in ['comprar_boleta', 'pagar']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [perm() for perm in permission_classes]

    @extend_schema(
        description="Lista tipos de boletos disponibles para un evento específico.",
        tags=['Eventos'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path', description='ID del evento')],
        responses={200: TipoBoletaEventoSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def tipos_disponibles(self, request, pk=None):
        evento = self.get_object()
        if evento.estado != "activo":
            return Response({"error": "No se pueden consultar tipos para eventos inactivos."}, status=status.HTTP_400_BAD_REQUEST)
        tipos = TipoBoletaEvento.objects.select_related('tipo_boleta').filter(evento=evento)
        serializer = self.get_serializer(tipos, many=True)
        return Response(serializer.data)

    @extend_schema(
    description="Inicia compra de boletas para un evento (crea Boleta pendiente o gratuita).",
    tags=['Eventos'],
    parameters=[OpenApiParameter(name='pk', type=int, location='path')],
    request={
        'application/json': {
            'example': {
                'tipo_config_id': 7,
                'cantidad': 1
            }
        }
    },
    responses={
        201: OpenApiResponse(description="Boleta creada (gratuita o pendiente pago)."),
        400: OpenApiResponse(description="Error: Aforo insuficiente o evento inactivo.")
    }
)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated]) 
    def comprar_boleta(self, request, pk=None):
        evento = self.get_object()
        if evento.estado != "activo":
            return Response({"error": "No se pueden comprar boletas para eventos inactivos."}, status=status.HTTP_400_BAD_REQUEST)
        
        tipo_config_id = request.data.get('tipo_config_id')
        cantidad = request.data.get('cantidad', 1)
        
        if not tipo_config_id:
            return Response({"error": "Debe especificar tipo_config_id (ID de TipoBoletaEvento)."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tipo_config = TipoBoletaEvento.objects.get(id=tipo_config_id, evento=evento)
        except TipoBoletaEvento.DoesNotExist:
            return Response({"error": "Tipo de boleta inválido para este evento."}, status=status.HTTP_400_BAD_REQUEST)
        
        aforo_restante = tipo_config.aforo_maximo - tipo_config.aforo_vendido
        if cantidad > aforo_restante:
            return Response({"error": f"No hay suficiente aforo disponible. Quedan {aforo_restante} boletos."}, status=status.HTTP_400_BAD_REQUEST)
        
        # CRÍTICO: Crea serializer y setea usuario automáticamente desde request.user
        # No requiere 'usuario_id' en body
        serializer = self.get_serializer(data={
            'tipo_config': tipo_config.id,
            'cantidad': cantidad,
            'estado': 'comprada' if tipo_config.precio == 0 else 'pendiente'  
        })
        serializer.is_valid(raise_exception=True)
        
        # Asigna usuario del request (autenticado)
        boleta = serializer.save(usuario=request.user)  
        
        if tipo_config.precio == 0:
            # Gratuita: Actualiza aforo inmediatamente
            tipo_config.aforo_vendido += cantidad
            tipo_config.save()
            return Response({
                "message": "Boleta gratuita creada exitosamente.",
                "boleta_id": boleta.id,
                "codigo_unico": boleta.codigo_unico 
            }, status=status.HTTP_201_CREATED)
        
        # Pagada: Retorna ID para proceder a /pay/
        return Response({
            "message": "Boleta creada. Procede al pago.",
            "boleta_id": boleta.id,
            "tipo_config_id": tipo_config_id,
            "cantidad": cantidad,
            "total_a_pagar": f"{float(tipo_config.precio) * cantidad:.2f}"
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
    operation_id='create_evento',
    description="Crea un evento con al menos un tipo de boleta requerido en 'tipos_data'.",
    tags=['Eventos'],
    request={
        'application/json': {
            'example': {
                'nombre': 'fiesta de daniela',
                'descripcion': 'fiesta de 20 años en la casa de daniela',
                'fecha': '2025-10-27',
                'ciudad': 'Neiva',
                'pais': 'Colombia',
                'tipos_data': [
                    {
                        'tipo_boleta_id': 1,  # ID de un TipoBoleta existente (e.g., GA)
                        'precio': 50.00,
                        'aforo_maximo': 100
                    },
                    {
                        'tipo_boleta_id': 2,  # ID de VIP
                        'precio': 100.00,
                        'aforo_maximo': 20
                    }
                ]
            }
        }
    },
    responses={201: EventoSerializer, 400: OpenApiExample('Falta tipos_data o validación fallida')}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        description="Genera datos para pago de boleta con PayU (para tipos pagados).",
        tags=['Pagos'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path'), OpenApiParameter(name='tipo_config_id', type=int, location='query')],
        responses={200: OpenApiExample('Datos de PayU para formulario'), 400: OpenApiExample('Evento gratuito o inactivo')}
    )
    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        evento = self.get_object()
        tipo_config_id = request.data.get('tipo_config_id')
        tipo_config = get_object_or_404(TipoBoletaEvento, id=tipo_config_id, evento=evento)
        if evento.estado != "activo":
            return Response({"error": "No se puede pagar para evento inactivo."}, status=status.HTTP_400_BAD_REQUEST)
        if tipo_config.precio == 0:
            return Response({"error": "Este tipo de boleta es gratuito."}, status=status.HTTP_400_BAD_REQUEST)

        # Datos de PayU
        api_key = os.getenv("PAYU_API_KEY")
        merchant_id = os.getenv("PAYU_MERCHANT_ID")
        account_id = os.getenv("PAYU_ACCOUNT_ID")
        sandbox = os.getenv("PAYU_SANDBOX", "1")
        reference_code = f"BOLETA-{tipo_config_id}-USER-{request.user.id}"

        # Firma
        amount = str(tipo_config.precio * int(request.data.get('cantidad', 1)))  # Multiplica por cantidad
        signature_str = f"{api_key}~{merchant_id}~{reference_code}~{amount}~COP"
        signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

        return Response({
            "sandbox": bool(int(sandbox)),
            "merchantId": merchant_id,
            "accountId": account_id,
            "description": f"{evento.nombre} - {tipo_config.tipo_boleta.nombre}",
            "referenceCode": reference_code,
            "amount": amount,
            "currency": "COP",
            "signature": signature,
            "buyerEmail": request.user.email,
            "confirmationUrl": "https://tuservidor.com/api/payu/confirmacion/",
            "responseUrl": "https://tu-frontend.com/pago-exitoso"
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Cancela un evento y notifica inscritos (actualiza boletas si aplica).",
        tags=['Eventos'],
        responses={200: OpenApiExample('Evento cancelado')}
    )
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        evento = self.get_object()
        evento.estado = "cancelado"
        evento.save()
        # Actualizar boletas a canceladas
        evento.boletas.update(estado='cancelada')
        # Aquí enviar notificaciones
        return Response({'status': 'Evento cancelado'}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        evento = self.get_object()
        nombre_evento = evento.nombre
        evento.delete()
        return Response(
            {"message": f"El evento '{nombre_evento}' fue eliminado exitosamente."},
            status=status.HTTP_200_OK
        )

class TipoBoletaViewSet(viewsets.ModelViewSet):
    """
    API completa para tipos de boletas comunes (templates reutilizables entre eventos).
    - GET /list: Lista todos (público).
    - POST /create: Crea nuevo (admin only).
    - GET/PUT/PATCH/DELETE por ID: Admin only.
    """
    queryset = TipoBoleta.objects.all()
    serializer_class = TipoBoletaSerializer
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
        description="Lista todos los tipos de boletas disponibles para usar en eventos (público).",
        tags=['Tipos de Boletas'],
        responses={
            200: TipoBoletaSerializer(many=True)
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
    description="Crea un nuevo tipo de boleta común (solo admins). Use 'nombre' de choices como 'GA', 'VIP', etc.",
    tags=['Tipos de Boletas'],
    request=TipoBoletaSerializer,
    responses={
        201: TipoBoletaSerializer,
        400: OpenApiExample(  # Simplificado: OpenApiExample directo para error 400
            'Ejemplo de error de validación',
            value={
                "nombre": ["Este campo es requerido."],
                "precio_base": ["Asegúrate de que este valor tenga como máximo 10 dígitos y 2 decimales."]
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
                "precio_base": "0.00"
            },
            description="Crear tipo Admisión General (gratuito)."
        )
    ]
)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Recupera un tipo de boleta por ID (público).",
        tags=['Tipos de Boletas'],
        parameters=[OpenApiParameter(name='pk', type=int, location='path')],
        responses={200: TipoBoletaSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Para update/partial_update/destroy: Usa extend_schema similar si necesitas, pero por defecto DRF-Spectacular lo genera auto
    @extend_schema(
        description="Actualiza un tipo de boleta por ID (solo admin).",
        tags=['Tipos de Boletas'],
        request=TipoBoletaSerializer,
        responses={200: TipoBoletaSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Actualización parcial de un tipo de boleta por ID (solo admin).",
        tags=['Tipos de Boletas'],
        request=TipoBoletaSerializer,
        responses={200: TipoBoletaSerializer}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        description="Elimina un tipo de boleta por ID (solo admin). Cuidado: Puede afectar eventos existentes.",
        tags=['Tipos de Boletas'],
        responses={204: OpenApiResponse(description="No Content")}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class PayUConfirmationView(APIView):
    """
    Vista para confirmar pagos de PayU. Actualiza estado de boleta al recibir notificación.
    """
    @extend_schema(
        description="Endpoint para confirmación de pagos PayU (solo POST).",
        tags=['Pagos'],
        request=None,  # PayU envía JSON fijo
        responses={200: OpenApiExample('OK - Pago procesado')}
    )
    def post(self, request):
        reference_code = request.data.get("reference_sale")
        estado = request.data.get("state_pol")
        transaction_id = request.data.get("transaction_id")

        if estado == "4":  # Aprobado en PayU
            # Extraer boleta_id de reference_code (e.g., BOLETA-123-...)
            try:
                boleta_id = int(reference_code.split('-')[1])
                boleta = get_object_or_404(Boleta, id=boleta_id)
                if boleta.estado == 'comprada':  # Pendiente
                    boleta.estado = 'usada'  # O 'pagada', ajusta según lógica
                    boleta.save()
                    # Opcional: Enviar email de confirmación
            except (ValueError, IndexError):
                pass  # Referencia inválida

        return Response({"status": "OK"}, status=status.HTTP_200_OK)