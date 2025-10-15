from django.db import models
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
    date = models.DateField()
    city = models.CharField(max_length=100) 
    country = models.CharField(max_length=100)
    status = models.CharField(max_length=520, choices=(("activo","Activo"),("cancelado","Cancelado")), default="activo")


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