from django.db import models

class TipoDocumento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    codigo = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name = "Tipo de documento"
        verbose_name_plural = "Tipos de documento"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom user abstraido de django
    """
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, help_text="Nombres")
    last_name = models.CharField(max_length=150, help_text="Apellidos")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Teléfono de contacto")
    birth_date = models.DateField(blank=True, null=True, help_text="Fecha de nacimiento")
    document_type = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, blank=True, null=True, help_text="Tipo de documento")
    document = models.CharField(max_length=30, blank=True, null=True, unique=True, help_text="Número de documento")
    country = models.CharField(max_length=50, blank=True, null=True, default="Colombia", help_text="País de residencia")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Fecha de creación del usuario")
    updated_at = models.DateTimeField(auto_now=True, help_text="Fecha de última actualización del usuario")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="Ciudad de residencia")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    