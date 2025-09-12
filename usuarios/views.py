from django.shortcuts import render
from .serializers import CustomUserSerializer, AssignRoleSerializer, RemoveRoleSerializer
from .models import CustomUser
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from .permissions import IsAdminGroup
from django.shortcuts import get_object_or_404



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

class AssignRoleView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    def post(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)
        
        return Response(
            {"message": "Rol asignado correctamente", "role": serializer.validated_data["role"]},
            status=status.HTTP_200_OK
        )

class RemoveRoleView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminGroup]

    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = RemoveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user,serializer.validated_data)

        return Response(
            {"message": f"Rol '{serializer.validated_data['role']}' eliminado correctamente"}, status=status.HTTP_200_OK
        )