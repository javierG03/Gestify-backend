from django.urls import path
from .views import EventViewSet, PayUConfirmationView, TicketTypeViewSet

event_list_create = EventViewSet.as_view({'get': 'list', 'post': 'create'})
event_detail = EventViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('events/', event_list_create, name='event-list-create'),
    path('events/<int:pk>/', event_detail, name='event-detail'),
    path('events/<int:pk>/types/', EventViewSet.as_view({'get': 'tipos_disponibles'}), name='tipo-boleta-por-event'),
    path('events/<int:pk>/buy/', EventViewSet.as_view({'post': 'buy_ticket'}), name='event-comprar-boleta'),
    path('events/<int:pk>/pay/', EventViewSet.as_view({'post': 'pay'}), name='event-pagar'),
    path('events/<int:pk>/cancel/', EventViewSet.as_view({'post': 'cancelar'}), name='event-cancelar'),
    path('events/payu/confirmation/', PayUConfirmationView.as_view(), name='payu-confirmacion'),
    # Nuevo: Paths para tipos de boletas
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
]
