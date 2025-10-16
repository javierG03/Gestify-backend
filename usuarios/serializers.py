from .models import CustomUser
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from eventos.models import Event
from drf_spectacular.utils import extend_schema_field

User = get_user_model()

class SimpleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'nombre', 'fecha', 'estado']

class CustomUserSerializer(serializers.ModelSerializer):
    def validate_document(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("El número de documento debe ser numérico.")
        if value and len(value) < 6:
            raise serializers.ValidationError("El número de documento debe tener al menos 6 dígitos.")
        return value

    def validate_phone(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("El teléfono debe ser numérico.")
        if value and len(value) < 7:
            raise serializers.ValidationError("El teléfono debe tener al menos 7 dígitos.")
        return value

    def validate_birth_date(self, value):
        import datetime
        if value and value > datetime.date.today():
            raise serializers.ValidationError("La fecha de nacimiento no puede ser en el futuro.")
        if value and (datetime.date.today().year - value.year) < 14:
            raise serializers.ValidationError("El usuario debe tener al menos 14 años.")
        return value
    role = serializers.SerializerMethodField()
    eventos_inscritos = serializers.SerializerMethodField()
    def get_eventos_inscritos(self, obj):
        from eventos.models import Ticket
        eventos = Ticket.objects.filter(user=obj).select_related('event').values_list('event', flat=True).distinct()
        from eventos.models import Event
        eventos_qs = Event.objects.filter(id__in=eventos)
        return SimpleEventSerializer(eventos_qs, many=True).data
    document_type = serializers.StringRelatedField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone', 'birth_date',
            'document_type', 'document', 'country', 'city', 'created_at', 'updated_at',
            'password', 'role', 'eventos_inscritos'
        ]
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
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 'birth_date',
            'document_type', 'document', 'country', 'city', 'password'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Extraer el password
        password = validated_data.pop('password')
        
        # Crear el usuario
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)  # Hashear el password correctamente
        user.save()
        
        # Asignar grupo por defecto
        try:
            group = Group.objects.get(name="Participante")
            user.groups.add(group)
        except Group.DoesNotExist:
            pass
        
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)