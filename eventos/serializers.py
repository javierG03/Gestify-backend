from .models import Event, TicketType, TicketTypeEvent, Ticket, Departamento, Ciudad
from rest_framework import serializers
from usuarios.models import CustomUser
from drf_spectacular.utils import extend_schema_field
import datetime
from django.shortcuts import get_object_or_404
from decimal import Decimal
from usuarios.serializers import CustomUserSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email']

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

    @extend_schema_field(serializers.IntegerField())
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

    start_datetime = serializers.DateTimeField(required=True)
    end_datetime = serializers.DateTimeField(required=True)
    category = serializers.ChoiceField(choices=[
        ("musica", "Música"),
        ("deporte", "Deporte"),
        ("educacion", "Educación"),
        ("tecnologia", "Tecnología"),
        ("arte", "Arte"),
        ("otros", "Otros")
    ], required=True)
    country = serializers.CharField(default="Colombia", read_only=True)
    department = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    image = serializers.ImageField(required=True)
    organizer = serializers.CharField(required=True)
    status = serializers.CharField(required=True)

    class Meta:
        model = Event
        fields = [
            'id', 'event_name', 'description', 'date', 'start_datetime', 'end_datetime',
            'city', 'department', 'country', 'status', 'category', 'image', 'organizer',
            'types_of_tickets_available', 'tickets', 'maximun_capacity_remaining', 'ticket_type'
        ]
        read_only_fields = ['id', 'types_of_tickets_available', 'tickets', 'maximun_capacity_remaining']

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
        errors = {}
        # Validar que todos los campos obligatorios estén presentes
        required_fields = [
            'event_name', 'description', 'date', 'start_datetime', 'end_datetime',
            'city', 'department', 'country', 'status', 'category', 'image', 'organizer', 'ticket_type'
        ]
        for field in required_fields:
            if field not in data or data[field] in [None, '', []]:
                errors[field] = f"El campo '{field}' es obligatorio."

        # Descripción mínima
        if 'description' in data and len(data['description']) < 20:
            errors['description'] = "La descripción debe tener al menos 20 caracteres."

        # Validación de fechas
        today = datetime.datetime.now()
        if 'start_datetime' in data:
            if data['start_datetime'] < today:
                errors['start_datetime'] = "La fecha y hora de inicio no puede ser en el pasado."
        if 'end_datetime' in data:
            if data['end_datetime'] < today:
                errors['end_datetime'] = "La fecha y hora de fin no puede ser en el pasado."
        if 'start_datetime' in data and 'end_datetime' in data:
            if data['end_datetime'] <= data['start_datetime']:
                errors['end_datetime'] = "La fecha y hora de fin debe ser posterior a la de inicio."

        # Validación de existencia de departamento y ciudad en la base de datos
        from .models import Departamento, Ciudad, Event
        if 'department' in data:
            if not Departamento.objects.filter(nombre__iexact=data['department']).exists():
                errors['department'] = "El departamento no existe en la base de datos."
        if 'city' in data and 'department' in data:
            departamento_obj = Departamento.objects.filter(nombre__iexact=data['department']).first()
            if departamento_obj:
                if not Ciudad.objects.filter(nombre__iexact=data['city'], departamento=departamento_obj).exists():
                    errors['city'] = "La ciudad no existe en la base de datos para el departamento seleccionado."
        # Evitar eventos duplicados (nombre, fecha, ciudad)
        if 'event_name' in data and 'date' in data and 'city' in data:
            if Event.objects.filter(event_name=data['event_name'], date=data['date'], city=data['city']).exists():
                errors['event_name'] = "Ya existe un evento con el mismo nombre, fecha y ciudad."
        # Validación de solapamiento de fechas/lugar
        if 'city' in data and 'start_datetime' in data and 'end_datetime' in data:
            overlapping = Event.objects.filter(
                city=data['city'],
                start_datetime__lt=data['end_datetime'],
                end_datetime__gt=data['start_datetime']
            )
            if overlapping.exists():
                errors['city'] = "Ya existe un evento en la ciudad con fechas que se solapan."

        # Validación de ticket_type
        if 'ticket_type' not in data or len(data['ticket_type']) == 0:
            errors['ticket_type'] = "Campo 'ticket_type' es requerido y debe tener al menos un ítem."
        else:
            # Capacidad total del evento (ejemplo: máximo 10000)
            total_capacity = sum([config['maximun_capacity'] for config in data['ticket_type']])
            if total_capacity > 10000:
                errors['ticket_type'] = "La suma de aforos no puede exceder 10,000 personas."
            # Precio mínimo/máximo por tipo
            for config in data['ticket_type']:
                if config['price'] < 1:
                    errors['ticket_type'] = "El precio mínimo por ticket es $1."
                if config['price'] > 10000000:
                    errors['ticket_type'] = "El precio máximo por ticket es $10,000,000."

        # Validación de imagen (formato y tamaño)
        if 'image' in data and data['image']:
            img = data['image']
            if hasattr(img, 'size') and img.size > 2*1024*1024:
                errors['image'] = "La imagen no debe superar los 2MB."
            if hasattr(img, 'name') and not img.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                errors['image'] = "Solo se permiten imágenes JPG y PNG."

        # Validación de organizador (si es usuario registrado)
        # Si el campo organizer fuera FK, aquí se validaría existencia


        # Validación ciudad-departamento: ya la garantiza el modelo FK

        if errors:
            raise serializers.ValidationError(errors)
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
    
