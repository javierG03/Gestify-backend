"""
eventos/urls.py
URLs principales del módulo de eventos. Organización por secciones y comentarios claros.
"""
from django.urls import path
from .views import (
    EventViewSet,
    TicketTypeViewSet,
    TicketValidationAPIView,
    BuyTicketAPIView,
    MyCreatedEventsAPIView,
    MyEventsAPIView,
    EventInscritosAPIView,
    DepartmentListView,
    CityListView,
    TicketAccessLogListView,
    MyTicketsAPIView,
    ResendTicketEmailAPIView,
    TicketDetailAPIView,
    EventQAView,
)

# --- Events ---
event_list_create = EventViewSet.as_view({'get': 'list', 'post': 'create'})
event_detail = EventViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # --- Events ---
    path('events/', event_list_create, name='event-list-create'),
    path('events/<int:pk>/', event_detail, name='event-detail'),
    path('events/<int:pk>/ticket-types/', EventViewSet.as_view({'get': 'ticket_types_available'}), name='event-ticket-types'),
    path('events/<int:pk>/availability/', EventViewSet.as_view({'get': 'availability'}), name='event-availability'),
    path('events/<int:pk>/buy/', BuyTicketAPIView.as_view(), name='event-buy-ticket'),
    path('events/<int:pk>/cancel/', EventViewSet.as_view({'post': 'cancelar'}), name='event-cancel'),
    path('events/<int:pk>/attendees/', EventInscritosAPIView.as_view(), name='event-attendees'),
    path('events/my-events/', MyEventsAPIView.as_view(), name='event-my-events'),
    path('organizer/my-events/', MyCreatedEventsAPIView.as_view(), name='organizer-my-events'),
    # --- Tickets del usuario ---
    path('tickets/my-tickets/', MyTicketsAPIView.as_view(), name='my-tickets'),
    # --- Ticket Detail ---
    path('tickets/<int:pk>/', TicketDetailAPIView.as_view(), name='ticket-detail'),
    # --- Reenvío de QR por email ---
    path('tickets/<int:pk>/resend/', ResendTicketEmailAPIView.as_view(), name='ticket-resend-email'),
    # --- Ticket Access Log ---
    path('tickets/<int:ticket_id>/access-log/', TicketAccessLogListView.as_view(), name='ticket-access-log'),
    # --- Ticket Types ---
    path('ticket-types/', TicketTypeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='ticket-types-list-create'),
    path('ticket-types/<int:pk>/', TicketTypeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='ticket-types-detail'),
    # --- Tickets ---
    path('tickets/validate/', TicketValidationAPIView.as_view(), name='ticket-validate'),
    # --- Departments ---
    path('departments/', DepartmentListView.as_view(), name='department-list'),
    # --- Cities ---
    path('cities/', CityListView.as_view(), name='city-list'),
    path('events/<int:event_id>/ask-ai/', EventQAView.as_view(), name='event-ask-ai'),
]
