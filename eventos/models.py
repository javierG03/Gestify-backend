from django.db import models
from usuarios.models import CustomUser
from django.conf import settings
# Create your models here.
class Evento(models.Model): 
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha = models.DateField()
    ubicacion = models.CharField(max_length=200)
    aforo = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=520, choices=(("activo","Activo"),("cancelado","Cancelado")), default="activo")

    # Relacion muchos a muchos para inscripciones
    inscritos = models.ManyToManyField(CustomUser, related_name="eventos_inscritos", blank=True)

    class Meta:
        # permisos personalizados que Django crea al migrar
        permissions = [
            ("cancelar_evento", "Puede cancelar evento"),
            ("inscribirse_evento", "Puede inscribirse a un evento"),            
        ]
    
    def __str__(self):
        return self.nombre
    
