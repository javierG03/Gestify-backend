from django.contrib import admin
from .models import TipoBoleta, TipoBoletaEvento, Boleta, Evento  # Incluye otros si quieres

@admin.register(TipoBoleta)
class TipoBoletaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'precio_base']
    list_filter = ['nombre']
    search_fields = ['nombre', 'descripcion']

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'fecha', 'ciudad', 'estado']  

# Registra los otros modelos si no lo has hecho
admin.site.register(TipoBoletaEvento)
admin.site.register(Boleta)
