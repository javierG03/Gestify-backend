from .models import Evento, TipoBoleta, TipoBoletaEvento, Boleta
from rest_framework import serializers
from usuarios.models import CustomUser
from drf_spectacular.utils import extend_schema_field
import datetime
from django.shortcuts import get_object_or_404
from decimal import Decimal


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email']

class TipoBoletaSerializer(serializers.ModelSerializer):
    """
    Serializer para tipos de boletos comunes (e.g., GA, VIP).
    """
    class Meta:
        model = TipoBoleta
        fields = ['id', 'nombre', 'descripcion', 'precio_base']
        read_only_fields = ['id']

    @extend_schema_field(str)  # Documenta el campo __str__ si se usa en responses
    def get_nombre_display(self, obj):
        return f"{obj.nombre} ({obj.precio_base})"

class TipoBoletaEventoSerializer(serializers.ModelSerializer):
    """
    Serializer para configuraciones específicas por evento (incluye aforo restante).
    """
    tipo_boleta = TipoBoletaSerializer(read_only=True)
    aforo_restante = serializers.SerializerMethodField()

    class Meta:
        model = TipoBoletaEvento
        fields = ['id', 'tipo_boleta', 'precio', 'aforo_maximo', 'aforo_vendido', 'aforo_restante']
        read_only_fields = ['id', 'aforo_vendido', 'aforo_restante']

    def get_aforo_restante(self, obj):
        return obj.aforo_maximo - obj.aforo_vendido

    def validate_aforo_maximo(self, value):
        if value <= 0:
            raise serializers.ValidationError("El aforo máximo debe ser mayor a 0.")
        return value

class BoletaSerializer(serializers.ModelSerializer):
    """
    Serializer para boletas individuales compradas por usuarios.
    """
    usuario = UserSerializer(read_only=True)
    evento = serializers.StringRelatedField()  # Muestra nombre del evento
    tipo_config = TipoBoletaEventoSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='usuario', write_only=True, required=False
    )

    class Meta:
        model = Boleta
        fields = [
            'id', 'usuario', 'usuario_id', 'evento', 'tipo_config', 'cantidad',
            'fecha_compra', 'estado', 'codigo_unico'
        ]
        read_only_fields = ['id', 'fecha_compra', 'codigo_unico']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

    def create(self, validated_data):
        # Lógica personalizada: Crear boleta y actualizar aforo
        tipo_config = validated_data.pop('tipo_config', None)
        if tipo_config.aforo_vendido + validated_data['cantidad'] > tipo_config.aforo_maximo:
            raise serializers.ValidationError("No hay suficiente aforo disponible para este tipo.")
        boleta = Boleta.objects.create(**validated_data, tipo_config=tipo_config)
        tipo_config.aforo_vendido += boleta.cantidad
        tipo_config.save()
        return boleta

class TipoConfigSerializer(serializers.Serializer):
    """
    Serializer para una configuración individual de tipo de boleta en tipos_data.
    Tipos explícitos para parsing correcto de números; validaciones post-parsing.
    """
    tipo_boleta_id = serializers.IntegerField(min_value=1, help_text="ID de un TipoBoleta existente.")
    precio = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=Decimal('0.00'),
        help_text="Precio específico (default 0 para gratuito)."
    )
    aforo_maximo = serializers.IntegerField(min_value=1, help_text="Capacidad máxima para este tipo (>0).")

    def validate_precio(self, value):
        """
        Validación post-parsing para precio (ya es Decimal, pero mensaje custom).
        """
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_aforo_maximo(self, value):
        """
        Validación post-parsing para aforo (ya es int, pero chequeo extra y mensaje custom).
        """
        if value <= 0:
            raise serializers.ValidationError("El aforo máximo debe ser mayor a 0.")
        return value

    def validate(self, data):
        """
        Validación cross-field en el inner serializer: Verifica existencia de TipoBoleta.
        """
        tipo_id = data['tipo_boleta_id']
        try:
            get_object_or_404(TipoBoleta, id=tipo_id)
        except:
            raise serializers.ValidationError(f"Tipo de boleta con ID {tipo_id} no existe.")
        return data
    
