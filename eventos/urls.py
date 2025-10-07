from django.urls import path
from .views import EventoViewSet, PayUConfirmationView, TipoBoletaViewSet

evento_list_create = EventoViewSet.as_view({'get': 'list', 'post': 'create'})
evento_detail = EventoViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('events/', evento_list_create, name='evento-list-create'),
    path('events/<int:pk>/', evento_detail, name='evento-detail'),
    path('events/<int:pk>/types/', EventoViewSet.as_view({'get': 'tipos_disponibles'}), name='tipo-boleta-por-evento'),
    path('events/<int:pk>/buy/', EventoViewSet.as_view({'post': 'comprar_boleta'}), name='evento-comprar-boleta'),
    path('events/<int:pk>/pay/', EventoViewSet.as_view({'post': 'pagar'}), name='evento-pagar'),
    path('events/<int:pk>/cancel/', EventoViewSet.as_view({'post': 'cancelar'}), name='evento-cancelar'),
    path('events/payu/confirmation/', PayUConfirmationView.as_view(), name='payu-confirmacion'),
    # Nuevo: Paths para tipos de boletas
    path('tipos-boletas/', TipoBoletaViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='tipos-boletas-list-create'),
    path('tipos-boletas/<int:pk>/', TipoBoletaViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tipos-boletas-detail'),
]
