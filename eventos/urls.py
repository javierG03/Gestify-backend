from django.urls import path
from .views import EventoViewSet, PayUConfirmationView

urlpatterns = [
    path('events/', EventoViewSet.as_view({'get': 'list', 'post': 'create'}), name='evento-list-create'),
    path('events/<int:pk>/', EventoViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='evento-detail'),
    path('events/<int:pk>/cancel/', EventoViewSet.as_view({'post': 'cancelar'}), name='evento-cancelar'),
    path('events/<int:pk>/inscription/', EventoViewSet.as_view({'post': 'inscribirse'}), name='event-inscription'),
    path('events/<int:pk>/pay/', EventoViewSet.as_view({'post': 'pagar'}), name='pay-inscription'),
    path('events/payu/confirmation/', PayUConfirmationView.as_view(), name='payu-confirmacion'),
]