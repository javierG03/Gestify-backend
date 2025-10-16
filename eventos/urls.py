from django.urls import path
from .views import (
    EventViewSet,
    PayUConfirmationView,
    TicketTypeViewSet,
    TicketValidationView,
    BuyTicketAPIView,
    MyEventsAPIView,
    PayTicketAPIView,
    EventInscritosAPIView
)

event_list_create = EventViewSet.as_view({'get': 'list', 'post': 'create'})
event_detail = EventViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # --- Eventos ---
    path('events/', event_list_create, name='event-list-create'),
    path('events/<int:pk>/', event_detail, name='event-detail'),
    path('events/<int:pk>/types/', EventViewSet.as_view({'get': 'ticket_types_available'}), name='tipo-boleta-por-event'),
    path('events/<int:pk>/buy/', BuyTicketAPIView.as_view(), name='event-comprar-boleta'),
    path('events/<int:pk>/pay/', PayTicketAPIView.as_view(), name='event-pagar'),
    path('events/<int:pk>/cancel/', EventViewSet.as_view({'post': 'cancelar'}), name='event-cancelar'),
    path('events/<int:pk>/inscritos/', EventInscritosAPIView.as_view(), name='event-inscritos'),
    path('events/my/', MyEventsAPIView.as_view(), name='event-my-events'),

    # --- Pagos ---
    path('events/payu/confirmation/', PayUConfirmationView.as_view(), name='payu-confirmacion'),

    # --- Tipos de Boletas ---
    path('tipos-boletas/', TicketTypeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='tipos-boletas-list-create'),
    path('tipos-boletas/<int:pk>/', TicketTypeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tipos-boletas-detail'),

    # --- Tickets ---
    path('tickets/validate/', TicketValidationView.as_view(), name='ticket-validate'),
]
