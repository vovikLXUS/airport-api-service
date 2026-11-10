from django.db.models import Count, F, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from airport.models import Crew, Flight
from airport.serializers import (
    CrewListSerializer,
    CrewRetrieveSerializer,
    CrewSerializer,
    FlightListSerializer,
    FlightRetrieveSerializer,
    FlightSerializer,
)
from airport.views.base import (
    ADMIN_ONLY,
    param_to_bool,
    param_to_date,
    params_to_ints,
)


@extend_schema_view(
    list=extend_schema(
        summary="List crew members",
        description=(
            "Short list of crew members. "
            "The name filter matches both the first and the last name."
        ),
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Part of the first or last name (ex. ?name=kov)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a crew member",
        description="Returns the full name (first_name + last_name).",
    ),
    create=extend_schema(
        summary="Create a crew member", description=ADMIN_ONLY
    ),
    update=extend_schema(
        summary="Update a crew member", description=ADMIN_ONLY
    ),
    partial_update=extend_schema(
        summary="Partially update a crew member", description=ADMIN_ONLY
    ),
)
class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Crew members that can be assigned to flights."""

    queryset = Crew.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return CrewListSerializer
        elif self.action == "retrieve":
            return CrewRetrieveSerializer
        return CrewSerializer

    def get_queryset(self):
        queryset = self.queryset
        name = self.request.query_params.get("name")

        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List flights",
        description=(
            "Flights with the tickets_available field - how many seats are "
            "still free (airplane capacity minus sold tickets). "
            "Filters can be combined: "
            "?from_city=kyiv&date_from=2026-11-10&available=true"
        ),
        parameters=[
            OpenApiParameter(
                "routes",
                type={"type": "array", "items": {"type": "number"}},
                description="Route ids (ex. ?routes=2,5)",
            ),
            OpenApiParameter(
                "airplane_type",
                type={"type": "array", "items": {"type": "number"}},
                description="Airplane type ids (ex. ?airplane_type=2)",
            ),
            OpenApiParameter(
                "crew",
                type={"type": "array", "items": {"type": "number"}},
                description="Crew member ids (ex. ?crew=5,18)",
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Exact departure date (ex. ?date=2026-11-12)",
            ),
            OpenApiParameter(
                "date_from",
                type=OpenApiTypes.DATE,
                description="Departure on or after this date (ex. ?date_from=2026-11-10)",
            ),
            OpenApiParameter(
                "date_to",
                type=OpenApiTypes.DATE,
                description="Departure on or before this date (ex. ?date_to=2026-11-15)",
            ),
            OpenApiParameter(
                "from_city",
                type=OpenApiTypes.STR,
                description="Departure city (ex. ?from_city=kyiv)",
            ),
            OpenApiParameter(
                "to_city",
                type=OpenApiTypes.STR,
                description="Arrival city (ex. ?to_city=seoul)",
            ),
            OpenApiParameter(
                "available",
                type=OpenApiTypes.BOOL,
                description="Only flights with free seats (ex. ?available=true)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a flight",
        description=(
            "Full flight card: nested route with airports, airplane with its "
            "type, the assigned crew and the number of free seats."
        ),
    ),
    create=extend_schema(summary="Create a flight", description=ADMIN_ONLY),
    update=extend_schema(summary="Update a flight", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Partially update a flight", description=ADMIN_ONLY
    ),
)
class FlightViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Flights: route + airplane + departure and arrival time."""

    queryset = Flight.objects.all().order_by("departure_time")

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        elif self.action == "retrieve":
            return FlightRetrieveSerializer
        return FlightSerializer

    def get_queryset(self):
        queryset = self.queryset

        routes = self.request.query_params.get("routes")
        airplane_type = self.request.query_params.get("airplane_type")
        crew = self.request.query_params.get("crew")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        from_city = self.request.query_params.get("from_city")
        to_city = self.request.query_params.get("to_city")
        available = self.request.query_params.get("available")

        if routes:
            queryset = queryset.filter(route__id__in=params_to_ints(routes))

        if airplane_type:
            queryset = queryset.filter(
                airplane__airplane_type__id__in=params_to_ints(airplane_type)
            )

        if crew:
            queryset = queryset.filter(crew__id__in=params_to_ints(crew))

        if date:
            queryset = queryset.filter(
                departure_time__date=param_to_date(date, "date")
            )

        if date_from:
            queryset = queryset.filter(
                departure_time__date__gte=param_to_date(date_from, "date_from")
            )

        if date_to:
            queryset = queryset.filter(
                departure_time__date__lte=param_to_date(date_to, "date_to")
            )

        if from_city:
            queryset = queryset.filter(
                route__source__closest_big_city__icontains=from_city
            )

        if to_city:
            queryset = queryset.filter(
                route__destination__closest_big_city__icontains=to_city
            )

        if self.action in ("list", "retrieve"):
            queryset = queryset.annotate(
                tickets_available=(
                    F("airplane__rows")
                    * F("airplane__seats_in_row")
                    - Count("tickets", distinct=True)
                )
            )

            if available is not None and param_to_bool(available, "available"):
                queryset = queryset.filter(tickets_available__gt=0)

        if self.action == "list":
            queryset = queryset.select_related(
                "route", "airplane"
            ).prefetch_related("crew")
        elif self.action == "retrieve":
            queryset = queryset.select_related(
                "airplane__airplane_type",
                "route__source",
                "route__destination",
            ).prefetch_related("crew")
        return queryset.distinct()
