# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom user abstraido de django
    """
    first_name = None
    last_name = None
    username = models.CharField(max_length=150, unique=True)  # ← Asegurar que esté
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    