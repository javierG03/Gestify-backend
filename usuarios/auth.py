from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group
from .models import CustomUser
from .serializers import CustomUserSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny

class CustomUserRegisterView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        group, created = Group.objects.get_or_create(name="Participante")
        user.groups.add(group)
        return Response({"message": "Te has Registrado Exitosamente"}, status=status.HTTP_201_CREATED)
    
class CustomUserLoginView(APIView):
    permission_classes = []
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        print("Email recibido:", email)
        print("Password recibido:", password)

        user = authenticate(request, username=email, password=password)

        print("Usuario autenticado:", user)
        
        if user:
            # Crear o recuperar token
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
    
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        
        validate_password(new_password, user)
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)