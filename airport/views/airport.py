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

from airport.models import Airport, Route
from airport.serializers import (
    AirportImageSerializer,
    AirportSerializer,
    RouteListSerializer,
    RouteRetrieveSerializer,
    RouteSerializer,
)
from airport.views.base import ADMIN_ONLY, param_to_int, params_to_ints


@extend_schema_view(
    list=extend_schema(
        summary="List airports",
        description=(
            "Airports with their name and the closest big city. "
            "Supports substring search by name and by city."
        ),
        parameters=[
            OpenApiParameter(
                "city",
                type=OpenApiTypes.STR,
                description="Part of the city name (ex. ?city=kyiv)",
            ),
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Part of the airport name (ex. ?name=boryspil)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve an airport",
        description="Detailed information about a single airport.",
    ),
    create=extend_schema(summary="Create an airport", description=ADMIN_ONLY),
    update=extend_schema(summary="Update an airport", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Partially update an airport", description=ADMIN_ONLY
    ),
    upload_image=extend_schema(
        summary="Upload an image",
        description=(
            "Upload or replace the image of this object. "
            "Expects multipart/form-data. " + ADMIN_ONLY
        ),
    ),
)
class AirportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Airport directory."""

    queryset = Airport.objects.all().order_by("id")
    serializer_class = AirportSerializer

    def get_serializer_class(self):
        if self.action == "upload_image":
            return AirportImageSerializer
        return AirportSerializer

    def get_queryset(self):
        queryset = self.queryset
        city = self.request.query_params.get("city")
        name = self.request.query_params.get("name")

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Upload an image for a specific airport."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List routes",
        description=(
            "Routes between pairs of airports with the distance in kilometers. "
            "The list returns airports as ids; "
            "full objects are available in the retrieve response."
        ),
        parameters=[
            OpenApiParameter(
                "source",
                type={"type": "array", "items": {"type": "number"}},
                description="Ids of departure airports (ex. ?source=3,5)",
            ),
            OpenApiParameter(
                "destination",
                type={"type": "array", "items": {"type": "number"}},
                description="Ids of arrival airports (ex. ?destination=8)",
            ),
            OpenApiParameter(
                "from_city",
                type=OpenApiTypes.STR,
                description="Departure city (ex. ?from_city=kyiv)",
            ),
            OpenApiParameter(
                "to_city",
                type=OpenApiTypes.STR,
                description="Arrival city (ex. ?to_city=frankfurt)",
            ),
            OpenApiParameter(
                "min_distance",
                type=OpenApiTypes.INT,
                description="Minimum distance in km (ex. ?min_distance=1000)",
            ),
            OpenApiParameter(
                "max_distance",
                type=OpenApiTypes.INT,
                description="Maximum distance in km (ex. ?max_distance=3000)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a route",
        description=(
            "Route with nested departure and arrival airport objects."
        ),
    ),
    create=extend_schema(summary="Create a route", description=ADMIN_ONLY),
    update=extend_schema(summary="Update a route", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Partially update a route", description=ADMIN_ONLY
    ),
)
class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Routes between airports."""

    queryset = Route.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteRetrieveSerializer
        return RouteSerializer

    def get_queryset(self):
        queryset = self.queryset

        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")
        from_city = self.request.query_params.get("from_city")
        to_city = self.request.query_params.get("to_city")
        min_distance = self.request.query_params.get("min_distance")
        max_distance = self.request.query_params.get("max_distance")

        if source:
            queryset = queryset.filter(source__id__in=params_to_ints(source))

        if destination:
            queryset = queryset.filter(
                destination__id__in=params_to_ints(destination)
            )

        if from_city:
            queryset = queryset.filter(
                source__closest_big_city__icontains=from_city
            )

        if to_city:
            queryset = queryset.filter(
                destination__closest_big_city__icontains=to_city
            )

        if min_distance:
            queryset = queryset.filter(
                distance__gte=param_to_int(min_distance, "min_distance")
            )

        if max_distance:
            queryset = queryset.filter(
                distance__lte=param_to_int(max_distance, "max_distance")
            )

        if self.action == "retrieve":
            queryset = queryset.select_related("source", "destination")
        return queryset
