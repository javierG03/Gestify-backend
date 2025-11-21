"""
usuarios/serializers.py
Serializadores principales del módulo de usuarios. Clean code, validaciones centralizadas y comentarios claros.
"""

from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from eventos.models import Event, City
from drf_spectacular.utils import extend_schema_field
from .models import CustomUser, DocumentType
from .utils import assign_user_to_group
from typing import List, Optional

User = get_user_model()

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ["id", "name", "code"]

class SimpleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "event_name", "date", "status"]

class CustomUserSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    eventos_inscritos = serializers.SerializerMethodField()

    def get_department_name(self, obj) -> Optional[str]:
        """Retorna el nombre del departamento en lugar del ID"""
        return obj.department.name if obj.department else None
    
    def get_city_name(self, obj) -> Optional[str]:
        """Retorna el nombre de la ciudad en lugar del ID"""
        return obj.city.name if obj.city else None

    def get_role(self, obj) -> list:
        """Retorna los grupos (roles) del usuario como una lista de nombres"""
        return list(obj.groups.values_list('name', flat=True))
    
    @extend_schema_field(SimpleEventSerializer(many=True))
    def get_eventos_inscritos(self, obj):
        """Retorna los eventos inscritos del usuario"""
        from eventos.models import Ticket
        eventos = Ticket.objects.filter(user=obj).select_related('event').values_list('event', flat=True).distinct()
        from eventos.models import Event
        eventos_qs = Event.objects.filter(id__in=eventos)
        return SimpleEventSerializer(eventos_qs, many=True).data

    def validate(self, data):
        # Validar ciudad-departamento solo si ambos están presentes
        city = data.get('city')
        department = data.get('department')
        if city and department:
            if city.department_id != department.id:
                raise serializers.ValidationError({
                    'city': 'La ciudad seleccionada no pertenece al departamento elegido.'
                })
        return data
    
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
    
    document_type = serializers.StringRelatedField()

    class Meta:
        model = CustomUser
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False},
            'role': {'read_only': True},
            'eventos_inscritos': {'read_only': True},
            'department_name': {'read_only': True},
            'city_name': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        user = super().create(validated_data)
    
        # asignar grupo por defecto
        assign_user_to_group(user, "Participante")

        return user
            

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Guardar el usuario que realiza el cambio para la señal
            instance._changed_by = request.user
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
    
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
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False)
    department = serializers.PrimaryKeyRelatedField(queryset=CustomUser._meta.get_field('department').related_model.objects.all(), required=False)
    city_text = serializers.CharField(required=False, allow_blank=True)
    department_text = serializers.CharField(required=False, allow_blank=True)
    password_confirm = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 'birth_date',
            'document_type', 'document', 'country', 'department', 'city', 'city_text', 'department_text', 'password', 'password_confirm'
        ]
        extra_kwargs = {'password': {'write_only': True}, 'password_confirm': {'write_only': True}}
    def validate(self, data):
        from django.contrib.auth.password_validation import validate_password
        country = data.get('country', 'Colombia')
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        email = data.get('email')
        document = data.get('document')
        if password != password_confirm:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        validate_password(password)
        # Validar unicidad de email
        from .models import CustomUser
        if email and CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Ya existe un usuario registrado con este correo.'})
        # Validar unicidad de documento
        if document and CustomUser.objects.filter(document=document).exists():
            raise serializers.ValidationError({'document': 'Ya existe un usuario registrado con este número de documento.'})
        if country.lower() == 'colombia':
            if not data.get('city'):
                raise serializers.ValidationError({'city': 'La ciudad es obligatoria para usuarios de Colombia.'})
            if not data.get('department'):
                raise serializers.ValidationError({'department': 'El departamento es obligatorio para usuarios de Colombia.'})
        else:
            if not data.get('city_text') or not data.get('department_text'):
                raise serializers.ValidationError({'city_text': 'Ciudad y departamento son obligatorios para otros países.'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm', None)
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        assign_user_to_group(user, "Participante")
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class MessageSerializer(serializers.Serializer):
    """Serializador genérico para un mensaje de respuesta."""
    message = serializers.CharField()

class EmailSerializer(serializers.Serializer):
    """Serializador para un solo campo de email."""
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializador para confirmar el reseteo de contraseña."""
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

class EmptySerializer(serializers.Serializer):
    """Un serializador vacío para silenciar advertencias."""
    pass