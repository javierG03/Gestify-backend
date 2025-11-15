"""Endpoints para recuperación de contraseña usando tokens persistentes."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.validators import StrongPasswordValidator
from .email_service import create_password_reset_token, send_password_reset_email
from .models import UserToken

User = get_user_model()

password_validator = StrongPasswordValidator()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        password_validator.validate(data['password'])
        return data

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_email_verified:
            return Response({'error': 'Debes verificar tu email antes de recuperar la contraseña.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            token_value = create_password_reset_token(user)
            send_password_reset_email(user, token_value)
        except ImproperlyConfigured as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'message': 'Se ha enviado el enlace de recuperación al correo.'}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        try:
            user_token = UserToken.objects.get(token=token, token_type=UserToken.TokenType.PASSWORD_RESET)
        except UserToken.DoesNotExist:
            return Response({'error': 'Token inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_token.is_valid():
            user_token.mark_used()
            return Response({'error': 'Token expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        user = user_token.user
        user.set_password(password)
        user.save(update_fields=['password'])
        user_token.mark_used()
        return Response({'message': 'Contraseña restablecida correctamente.'}, status=status.HTTP_200_OK)
