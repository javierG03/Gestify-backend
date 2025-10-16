from .models import Event, TicketType, TicketTypeEvent, Ticket
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

class TicketTypeSerializer(serializers.ModelSerializer):
    """
    Serializer para tipos de boletos comunes (e.g., GA, VIP).
    """
    class Meta:
        model = TicketType
        fields = ['id', 'ticket_name', 'description']
        read_only_fields = ['id']

    @extend_schema_field(str)  # Documenta el campo __str__ si se usa en responses
    def get_display_name(self, obj):
        return f"{obj.ticket_name}"

class TicketTypeEventSerializer(serializers.ModelSerializer):
    """
    Serializer para configuraciones específicas por evento (incluye aforo restante).
    """
    ticket_type = TicketTypeSerializer(read_only=True)
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = TicketTypeEvent
        fields = ['id', 'ticket_type', 'price', 'maximun_capacity', 'capacity_sold', 'remaining_capacity']
        read_only_fields = ['id', 'capacity_sold', 'remaining_capacity']

    def get_remaining_capacity(self, obj):
        return obj.maximun_capacity - obj.capacity_sold

    def validate_maximun_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("El aforo máximo debe ser mayor a 0.")
        return value

class TicketSerializer(serializers.ModelSerializer):
    """
    Serializer para Tickets individuales compradas por usuarios.
    """
    user = UserSerializer(read_only=True)
    event = serializers.StringRelatedField()  # Muestra nombre del evento
    config_type = TicketTypeEventSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True, required=False
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'user_id', 'event', 'config_type', 'amount',
            'date_of_purchase', 'status', 'unique_code'
        ]
        read_only_fields = ['id', 'date_of_purchase', 'unique_code']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

    def create(self, validated_data):
        # Lógica personalizada: Crear Ticket y actualizar aforo
        import uuid
        config_type = self.context.get('config_type')

        if config_type.capacity_sold + validated_data['amount'] > config_type.maximun_capacity:
            raise serializers.ValidationError("No hay suficiente aforo disponible para este tipo.")

        # Generar unique_code si no viene en validated_data
        if not validated_data.get('unique_code'):
            validated_data['unique_code'] = str(uuid.uuid4())

        ticket = Ticket.objects.create(
            **validated_data,
            event=config_type.event,
            config_type=config_type
        )

        config_type.capacity_sold += ticket.amount
        config_type.save()
        return ticket

class ConfigTypeSerializer(serializers.Serializer):
    """
    Serializer para una configuración individual de tipo de Ticket en ticket_type.
    Tipos explícitos para parsing correcto de números; validaciones post-parsing.
    """
    ticket_type_id = serializers.IntegerField(min_value=1, help_text="ID de un tipo de boleta existente.")
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=Decimal('0.00'),
        help_text="Precio específico por evento(default 0 para gratuito)."
    )
    maximun_capacity = serializers.IntegerField(min_value=1, help_text="Capacidad máxima para este tipo de boleta (>0).")

    def validate_price(self, value):
        """
        Validación post-parsing para precio (ya es Decimal, pero mensaje custom).
        """
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_maximun_capacity(self, value):
        """
        Validación post-parsing para aforo (ya es int, pero chequeo extra y mensaje custom).
        """
        if value <= 0:
            raise serializers.ValidationError("El aforo máximo debe ser mayor a 0.")
        return value

    def validate(self, data):
        """
        Validación cross-field en el inner serializer: Verifica existencia de TipoTicket.
        """
        tipo_id = data['ticket_type_id']
        try:
            get_object_or_404(TicketType, id=tipo_id)
        except:
            raise serializers.ValidationError(f"El tipo de boleta con el ID {tipo_id} no existe.")
        return data
    
class EventSerializer(serializers.ModelSerializer):
    """
    Serializer principal para eventos, incluyendo tipos disponibles y Tickets vendidas.
    Requiere 'ticket_type' al crear para configurar al menos un tipo de Ticket.
    """
    tickets = TicketSerializer(many=True, read_only=True)
    types_of_tickets_available = serializers.SerializerMethodField()  # CRÍTICO: MethodField para serializar TicketTypeEvent directamente
    maximun_capacity_remaining = serializers.SerializerMethodField()
    ticket_type = serializers.ListSerializer(
        child=ConfigTypeSerializer(),
        write_only=True,
        min_length=1,
        help_text="Array de configuraciones para tipos de Tickets. Ej: [{'ticket_type_id': 1, 'price': 50.00, 'maximun_capacity': 100}]"
    )

    class Meta:
        model = Event
        fields = [
            'id', 'event_name', 'description', 'date', 'city', 'country',
            'status', 'types_of_tickets_available', 'tickets', 'maximun_capacity_remaining', 'ticket_type'
        ]
        read_only_fields = ['id', 'maximun_capacity_remaining', 'types_of_tickets_available']

    @extend_schema_field(dict)  # Documenta como array de dicts para Swagger
    def get_types_of_tickets_available(self, obj):
        """
        Query y serializa directamente las instancias de TicketTypeEvent para este evento.
        Esto evita el AttributeError al no usar ManyToMany directo (que retorna TipoTicket).
        """
        event_type = TicketTypeEvent.objects.select_related('ticket_type').filter(event=obj)
        serializer = TicketTypeEventSerializer(event_type, many=True, context=self.context)
        return serializer.data

    @extend_schema_field(int)
    def get_maximun_capacity_remaining(self, obj):
        """
        Calcula aforo desde TicketTypeEvent para consistencia y eficiencia.
        """
        event_type = TicketTypeEvent.objects.filter(event=obj)
        maximun_total = sum(t.maximun_capacity for t in event_type)
        total_sold = sum(b.amount for b in obj.tickets.all())
        return max(0, maximun_total - total_sold)

    def validate_ticket_type(self, value):
        """
        Validación a nivel de lista: Solo duplicados y consistencia (valores ya parseados por children).
        """
        type_ids = [config['ticket_type_id'] for config in value]
        if len(type_ids) != len(set(type_ids)):
            raise serializers.ValidationError("No se permiten tipos de Ticket duplicados en la lista.")
        return value

    def validate(self, data):
        if 'date' in data and data['date'] < datetime.date.today():
            raise serializers.ValidationError("La fecha del evento no puede ser en el pasado.")
        if 'ticket_type' not in data or len(data['ticket_type']) == 0:
            raise serializers.ValidationError("Campo 'ticket_type' es requerido y debe tener al menos un ítem.")
        return data

    def create(self, validated_data):
        ticket_type = validated_data.pop('ticket_type')
        event = Event.objects.create(**validated_data)
        
        for config in ticket_type:
            TicketTypeEvent.objects.create(
                event=event,
                ticket_type_id=config['ticket_type_id'],
                price=config['price'],  # Ya Decimal del serializer
                maximun_capacity=config['maximun_capacity'],  # Ya int
                capacity_sold=0
            )
        
        # NO uses refresh_from_db() aquí; en su lugar, la response usará get_tipos_disponibles para fresh data
        return event

    def update(self, instance, validated_data):
        ticket_type = validated_data.pop('ticket_type', None)
        instance = super().update(instance, validated_data)
        
        if ticket_type:
            instance.types_available.clear()  # Limpia ManyToMany (elimina through records)
            for config in ticket_type:
                TicketTypeEvent.objects.create(
                    event=instance,
                    ticket_type_id=config['ticket_type_id'],
                    price=config['price'],
                    maximun_capacity=config['maximun_capacity'],
                    capacity_sold=0
                )
        
        # No refresh; method fields manejan data fresh en response
        return instance