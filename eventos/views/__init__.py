"""Punto de entrada para exponer las vistas del módulo de eventos."""

from .catalogs import CityListView, DepartmentListView
from .events import BuyTicketAPIView, EventInscritosAPIView, EventViewSet, MyEventsAPIView, MyCreatedEventsAPIView
from .ticket_types import TicketTypeViewSet
from .tickets import (
	MyTicketsAPIView,
	ResendTicketEmailAPIView,
	TicketAccessLogListView,
	TicketValidationAPIView,
	TicketDetailAPIView,
)
from .ia_assistant import EventQAView # <-- AÑADIR ESTO
__all__ = [
	"EventViewSet",
	"BuyTicketAPIView",
	"EventInscritosAPIView",
	"MyEventsAPIView",
	"MyTicketsAPIView",
	"ResendTicketEmailAPIView",
	"MyCreatedEventsAPIView",
	"TicketAccessLogListView",
	"TicketValidationAPIView",
	"TicketDetailAPIView",
	"TicketTypeViewSet",
	"DepartmentListView",
	"CityListView",
	"EventQAView", # <-- AÑADIR ESTO
]
