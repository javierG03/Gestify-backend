"""
usuarios/views.py
Vistas principales del módulo de usuarios. Clean code, docstrings y organización lógica.
"""

from django.shortcuts import get_object_or_404
from django.core.exceptions import ImproperlyConfigured
from rest_framework import generics, status, serializers
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema
from .serializers import (
    CustomUserSerializer, AssignRoleSerializer, EmptySerializer, RemoveRoleSerializer,
    UserRegisterSerializer, UserLoginSerializer, ChangePasswordSerializer
)
from .models import CustomUser, UserToken, DocumentType
from .permissions import IsAdminGroup, IsSelfOrAdmin
from .email_service import (
    send_confirmation_email,
    create_email_verification_token,
    send_verification_email,
)
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

class UserProfileUpdateView(generics.UpdateAPIView):
    """Permite al usuario autenticado editar su perfil."""
    serializer_class = CustomUserSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

class CustomUserListView(ListAPIView):
    """Lista todos los usuarios (solo admin)."""
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(tags=["Usuarios"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class CustomUserRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """Permite ver, editar o eliminar un usuario (solo admin o el propio usuario)."""
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    authentication_classes = [TokenAuthentication]

    permission_classes = [IsAuthenticated, IsSelfOrAdmin]

    def get_object(self):
        obj = get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    # El decorador debe ir sobre el método, no sobre la clase
    @extend_schema(tags=["Usuarios"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Usuarios"])
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(tags=["Usuarios"])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["Usuarios"])
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

class AssignRoleView(generics.GenericAPIView):
    """Asigna un rol a un usuario (solo admin)."""
    serializer_class = AssignRoleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(
        request=AssignRoleSerializer,
        responses={200: AssignRoleSerializer},
        tags=["Usuarios"]
    )
    def post(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)

        return Response(
            {"message": "Rol asignado correctamente", "role": serializer.validated_data["role"]},
            status=status.HTTP_200_OK
        )

class RemoveRoleView(generics.GenericAPIView):
    """Elimina un rol de un usuario (solo admin)."""
    serializer_class = RemoveRoleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(
        request=RemoveRoleSerializer,
        responses={200: RemoveRoleSerializer(many=False)},
        tags=["Usuarios"]
    )
    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = RemoveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)

        return Response(
            {"message": f"Rol '{serializer.validated_data['role']}' eliminado correctamente"}, status=status.HTTP_200_OK
        )

class CustomUserRegisterView(generics.GenericAPIView):
    """Registra un nuevo usuario."""
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegisterSerializer,
        responses={201: UserRegisterSerializer(many=False)},
        tags=["Autenticación"]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.is_active = False
        user.is_email_verified = False
        user.save(update_fields=["is_active", "is_email_verified"])
        try:
            token_value = create_email_verification_token(user)
            send_verification_email(user, token_value)
        except ImproperlyConfigured as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"message": "Registro exitoso. Revisa tu correo para verificar tu cuenta."},
            status=status.HTTP_201_CREATED,
        )

class CustomUserLoginView(generics.GenericAPIView):
    """Inicia sesión un usuario registrado."""
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserLoginSerializer,
        responses={200: UserLoginSerializer(many=False)},
        tags=["Autenticación"]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)

        if user:
            if not user.is_email_verified:
                return Response(
                    {"error": "Debes verificar tu correo electrónico antes de iniciar sesión."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not user.is_active:
                return Response(
                    {"error": "Tu cuenta está inactiva. Contacta con soporte."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "token": token.key,
                "user_id": user.id,
                "email": user.email,
                "username": user.username
            }, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

class ChangePasswordView(generics.GenericAPIView):
    """Cambia la contraseña del usuario autenticado."""
    serializer_class = ChangePasswordSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: ChangePasswordSerializer(many=False)},
        tags=["Autenticación"]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        validate_password(new_password, user)
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

class VerifyEmailView(generics.GenericAPIView):
    """Verifica el correo electrónico del usuario."""
    permission_classes = [AllowAny]
    serializer_class = EmptySerializer

    @extend_schema(tags=["Autenticación"], operation_id="verify_email", description="Verificación de correo electrónico")
    def get(self, request):
        token_value = request.GET.get('token')
        if not token_value:
            return Response({'error': 'Token de verificación no proporcionado.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_token = UserToken.objects.get(token=token_value, token_type=UserToken.TokenType.EMAIL_VERIFICATION)
        except UserToken.DoesNotExist:
            return Response({'error': 'Token inválido o expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Si el usuario ya está verificado, es éxito
        if user_token.user.is_email_verified:
            return Response({'message': '¡Tu correo ya fue verificado anteriormente!'}, status=status.HTTP_200_OK)
        
        # Verificar si el token es válido
        if not user_token.is_valid():
            user_token.mark_used()
            return Response({'error': 'Token inválido o expirado. Solicita un nuevo link de verificación.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = user_token.user
            user.is_active = True
            user.is_email_verified = True
            user.save(update_fields=['is_active', 'is_email_verified'])
            user_token.mark_used()
            send_confirmation_email(user)
            return Response({'message': '¡Correo verificado exitosamente! Tu cuenta está activa.'}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

class DocumentTypeListView(generics.ListAPIView):
    """Lista todos los tipos de documentos disponibles."""
    queryset = DocumentType.objects.all().order_by("name")
    serializer_class = serializers.ModelSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Define un serializador simple para DocumentType."""
        class DocumentTypeSerializer(serializers.ModelSerializer):
            class Meta:
                model = DocumentType
                fields = ['id', 'name', 'code']
        return DocumentTypeSerializer

    @extend_schema(tags=["Catálogos"], operation_id="document_type_list")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DebugEmailView(generics.GenericAPIView):
    """
    SOLO PARA DESARROLLO: Prueba la configuración de emails.
    """
    permission_classes = [AllowAny]
    serializer_class = EmptySerializer

    @extend_schema(
        tags=["Debug"],
        operation_id="debug_email",
        description="[SOLO DESARROLLO] Prueba el envío de emails"
    )
    def post(self, request):
        from django.core.mail import send_mail
        from django.conf import settings

        email = request.data.get('email', 'gestifycol@gmail.com')
        
        debug_info = {
            'EMAIL_BACKEND': settings.EMAIL_BACKEND,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            'TEST_EMAIL': email,
        }

        try:
            result = send_mail(
                'Test Email from Gestify Debug',
                'Este es un email de prueba desde Gestify. Si recibiste esto, los emails están funcionando correctamente.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
            debug_info['status'] = 'success'
            debug_info['message'] = f'Email enviado exitosamente ({result} message sent)'
            return Response(debug_info, status=status.HTTP_200_OK)
        except Exception as e:
            debug_info['status'] = 'error'
            debug_info['error'] = str(e)
            debug_info['error_type'] = type(e).__name__
            return Response(debug_info, status=status.HTTP_400_BAD_REQUEST)