class EventInscritoSerializer(serializers.Serializer):

    """Serializer para la lista de inscritos (tickets) de un evento."""
    
    ticket_id = serializers.IntegerField()
    user = CustomUserSerializer()
    ticket_type = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    unique_code = serializers.CharField()
    date_of_purchase = serializers.DateTimeField()
    price_paid = serializers.CharField()

class TicketValidationRequestSerializer(serializers.Serializer):
    """Serializer para el request de validación de tickets."""
    unique_code = serializers.CharField(max_length=100, help_text="El código único escaneado del QR.")

# --- Para MyEventsAPIView ---

class MyTicketSerializer(serializers.Serializer):
    """Describe un ticket individual dentro de la lista de 'Mis Eventos'."""
    ticket_id = serializers.IntegerField()
    type = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    unique_code = serializers.CharField()
    qr_base64 = serializers.CharField(allow_null=True)
    date_of_purchase = serializers.DateTimeField()
    price_paid = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)

class MyEventsResponseSerializer(serializers.Serializer):
    """Describe la respuesta para la vista 'Mis Eventos'."""
    event = serializers.CharField()
    event_id = serializers.IntegerField()
    date = serializers.DateField()
    city = serializers.CharField()
    country = serializers.CharField()
    status = serializers.CharField()
    image = serializers.URLField(required=False, allow_null=True)
    tickets = MyTicketSerializer(many=True)


# --- Para BuyTicketAPIView y PayTicketAPIView ---

class TicketActionRequestSerializer(serializers.Serializer):
    """Describe el request para comprar o pagar un ticket."""
    config_type_id = serializers.IntegerField(help_text="ID del TicketTypeEvent.")
    amount = serializers.IntegerField(default=1)

class BuyTicketResponseSerializer(serializers.Serializer):
    """Describe la respuesta de BuyTicketAPIView."""
    message = serializers.CharField()
    ticket_id = serializers.IntegerField()
    config_type_id = serializers.IntegerField(required=False)
    amount = serializers.IntegerField(required=False)
    total_a_pagar = serializers.CharField(required=False)
    unique_code = serializers.CharField(required=False)

class PayTicketResponseSerializer(serializers.Serializer):
    """Describe la respuesta de PayTicketAPIView."""
    sandbox = serializers.BooleanField()
    merchantId = serializers.CharField()
    accountId = serializers.CharField()
    description = serializers.CharField()
    referenceCode = serializers.CharField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    signature = serializers.CharField()
    buyerEmail = serializers.EmailField()
    confirmationUrl = serializers.URLField()
    responseUrl = serializers.URLField()