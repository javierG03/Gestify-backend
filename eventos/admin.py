from django.contrib import admin
from .models import TicketType, TicketTypeEvent, Ticket, Event  # Incluye otros si quieres

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'ticket_name', 'description']
    list_filter = ['ticket_name']
    search_fields = ['ticket_name', 'description']

@admin.register(Event)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'date', 'city', 'country', 'status']  

# Registra los otros modelos si no lo has hecho
admin.site.register(TicketTypeEvent)
admin.site.register(Ticket)
