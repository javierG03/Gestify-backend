"""
eventos/admin.py
Configuración del admin para el módulo de eventos. Clean code y comentarios claros.
"""
from django.contrib import admin
from .models import TicketType, TicketTypeEvent, Ticket, Event

class TicketTypeEventInline(admin.TabularInline):
    model = TicketTypeEvent
    extra = 1

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    """Admin para tipos de ticket."""
    list_display = ['id', 'ticket_name', 'description']
    list_filter = ['ticket_name']
    search_fields = ['ticket_name', 'description']

@admin.register(Event)
class EventoAdmin(admin.ModelAdmin):
    """Admin para eventos."""
    list_display = ['event_name', 'date', 'country', 'location', 'city_text', 'department_text', 'status']
    inlines = [TicketTypeEventInline]

admin.site.register(Ticket)
