from django.db import models
from usuarios.models import CustomUser
from django.conf import settings

# Modelo para tipos de boletos comunes (puede reutilizarse entre eventos)
class TipoBoleta(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, help_text="Beneficios o detalles del tipo de boleta.")
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio por unidad.")

    class Meta:
        verbose_name = "Tipo de Boleta"
        verbose_name_plural = "Tipos de Boletos"

    def __str__(self):
        return self.nombre

class Evento(models.Model): 
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha = models.DateField()
    ciudad = models.CharField(max_length=100) 
    pais = models.CharField(max_length=100)
    estado = models.CharField(max_length=520, choices=(("activo","Activo"),("cancelado","Cancelado")), default="activo")


    # Relación con tipos de boletos disponibles para este evento
    tipos_disponibles = models.ManyToManyField(
        TipoBoleta,
        through='TipoBoletaEvento',  # Intermediario para capacidades y precios específicos
        blank=True,
        related_name="eventos"
    )

    class Meta:
        # permisos personalizados que Django crea al migrar
        permissions = [
            ("cancelar_evento", "Puede cancelar evento"),
            ("inscribirse_evento", "Puede inscribirse a un evento"),            
        ]
    
    def __str__(self):
        return self.nombre
    
    def boletos_vendidos(self):
            """Método helper para contar boletos totales vendidos."""
            return sum(boleta.cantidad for boleta in self.boletas.all())

# Intermediario para configurar capacidades y precios por tipo por evento
class TipoBoletaEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    tipo_boleta = models.ForeignKey(TipoBoleta, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio específico para este evento.")
    aforo_maximo = models.PositiveIntegerField(help_text="Capacidad máxima para este tipo de boleta.")
    aforo_vendido = models.PositiveIntegerField(default=0, editable=False)  # Actualízalo en views

    class Meta:
        unique_together = ('evento', 'tipo_boleta')  # Un tipo por evento
        verbose_name = "Configuración de Tipo de Boleta por Evento"

    def __str__(self):
        return f"{self.tipo_boleta.nombre} para {self.evento.nombre}"

# Modelo para boletas individuales (reemplaza o suplementa inscritos)
class Boleta(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="boletas")
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="boletas")
    tipo_config = models.ForeignKey(TipoBoletaEvento, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1, help_text="Número de boletos comprados.")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=[("comprada", "Comprada"), ("usada", "Usada"), ("cancelada", "Cancelada")],
        default="comprada"
    )
    # Campo para código QR o ID único si se integra con escaneo
    codigo_unico = models.CharField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "Boleta"
        verbose_name_plural = "Boletas"

    def __str__(self):
        return f"Boleta {self.codigo_unico} para {self.evento.nombre} ({self.tipo_config.tipo_boleta.nombre})"

    def save(self, *args, **kwargs):
        # Lógica para actualizar aforo_vendido en TipoBoletaEvento al comprar
        if self.estado == "comprada" and not self.pk:  # Nueva compra
            self.tipo_config.aforo_vendido += self.cantidad
            self.tipo_config.save()
        super().save(*args, **kwargs)