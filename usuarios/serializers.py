from .models import CustomUser
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from eventos.models import Evento
from drf_spectacular.utils import extend_schema_field

User = get_user_model()

class SimpleEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = ['id', 'nombre', 'fecha', 'estado']

class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    eventos_inscritos = SimpleEventoSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'password', 'role', 'eventos_inscritos']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        user = super().create(validated_data)
    
        # asignar grupo por defecto
        try:
            group = Group.objects.get(name="Participante")
            user.groups.add(group)
        except Group.DoesNotExist:
            # si el grupo no existe, no hacemos nada
            pass

        return user
            

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
    
    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_role (self, obj):
        return list(obj.groups.values_list('name',flat=True))


class AssignRoleSerializer(serializers.Serializer):
    role = serializers.CharField(write_only=True)

    def validate_role(self, value):
        if not Group.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"El rol '{value}' no existe")
        return value

    def update(self, instance, validated_data):
        role_name = validated_data.get("role")
        instance.groups.clear()
        group = Group.objects.get(name=role_name)
        instance.groups.add(group)
        instance.save()
        return instance
    
class RemoveRoleSerializer(serializers.Serializer):
    role = serializers.CharField()

    def update(self, instance, validated_data):
        role_name = validated_data.get("role")
        instance.groups.remove(*instance.groups.filter(name=role_name))
        return instance
    
# Serializers nuevos para las vistas de auth (para documentación)
class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'password']  # Ajusta según los campos requeridos
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)  # Usa create_user si existe, o ajusta

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

