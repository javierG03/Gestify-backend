"""Vistas de catálogos (departamentos y ciudades)."""

from __future__ import annotations

from rest_framework import generics
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema

from ..models import City, Department
from ..serializers import CitySerializer, DepartmentSerializer


class DepartmentListView(generics.ListAPIView):
	"""Catálogo de departamentos disponibles."""

	queryset = Department.objects.all().order_by("name")
	serializer_class = DepartmentSerializer
	permission_classes = [AllowAny]

	@extend_schema(tags=["Catálogos"], operation_id="department_list")
	def get(self, request, *args, **kwargs):  # type: ignore[override]
		return super().get(request, *args, **kwargs)


class CityListView(generics.ListAPIView):
	"""Catálogo de ciudades filtrable por departamento."""

	serializer_class = CitySerializer
	permission_classes = [AllowAny]

	@extend_schema(tags=["Catálogos"], operation_id="city_list")
	def get(self, request, *args, **kwargs):  # type: ignore[override]
		return super().get(request, *args, **kwargs)

	def get_queryset(self):
		department_id = self.request.query_params.get("department_id")
		queryset = City.objects.select_related("department").order_by("name")
		if department_id:
			queryset = queryset.filter(department_id=department_id)
		return queryset
