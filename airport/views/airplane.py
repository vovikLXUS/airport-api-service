from django.db.models import F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from airport.models import Airplane, AirplaneType
from airport.serializers import (
    AirplaneImageSerializer,
    AirplaneListSerializer,
    AirplaneRetrieveSerializer,
    AirplaneSerializer,
    AirplaneTypeSerializer,
)
from airport.views.base import ADMIN_ONLY, param_to_int, params_to_ints


@extend_schema_view(
    list=extend_schema(
        summary="List airplane types",
        description="Airplane categories: narrow-body, wide-body, regional and so on.",
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Part of the type name (ex. ?name=wide)",
            ),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve an airplane type"),
    create=extend_schema(summary="Create an airplane type", description=ADMIN_ONLY),
    update=extend_schema(summary="Update an airplane type", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Partially update an airplane type", description=ADMIN_ONLY
    ),
)
class AirplaneTypeViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Airplane type directory."""

    queryset = AirplaneType.objects.all().order_by("id")
    serializer_class = AirplaneTypeSerializer

    def get_queryset(self):
        queryset = self.queryset
        name = self.request.query_params.get("name")

        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List airplanes",
        description=(
            "Airplanes with calculated capacity (seats = rows * seats_in_row). "
            "Capacity filters are evaluated on the database side."
        ),
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Part of the airplane name (ex. ?name=boeing)",
            ),
            OpenApiParameter(
                "airplane_type",
                type={"type": "array", "items": {"type": "number"}},
                description="Airplane type ids (ex. ?airplane_type=1,2)",
            ),
            OpenApiParameter(
                "min_seats",
                type=OpenApiTypes.INT,
                description="Minimum number of seats (ex. ?min_seats=200)",
            ),
            OpenApiParameter(
                "max_seats",
                type=OpenApiTypes.INT,
                description="Maximum number of seats (ex. ?max_seats=400)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve an airplane",
        description=(
            "Detailed card: number of rows, seats per row "
            "and the nested airplane type."
        ),
    ),
    create=extend_schema(summary="Create an airplane", description=ADMIN_ONLY),
    update=extend_schema(summary="Update an airplane", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Partially update an airplane", description=ADMIN_ONLY
    ),
    upload_image=extend_schema(
        summary="Upload an image",
        description=(
            "Upload or replace the image of this object. "
            "Expects multipart/form-data. " + ADMIN_ONLY
        ),
    ),
)
class AirplaneViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Airplane fleet."""

    queryset = Airplane.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        elif self.action == "retrieve":
            return AirplaneRetrieveSerializer
        elif self.action == "upload_image":
            return AirplaneImageSerializer
        return AirplaneSerializer

    def get_queryset(self):
        queryset = self.queryset

        name = self.request.query_params.get("name")
        airplane_type = self.request.query_params.get("airplane_type")
        min_seats = self.request.query_params.get("min_seats")
        max_seats = self.request.query_params.get("max_seats")

        if name:
            queryset = queryset.filter(name__icontains=name)

        if airplane_type:
            queryset = queryset.filter(
                airplane_type__id__in=params_to_ints(airplane_type)
            )

        if min_seats or max_seats:
            queryset = queryset.annotate(
                total_seats=F("rows") * F("seats_in_row")
            )

            if min_seats:
                queryset = queryset.filter(
                    total_seats__gte=param_to_int(min_seats, "min_seats")
                )

            if max_seats:
                queryset = queryset.filter(
                    total_seats__lte=param_to_int(max_seats, "max_seats")
                )

        if self.action == "retrieve":
            queryset = queryset.select_related("airplane_type")
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Upload an image for a specific airplane."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
