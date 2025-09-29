from django.shortcuts import render, get_object_or_404
from .serializers import CustomUserSerializer, AssignRoleSerializer, RemoveRoleSerializer, UserRegisterSerializer, UserLoginSerializer, ChangePasswordSerializer
from .models import CustomUser
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import status
from .permissions import IsAdminGroup
from drf_spectacular.utils import extend_schema
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group


# Create your views here.
class CustomUserListView(ListAPIView):
    allowed_methods = ['GET']
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    

class CustomUserRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    allowed_methods = ['GET', 'PUT', 'PATCH', 'DELETE']
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

class AssignRoleView(GenericAPIView):
    serializer_class = AssignRoleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(
        request=AssignRoleSerializer,
        responses={200: AssignRoleSerializer}
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

class RemoveRoleView(GenericAPIView):  # Cambiado de APIView a GenericAPIView
    serializer_class = RemoveRoleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    @extend_schema(
        request=RemoveRoleSerializer,
        responses={200: RemoveRoleSerializer(many=False)}
    )
    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = RemoveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)

        return Response(
            {"message": f"Rol '{serializer.validated_data['role']}' eliminado correctamente"}, status=status.HTTP_200_OK
        )

class CustomUserRegisterView(GenericAPIView):  # Cambiado de APIView a GenericAPIView
    serializer_class = UserRegisterSerializer  # Serializer agregado
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegisterSerializer,
        responses={201: UserRegisterSerializer(many=False)}
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        group, created = Group.objects.get_or_create(name="Participante")
        user.groups.add(group)
        return Response({"message": "Te has Registrado Exitosamente"}, status=status.HTTP_201_CREATED)
    
class CustomUserLoginView(GenericAPIView):  # Cambiado de APIView a GenericAPIView
    serializer_class = UserLoginSerializer  # Serializer agregado
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserLoginSerializer,
        responses={200: UserLoginSerializer(many=False)}
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)
        
        if user:
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
    
class ChangePasswordView(GenericAPIView):  # Cambiado de APIView a GenericAPIView
    serializer_class = ChangePasswordSerializer  # Serializer agregado
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: ChangePasswordSerializer(many=False)}
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