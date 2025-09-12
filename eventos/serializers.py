from .models import Evento  
from rest_framework import serializers
from usuarios.models import CustomUser

class UserInscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email']

class EventoSerializer(serializers.ModelSerializer):
    inscritos = UserInscripcionSerializer(many=True, read_only=True)

    class Meta:
        model = Evento
        fields = "__all__"

    def validate_aforo(self, value):
        if value <= 0:
            raise serializers.ValidationError("El aforo debe ser mayor a 0.")
        return value