class EventoSerializer(serializers.ModelSerializer):
    """
    Serializer principal para eventos, incluyendo tipos disponibles y boletas vendidas.
    Requiere 'tipos_data' al crear para configurar al menos un tipo de boleta.
    """
    boletas = BoletaSerializer(many=True, read_only=True)
    tipos_disponibles = serializers.SerializerMethodField()  # CRÍTICO: MethodField para serializar TipoBoletaEvento directamente
    aforo_total_restante = serializers.SerializerMethodField()
    tipos_data = serializers.ListSerializer(
        child=TipoConfigSerializer(),
        write_only=True,
        min_length=1,
        help_text="Array de configuraciones para tipos de boletas. Ej: [{'tipo_boleta_id': 1, 'precio': 50.00, 'aforo_maximo': 100}]"
    )

    class Meta:
        model = Evento
        fields = [
            'id', 'nombre', 'descripcion', 'fecha', 'ciudad', 'pais',
            'estado', 'tipos_disponibles', 'boletas', 'aforo_total_restante', 'tipos_data'
        ]
        read_only_fields = ['id', 'aforo_total_restante', 'tipos_disponibles']

    @extend_schema_field(dict)  # Documenta como array de dicts para Swagger
    def get_tipos_disponibles(self, obj):
        """
        Query y serializa directamente las instancias de TipoBoletaEvento para este evento.
        Esto evita el AttributeError al no usar ManyToMany directo (que retorna TipoBoleta).
        """
        tipos_evento = TipoBoletaEvento.objects.select_related('tipo_boleta').filter(evento=obj)
        serializer = TipoBoletaEventoSerializer(tipos_evento, many=True, context=self.context)
        return serializer.data

    @extend_schema_field(int)
    def get_aforo_total_restante(self, obj):
        """
        Calcula aforo desde TipoBoletaEvento para consistencia y eficiencia.
        """
        tipos_evento = TipoBoletaEvento.objects.filter(evento=obj)
        total_maximo = sum(t.aforo_maximo for t in tipos_evento)
        total_vendido = sum(b.cantidad for b in obj.boletas.all())
        return max(0, total_maximo - total_vendido)

    def validate_tipos_data(self, value):
        """
        Validación a nivel de lista: Solo duplicados y consistencia (valores ya parseados por children).
        """
        tipo_ids = [config['tipo_boleta_id'] for config in value]
        if len(tipo_ids) != len(set(tipo_ids)):
            raise serializers.ValidationError("No se permiten tipos de boleta duplicados en la lista.")
        return value

    def validate(self, data):
        if 'fecha' in data and data['fecha'] < datetime.date.today():
            raise serializers.ValidationError("La fecha del evento no puede ser en el pasado.")
        if 'tipos_data' not in data or len(data['tipos_data']) == 0:
            raise serializers.ValidationError("Campo 'tipos_data' es requerido y debe tener al menos un ítem.")
        return data

    def create(self, validated_data):
        tipos_data = validated_data.pop('tipos_data')
        evento = Evento.objects.create(**validated_data)
        
        for config in tipos_data:
            TipoBoletaEvento.objects.create(
                evento=evento,
                tipo_boleta_id=config['tipo_boleta_id'],
                precio=config['precio'],  # Ya Decimal del serializer
                aforo_maximo=config['aforo_maximo'],  # Ya int
                aforo_vendido=0
            )
        
        # NO uses refresh_from_db() aquí; en su lugar, la response usará get_tipos_disponibles para fresh data
        return evento

    def update(self, instance, validated_data):
        tipos_data = validated_data.pop('tipos_data', None)
        instance = super().update(instance, validated_data)
        
        if tipos_data:
            instance.tipos_disponibles.clear()  # Limpia ManyToMany (elimina through records)
            for config in tipos_data:
                TipoBoletaEvento.objects.create(
                    evento=instance,
                    tipo_boleta_id=config['tipo_boleta_id'],
                    precio=config['precio'],
                    aforo_maximo=config['aforo_maximo'],
                    aforo_vendido=0
                )
        
        # No refresh; method fields manejan data fresh en response
        return instance