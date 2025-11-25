"""
eventos/models.py
Modelos principales del módulo de eventos. Clean code, docstrings y auditoría.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class EventStatusChoices(models.TextChoices):
    PROGRAMADO = "programado", "Programado"
    ACTIVO = "activo", "Activo"
    CANCELADO = "cancelado", "Cancelado"
    FINALIZADO = "finalizado", "Finalizado"

class EventCategoryChoices(models.TextChoices):
    MUSICA = "musica", "Música"
    DEPORTE = "deporte", "Deporte"
    EDUCACION = "educacion", "Educación"
    TECNOLOGIA = "tecnologia", "Tecnología"
    ARTE = "arte", "Arte"
    OTROS = "otros", "Otros"

class TicketStatusChoices(models.TextChoices):
    COMPRADA = "comprada", "Comprada"
    USADA = "usada", "Usada"
    PENDIENTE = "pendiente", "Pendiente por pagar"
    CANCELADA = "cancelada", "Cancelada"

class EventChangeLog(models.Model):
    """Auditoría de cambios importantes en eventos."""
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='change_logs')
    changed_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, help_text="Usuario que realizó el cambio")
    change_type = models.CharField(max_length=50, help_text="Tipo de cambio: nombre, fecha, estado, etc.")
    field_changed = models.CharField(max_length=50, help_text="Campo modificado")
    old_value = models.TextField(blank=True, null=True, help_text="Valor anterior")
    new_value = models.TextField(blank=True, null=True, help_text="Nuevo valor")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora del cambio")

    class Meta:
        verbose_name = "Event Change Log"
        verbose_name_plural = "Event Change Logs"
        ordering = ["-timestamp"]
        db_table = "events_change_log"

    def __str__(self):
        return f"{self.event.event_name} - {self.change_type} - {self.field_changed} ({self.timestamp})"

class Department(models.Model):
    """Departamento normalizado para eventos y usuarios."""
    name = models.CharField(max_length=100, unique=True, help_text="Nombre del departamento")

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]
        db_table = "events_department"

    def __str__(self):
        return self.name

class City(models.Model):
    """Ciudad normalizada, asociada a un departamento."""
    name = models.CharField(max_length=100, help_text="Nombre de la ciudad")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="cities", help_text="Departamento al que pertenece la ciudad")

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        unique_together = ("name", "department")
        ordering = ["name"]
        db_table = "events_city"

    def __str__(self):
        return f"{self.name} ({self.department.name})"

class TicketAccessLog(models.Model):
    """Auditoría de accesos a tickets."""
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    access_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    device_info = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "events_ticket_access_log"

    def __str__(self):
        return f"Acceso a ticket {self.ticket.id} por {self.accessed_by} en {self.access_time}"

from usuarios.models import CustomUser
from django.conf import settings

# Modelo para tipos de boletos comunes (puede reutilizarse entre eventos)
class TicketType(models.Model):
    ticket_name = models.CharField(max_length=50)
    description = models.TextField(blank=True, help_text="Benefits or details of ticket type.")

    class Meta:
        verbose_name = "Ticket type"
        verbose_name_plural = "Ticket Types"
        db_table = "events_ticket_type"

    def __str__(self):
        return self.ticket_name

class Event(models.Model): 
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Apunta a tu modelo CustomUser
        on_delete=models.SET_NULL,  # Si se borra el usuario, el evento no se borra (se pone en NULL)
        null=True,
        blank=True, # Lo ponemos blank/null temporalmente para migraciones
        related_name="created_events",
        help_text="Usuario que creó el evento."
    )
    event_name = models.CharField(max_length=200, help_text="Nombre del evento")
    description = models.TextField(help_text="Descripción del evento")
    start_datetime = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de inicio del evento")
    end_datetime = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de finalización del evento")
    country = models.CharField(max_length=50, default="Colombia", help_text="País donde se realiza el evento")
    location = models.ForeignKey('City', on_delete=models.SET_NULL, blank=True, null=True, help_text="Ciudad del evento (solo Colombia)")
    city_text = models.CharField(max_length=100, blank=True, null=True, help_text="Ciudad libre (otros países)")
    department_text = models.CharField(max_length=100, blank=True, null=True, help_text="Departamento/Región libre (otros países)")
    status = models.CharField(max_length=50, choices=EventStatusChoices.choices,default=EventStatusChoices.PROGRAMADO, help_text="Estado del evento")
    CATEGORY_CHOICES = [
        ("musica", "Música"),
        ("deporte", "Deporte"),
        ("educacion", "Educación"),
        ("tecnologia", "Tecnología"),
        ("arte", "Arte"),
        ("otros", "Otros")
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="otros", help_text="Categoría del evento")
    image = models.URLField(blank=True, null=True, help_text="URL de la imagen del evento (almacenada en Supabase)")
    organizer = models.CharField(max_length=200, blank=True, null=True, help_text="Nombre del organizador")
    min_age = models.PositiveIntegerField(blank=True, null=True, help_text="Edad mínima requerida para asistir al evento. Dejar vacío si no hay restricción.")
    max_capacity = models.PositiveIntegerField(blank=True, null=True, help_text="Aforo máximo permitido para el evento.")
    sales_open_datetime = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora en que se habilitan las ventas de tickets.")


    # Relación con tipos de boletos disponibles para este evento
    types_of_tickets_available = models.ManyToManyField(
        TicketType,
        through='TicketTypeEvent',  # Intermediario para capacidades y precios específicos
        blank=True,
        related_name="event"
    )

    class Meta:
        # permisos personalizados que Django crea al migrar
        permissions = [
            ("cancelar_evento", "Puede cancelar evento"),
            ("inscribirse_evento", "Puede inscribirse a un evento"),            
        ]
        db_table = "events_event"
    
    def __str__(self):
        return self.event_name
    
    def tickets_solds(self):
            """Método helper para contar boletos totales vendidos."""
            return sum(ticket.amount for ticket in self.tickets.all())

    def clean(self):
        super().clean()
        if self.event_name and self.location and self.start_datetime and self.end_datetime:
            qs = Event.objects.filter(
                event_name=self.event_name,
                location=self.location,
                start_datetime=self.start_datetime,
                end_datetime=self.end_datetime
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Ya existe un evento con el mismo nombre, lugar y fecha/hora.")

# Intermediario para configurar capacidades y precios por tipo por evento
class TicketTypeEvent(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Specfic price for this event.")
    maximun_capacity = models.PositiveIntegerField(help_text="Maximun capacity for this event.")
    capacity_sold = models.PositiveIntegerField(default=0, editable=False)  # Actualízalo en views

    class Meta:
        unique_together = ('event', 'ticket_type')  # Un tipo por evento
        verbose_name = "Settings of ticket type per event"
        db_table = "events_ticket_type_event"

    def __str__(self):
        return f"{self.ticket_type.ticket_name} para {self.event.event_name}"

# Modelo para boletas individuales (reemplaza o suplementa inscritos)
class Ticket(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_tickets")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    config_type = models.ForeignKey(TicketTypeEvent, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(default=1, help_text="Number of tickets purchased.")
    date_of_purchase = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=TicketStatusChoices.choices, default=TicketStatusChoices.PENDIENTE
    )
    # Campo para código QR o ID único si se integra con escaneo
    unique_code = models.CharField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "ticket per user"
        verbose_name_plural = "Tickets per users"
        db_table = "events_ticket"

    def __str__(self):
        return f"Boleta {self.unique_code} para {self.event.event_name} ({self.config_type.ticket_type.ticket_name})"

    def save(self, *args, **kwargs):
        previous: "Ticket | None" = None
        if self.pk:
            try:
                previous = Ticket.objects.select_related("config_type").get(pk=self.pk)
            except Ticket.DoesNotExist:
                previous = None

        super().save(*args, **kwargs)

        if previous and previous.config_type_id != self.config_type_id:
            if previous.status == "comprada":
                previous.config_type.capacity_sold = max(0, previous.config_type.capacity_sold - previous.amount)
                previous.config_type.save(update_fields=["capacity_sold"])
            if self.status == "comprada":
                self.config_type.refresh_from_db(fields=["capacity_sold", "maximun_capacity"])
                self.config_type.capacity_sold = min(
                    self.config_type.maximun_capacity,
                    self.config_type.capacity_sold + self.amount,
                )
                self.config_type.save(update_fields=["capacity_sold"])
            return

        if previous:
            if previous.status == "comprada" and (
                self.status != "comprada"
                or previous.amount != self.amount
            ):
                previous.config_type.capacity_sold = max(
                    0,
                    previous.config_type.capacity_sold - previous.amount,
                )
                previous.config_type.save(update_fields=["capacity_sold"])

            if self.status == "comprada" and (
                previous.status != "comprada"
                or previous.amount != self.amount
            ):
                self.config_type.refresh_from_db(fields=["capacity_sold", "maximun_capacity"])
                self.config_type.capacity_sold = min(
                    self.config_type.maximun_capacity,
                    self.config_type.capacity_sold + self.amount,
                )
                self.config_type.save(update_fields=["capacity_sold"])
            return

        if self.status == "comprada":
            self.config_type.refresh_from_db(fields=["capacity_sold", "maximun_capacity"])
            self.config_type.capacity_sold = min(
                self.config_type.maximun_capacity,
                self.config_type.capacity_sold + self.amount,
            )
            self.config_type.save(update_fields=["capacity_sold"])

    def get_qr_base64(self):
        """
        Genera el QR en base64 usando el unique_code del ticket SOLO si está pagado.
        """
        if self.status != "comprada":
            return None
        import qrcode
        import base64
        from io import BytesIO
        if not self.unique_code:
            return None
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.unique_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str