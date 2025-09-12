from django.shortcuts import render
from .serializers import EventoSerializer
from .models import Evento
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from usuarios.permissions import IsAdminGroup
import os
import hashlib



# Create your views here.

class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

    def get_permissions(self):
        #Acciones que requieren ser Administrador

        admin_actions = ["create", "update", "partial_update", "destroy", "cancelar"]
        if self.action in admin_actions:
            permission_classes = [IsAuthenticated, IsAdminGroup]
        else:
            permission_classes = [AllowAny]
        return [perm() for perm in permission_classes]

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        evento = self.get_object()
        evento.estado = "cancelado"
        evento.save()
        #Aqui puedo enviar notificaciones a los usuarios inscritos
        return Response({'status': 'Evento cancelado'}, status=status.HTTP_200_OK)
    

    def destroy(self, request, *args, **kwargs):
        evento = self.get_object()
        nombre_evento = evento.nombre  # guardamos el nombre antes de eliminar
        evento.delete()
        return Response(
            {"message": f"El evento '{nombre_evento}' fue eliminado exitosamente."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, method=['post'], Permission_classes=[IsAuthenticated])
    def inscribirse(self, request, pk=None):
        evento = self.get_object()
        usuario = request.user

        if evento.estado != "activo":
            return Response({"error": "No puedes inscribirte a un evento cancelado o cerrado"}, status=status.HTTP_400_BAD_REQUEST)
        
        if evento.inscritos.filter(id=usuario.id).exists():
            return Response(
                {"error": "Ya estás inscrito en este evento."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if evento.inscritos.count() >= evento.aforo:
            return Response(
                {"error": "El aforo máximo ya fue alcanzado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        evento.inscritos.add(usuario)
        return Response({"message": f"Usuario {usuario.name} inscrito al evento {evento.nombre} con exito!"}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        evento = self.get_object()
        usuario = request.user

        if evento.precio == 0:
            return Response({"error": "Este evento es gratuito."}, status=status.HTTP_400_BAD_REQUEST)

        # ⚡ Datos de PayU desde variables de entorno
        api_key = os.getenv("PAYU_API_KEY")
        merchant_id = os.getenv("PAYU_MERCHANT_ID")
        account_id = os.getenv("PAYU_ACCOUNT_ID")
        sandbox = os.getenv("PAYU_SANDBOX", "1")

        # ⚡ Generar referencia de pago
        reference_code = f"EVENTO-{evento.id}-USER-{usuario.id}"

        # ⚡ Generar firma
        signature_str = f"{api_key}~{merchant_id}~{reference_code}~{evento.precio}~COP"
        signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

        # ⚡ Respuesta para el frontend
        return Response({
            "sandbox": bool(int(sandbox)),
            "merchantId": merchant_id,
            "accountId": account_id,
            "description": evento.nombre,
            "referenceCode": reference_code,
            "amount": str(evento.precio),
            "currency": "COP",
            "signature": signature,
            "buyerEmail": usuario.email,
            "confirmationUrl": "https://tuservidor.com/api/payu/confirmacion/",
            "responseUrl": "https://tu-frontend.com/pago-exitoso"
        }, status=status.HTTP_200_OK)
    

class PayUConfirmationView(APIView):
    def post(self, request):
        # Aquí procesas la notificación
        reference_code = request.data.get("reference_sale")
        estado = request.data.get("state_pol")
        
        # Aquí puedes actualizar el estado del evento/inscripción
        # por ejemplo, guardar que el usuario ya pagó
        return Response({"status": "OK"}, status=status.HTTP_200_OK)