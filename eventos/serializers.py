"""Serializadores del módulo de eventos."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
import json

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from usuarios.models import CustomUser
from usuarios.serializers import CustomUserSerializer

from .models import (
    City,
    Department,
    Event,
    Ticket,
    TicketAccessLog,
    TicketType,
    TicketTypeEvent,
)


class UserSummarySerializer(serializers.ModelSerializer):
    """Datos básicos del usuario asociado a un ticket."""

    class Meta:
        model = CustomUser
        fields = ["id", "first_name", "last_name", "email"]


class TicketTypeSerializer(serializers.ModelSerializer):
    """Tipo de ticket reutilizable entre eventos."""

    class Meta:
        model = TicketType
        fields = ["id", "ticket_name", "description"]
        read_only_fields = ["id"]


class TicketTypeEventSerializer(serializers.ModelSerializer):
    """Configuración específica de un tipo de ticket para un evento."""

    ticket_type = TicketTypeSerializer(read_only=True)
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = TicketTypeEvent
        fields = [
            "id",
            "ticket_type",
            "price",
            "maximun_capacity",
            "capacity_sold",
            "remaining_capacity",
        ]
        read_only_fields = ["id", "capacity_sold", "remaining_capacity"]

    def get_remaining_capacity(self, obj: TicketTypeEvent) -> int:
        return max(0, obj.maximun_capacity - obj.capacity_sold)


class TicketSerializer(serializers.ModelSerializer):
    """Detalle de tickets vendidos o reservados."""

    user = UserSummarySerializer(read_only=True)
    event = serializers.StringRelatedField(read_only=True)
    config_type = TicketTypeEventSerializer(read_only=True)
    qr_base64 = serializers.SerializerMethodField()
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source="user",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = ["id", "date_of_purchase", "event", "unique_code", "qr_base64"]

    def get_qr_base64(self, obj) -> Optional[str]:
        if hasattr(obj, "get_qr_base64"):
            return obj.get_qr_base64()
        return None

    def validate_amount(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

    def create(self, validated_data: Dict[str, Any]) -> Ticket:
        config_type: TicketTypeEvent | None = self.context.get("config_type")
        if config_type is None:
            raise serializers.ValidationError("Config type debe estar presente en el contexto.")

        if config_type.capacity_sold + validated_data.get("amount", 0) > config_type.maximun_capacity:
            raise serializers.ValidationError("No hay suficiente aforo disponible para este tipo de ticket.")

        if "unique_code" not in validated_data:
            import uuid

            validated_data["unique_code"] = str(uuid.uuid4())

        ticket = Ticket.objects.create(
            **validated_data,
            event=config_type.event,
            config_type=config_type,
        )
        return ticket


class ConfigTypeSerializer(serializers.Serializer):
    """Configuración de un tipo de ticket al crear o actualizar eventos."""

    ticket_type_id = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        default=Decimal("0.00"),
    )
    maximun_capacity = serializers.IntegerField(min_value=1)

    def validate_ticket_type_id(self, value: int) -> int:
        if not TicketType.objects.filter(id=value).exists():
            raise serializers.ValidationError("El tipo de ticket indicado no existe.")
        return value


class EventSerializer(serializers.ModelSerializer):
    sales_open_datetime = serializers.DateTimeField(required=False, allow_null=True)
    image_file = serializers.ImageField(write_only=True, required=False)
    """Serializer principal de eventos incluyendo tipos de ticket."""

    location = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    city_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    tickets = TicketSerializer(many=True, read_only=True)
    types_of_tickets_available = serializers.SerializerMethodField()
    maximun_capacity_remaining = serializers.SerializerMethodField()

    # Campo manual para ticket_type, procesado en to_internal_value
    ticket_type = serializers.SerializerMethodField()

    def to_internal_value(self, data):
        parsed_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "ticket_type" in parsed_data:
            raw_value = parsed_data.get("ticket_type")
            if isinstance(raw_value, str):
                try:
                    parsed_data["ticket_type"] = json.loads(raw_value)
                except json.JSONDecodeError as exc:
                    raise serializers.ValidationError({"ticket_type": "Formato JSON inválido."}) from exc
            elif raw_value in (None, ""):
                parsed_data["ticket_type"] = []
            elif not isinstance(raw_value, list):
                raise serializers.ValidationError({"ticket_type": "Debe ser una lista de configuraciones."})
        return super().to_internal_value(parsed_data)

    def get_ticket_type(self, obj) -> List[Dict[str, Any]]:
        # Solo para lectura, retorna la configuración de tickets
        types = (
            TicketTypeEvent.objects.select_related("ticket_type")
            .filter(event=obj)
            .order_by("ticket_type__ticket_name")
        )
        serializer = TicketTypeEventSerializer(types, many=True, context=self.context)
        return serializer.data

    max_capacity = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Event
        fields = [
            "id",
            'creator',
            "event_name",
            "description",
            "date",
            "start_datetime",
            "end_datetime",
            "country",
            "location",
            "city_text",
            "department_text",
            "status",
            "category",
            "image",
            "image_file",
            "organizer",
            "min_age",
            "max_capacity",
            "sales_open_datetime",
            "tickets",
            "types_of_tickets_available",
            "maximun_capacity_remaining",
            "ticket_type",
        ]
        read_only_fields = [
            "id",
            'creator',
            "tickets",
            "types_of_tickets_available",
            "maximun_capacity_remaining",
        ]

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        start = data.get("start_datetime")
        end = data.get("end_datetime")
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_datetime": "La fecha y hora de fin debe ser posterior a la de inicio."}
            )

        if start and start < timezone.now():
            raise serializers.ValidationError(
                {"start_datetime": "La fecha y hora de inicio no puede estar en el pasado."}
            )

        if end and end < timezone.now():
            raise serializers.ValidationError(
                {"end_datetime": "La fecha y hora de fin no puede estar en el pasado."}
            )

        ticket_configs: List[Dict[str, Any]] = data.get("ticket_type", [])
        type_ids = [cfg["ticket_type_id"] for cfg in ticket_configs]
        if len(type_ids) != len(set(type_ids)):
            raise serializers.ValidationError(
                {"ticket_type": "No se permiten tipos de ticket repetidos."}
            )

        # Validación de aforo total
        max_capacity = data.get("max_capacity")
        if max_capacity is not None:
            total_tickets = sum(cfg["maximun_capacity"] for cfg in ticket_configs)
            if total_tickets > max_capacity:
                raise serializers.ValidationError({
                    "ticket_type": f"La suma de las capacidades de los tipos de ticket ({total_tickets}) supera el aforo máximo del evento ({max_capacity})."
                })

        country = data.get("country", "Colombia")
        if country.lower() == "colombia":
            if not data.get("location"):
                raise serializers.ValidationError({
                    "location": "La ciudad es obligatoria para eventos en Colombia."
                })
        else:
            if not data.get("city_text") or not data.get("department_text"):
                raise serializers.ValidationError({
                    "city_text": "Debe indicar ciudad y departamento/estado para eventos fuera de Colombia."
                })
        return data

    def get_types_of_tickets_available(self, obj: Event) -> List[Dict[str, Any]]:
        types = (
            TicketTypeEvent.objects.select_related("ticket_type")
            .filter(event=obj)
            .order_by("ticket_type__ticket_name")
        )
        serializer = TicketTypeEventSerializer(types, many=True, context=self.context)
        return serializer.data

    def get_maximun_capacity_remaining(self, obj: Event) -> int:
        total_capacity = (
            TicketTypeEvent.objects.filter(event=obj).aggregate(total=Sum("maximun_capacity"))["total"]
            or 0
        )
        sold = Ticket.objects.filter(event=obj).aggregate(total=Sum("amount"))["total"] or 0
        return max(0, total_capacity - sold)

    def create(self, validated_data: Dict[str, Any]) -> Event:
        from .supabase_service import upload_image_to_supabase
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        # Obtener ticket_type desde self.initial_data
        ticket_configs = self.initial_data.get("ticket_type")
        if isinstance(ticket_configs, str):
            try:
                ticket_configs = json.loads(ticket_configs)
            except Exception:
                ticket_configs = []
        elif not isinstance(ticket_configs, list):
            ticket_configs = []

        image_file = validated_data.pop("image_file", None)
        if image_file:
            validated_data["image"] = upload_image_to_supabase(image_file, image_file.name)
        event = Event(**validated_data)
        try:
            event.clean()  # Validación de duplicados
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        event.save()
        for config in ticket_configs:
            from .models import TicketTypeEvent
            TicketTypeEvent.objects.create(
                event=event,
                ticket_type_id=config["ticket_type_id"],
                price=config["price"],
                maximun_capacity=config["maximun_capacity"],
                capacity_sold=0,
            )
        return event

    def update(self, instance: Event, validated_data: Dict[str, Any]) -> Event:
        from .supabase_service import upload_image_to_supabase

        ticket_configs = validated_data.pop("ticket_type", None)
        image_file = validated_data.pop("image_file", None)

        if image_file:
            validated_data["image"] = upload_image_to_supabase(image_file, image_file.name)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ticket_configs is not None:
            TicketTypeEvent.objects.filter(event=instance).delete()
            for config in ticket_configs:
                TicketTypeEvent.objects.create(
                    event=instance,
                    ticket_type_id=config["ticket_type_id"],
                    price=config["price"],
                    maximun_capacity=config["maximun_capacity"],
                    capacity_sold=0,
                )
        return instance

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class CitySerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "department"]


class TicketAccessLogSerializer(serializers.ModelSerializer):
    ticket = serializers.PrimaryKeyRelatedField(read_only=True)
    accessed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = TicketAccessLog
        fields = [
            "id",
            "ticket",
            "accessed_by",
            "access_time",
            "ip_address",
            "device_info",
        ]
        read_only_fields = fields
    
# --- INICIO DE NUEVOS SERIALIZERS PARA SPECTACULAR ---

class AttendeeTicketSerializer(serializers.Serializer):
    """Serializador para un ticket en la lista de asistentes (EventInscritosAPIView)."""
    ticket_id = serializers.IntegerField()
    user = CustomUserSerializer()
    ticket_type = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    unique_code = serializers.UUIDField()
    date_of_purchase = serializers.DateTimeField()
    price_paid = serializers.DecimalField(max_digits=10, decimal_places=2)


class MyTicketDetailSerializer(serializers.Serializer):
    """Serializador para un ticket en la lista de 'mis eventos' (MyEventsAPIView)."""
    ticket_id = serializers.IntegerField()
    type = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    unique_code = serializers.UUIDField()
    qr_base64 = serializers.CharField(allow_null=True)
    date_of_purchase = serializers.DateTimeField()
    price_paid = serializers.DecimalField(max_digits=10, decimal_places=2)


class MyEventSerializer(serializers.Serializer):
    """Serializador para un evento en la lista de 'mis eventos' (MyEventsAPIView)."""
    event = serializers.CharField()
    event_id = serializers.IntegerField()
    date = serializers.DateField()
    location = serializers.CharField(allow_null=True)
    country = serializers.CharField()
    city_text = serializers.CharField()
    department_text = serializers.CharField()
    status = serializers.CharField()
    tickets = MyTicketDetailSerializer(many=True)


class BuyTicketRequestSerializer(serializers.Serializer):
    """Serializador para el *request* de BuyTicketAPIView."""
    config_type_id = serializers.IntegerField(help_text="ID de la configuración (TicketTypeEvent) a comprar.")
    amount = serializers.IntegerField(default=1, help_text="Cantidad de boletos a comprar.")


class PayUPaymentDataSerializer(serializers.Serializer):
    """Serializador para la data de PayU (BuyTicketAPIView response)."""
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


class BuyTicketResponseSerializer(serializers.Serializer):
    """Serializador para la *respuesta* de BuyTicketAPIView."""
    message = serializers.CharField()
    ticket_id = serializers.IntegerField()
    config_type_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    total_a_pagar = serializers.CharField()
    payment = PayUPaymentDataSerializer()

# --- FIN DE NUEVOS SERIALIZERS ---