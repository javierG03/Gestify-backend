"""Vistas para gestionar tipos de ticket reutilizables."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from usuarios.permissions import IsAdminGroup

from ..models import TicketType
from ..serializers import TicketTypeSerializer


class TicketTypeViewSet(viewsets.ModelViewSet):
	"""CRUD de tipos de ticket reutilizables entre eventos."""

	queryset = TicketType.objects.all().order_by("ticket_name")
	serializer_class = TicketTypeSerializer
	authentication_classes = [TokenAuthentication]

	def get_permissions(self):
		if getattr(self, "action", None) in {"create", "update", "partial_update", "destroy"}:
			permissions = [IsAuthenticated, IsAdminGroup]
		else:
			permissions = [AllowAny]
		return [perm() for perm in permissions]

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_list")
	def list(self, request, *args, **kwargs):  # type: ignore[override]
		return super().list(request, *args, **kwargs)

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_create")
	def create(self, request, *args, **kwargs):  # type: ignore[override]
		return super().create(request, *args, **kwargs)

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_detail")
	def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
		return super().retrieve(request, *args, **kwargs)

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_update")
	def update(self, request, *args, **kwargs):  # type: ignore[override]
		return super().update(request, *args, **kwargs)

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_partial_update")
	def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
		return super().partial_update(request, *args, **kwargs)

	@extend_schema(tags=["Tipos de tickets"], operation_id="ticket_type_delete")
	def destroy(self, request, *args, **kwargs):  # type: ignore[override]
		super().destroy(request, *args, **kwargs)
		return Response({"message": "Tipo de ticket eliminado correctamente."}, status=status.HTTP_200_OK)
