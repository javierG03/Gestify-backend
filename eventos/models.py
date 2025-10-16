from django.db import models
# Modelo para Departamento
class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

# Modelo para Ciudad
class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name="ciudades")

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"
        unique_together = ("nombre", "departamento")
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"

# Auditoría de accesos a tickets

from django.db import models
from django.contrib.auth import get_user_model

class TicketAccessLog(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    access_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    device_info = models.CharField(max_length=255, blank=True, null=True)

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

    def __str__(self):
        return self.ticket_name

class Event(models.Model): 
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField(help_text="Fecha principal del evento (legacy, usar start_datetime y end_datetime)")
    start_datetime = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de inicio del evento")
    end_datetime = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de finalización del evento")
    department = models.CharField(max_length=100, help_text="Departamento del evento")
    city = models.CharField(max_length=100, help_text="Ciudad del evento")
    country = models.CharField(max_length=20, default="Colombia", editable=False)
    status = models.CharField(max_length=50, choices=(
        ("programado", "Programado"),
        ("activo", "Activo"),
        ("cancelado", "Cancelado"),
        ("finalizado", "Finalizado")
    ), default="programado")
    CATEGORY_CHOICES = [
        ("musica", "Música"),
        ("deporte", "Deporte"),
        ("educacion", "Educación"),
        ("tecnologia", "Tecnología"),
        ("arte", "Arte"),
        ("otros", "Otros")
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="otros", help_text="Categoría del evento")
    image = models.ImageField(upload_to="event_images/", blank=True, null=True, help_text="Imagen del evento")
    organizer = models.CharField(max_length=200, blank=True, null=True, help_text="Nombre del organizador")


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
    
    def __str__(self):
        return self.event_name
    
    def tickets_solds(self):
            """Método helper para contar boletos totales vendidos."""
            return sum(ticket.amount for ticket in self.tickets.all())

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
        choices=[("comprada", "Comprada"), ("usada", "Usada"), ("pendiente", "Pendiente por pagar"), ("cancelada", "Cancelada")],
        default="pendiente"
    )
    # Campo para código QR o ID único si se integra con escaneo
    unique_code = models.CharField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "ticket per user"
        verbose_name_plural = "Tickets per users"

    def __str__(self):
        return f"Boleta {self.unique_code} para {self.event.event_name} ({self.config_type.ticket_type.ticket_name})"

    def save(self, *args, **kwargs):
        # Lógica para actualizar aforo_vendido en TipoBoletaEvento al comprar
        if self.status == "comprada" and not self.pk:  # Nueva compra
            self.config_type.capacity_sold += self.amount
            self.config_type.save()
        super().save(*args, **kwargs)

    def get_qr_base64(self):
        """
        Genera el QR en base64 usando el unique_code del ticket.
        """
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
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str