from django.db.models import Count, F, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from airport.models import (
    Airport,
    Route,
    Crew,
    AirplaneType,
    Airplane,
    Flight,
    Order,
    Ticket
)
from airport.serializers import (
    AirportSerializer,
    RouteSerializer,
    CrewSerializer,
    AirplaneTypeSerializer,
    AirplaneSerializer,
    FlightSerializer,
    OrderSerializer,
    TicketSerializer,
    RouteListSerializer,
    RouteRetrieveSerializer,
    CrewRetrieveSerializer,
    CrewListSerializer,
    AirplaneListSerializer,
    AirplaneRetrieveSerializer,
    AirplaneImageSerializer,
    AirportImageSerializer,
    FlightListSerializer,
    FlightRetrieveSerializer,
    TicketListSerializer,
    TicketRetrieveSerializer
)

ADMIN_ONLY = "Admin only (is_staff)."


def params_to_ints(query_string):
    """
    Convert a string of format '1,2,3' to a list of integers [1, 2, 3].
    Non-numeric values are ignored.
    """
    return [
        int(str_id)
        for str_id in query_string.split(",")
        if str_id.strip().isdigit()
    ]


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
            queryset = queryset.filter(distance__gte=min_distance)

        if max_distance:
            queryset = queryset.filter(distance__lte=max_distance)

        if self.action == "retrieve":
            queryset = queryset.select_related("source", "destination")
        return queryset


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
            # seats is a @property with no column in the database,
            # so it is calculated on the database side with F()
            queryset = queryset.annotate(
                total_seats=F("rows") * F("seats_in_row")
            )

            if min_seats:
                queryset = queryset.filter(total_seats__gte=min_seats)

            if max_seats:
                queryset = queryset.filter(total_seats__lte=max_seats)

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
            queryset = queryset.filter(departure_time__date=date)

        if date_from:
            queryset = queryset.filter(departure_time__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(departure_time__date__lte=date_to)

        if from_city:
            queryset = queryset.filter(
                route__source__closest_big_city__icontains=from_city
            )

        if to_city:
            queryset = queryset.filter(
                route__destination__closest_big_city__icontains=to_city
            )

        if self.action in ("list", "retrieve"):
            # free seats = airplane capacity - number of sold tickets;
            # distinct=True is required because the crew filter (M2M)
            # duplicates rows
            queryset = queryset.annotate(
                tickets_available=(
                    F("airplane__rows")
                    * F("airplane__seats_in_row")
                    - Count("tickets", distinct=True)
                )
            )

            if available and available.lower() in ("true", "1", "yes"):
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


@extend_schema_view(
    list=extend_schema(
        summary="List my orders",
        description=(
            "Returns only the orders of the current user. "
            "Other users' orders are not reachable through the API, "
            "not even for an admin."
        ),
        parameters=[
            OpenApiParameter(
                "date_from",
                type=OpenApiTypes.DATE,
                description="Created on or after this date (ex. ?date_from=2026-11-01)",
            ),
            OpenApiParameter(
                "date_to",
                type=OpenApiTypes.DATE,
                description="Created on or before this date (ex. ?date_to=2026-11-30)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve an order",
        description="Available only if the order belongs to the current user.",
    ),
    create=extend_schema(
        summary="Create an order",
        description=(
            "The user field is filled automatically from the token, "
            "there is no need to send it in the request body."
        ),
    ),
    update=extend_schema(summary="Update an order"),
    partial_update=extend_schema(summary="Partially update an order"),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Orders of the current user."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List tickets",
        description=(
            "Tickets with their row and seat number. "
            "The (flight, row, seat) triple is unique: "
            "the same seat cannot be sold twice for one flight."
        ),
        parameters=[
            OpenApiParameter(
                "flight",
                type={"type": "array", "items": {"type": "number"}},
                description="Flight ids (ex. ?flight=14,23)",
            ),
            OpenApiParameter(
                "order",
                type={"type": "array", "items": {"type": "number"}},
                description="Order ids (ex. ?order=3)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a ticket",
        description="Ticket with nested flight and order data.",
    ),
    create=extend_schema(summary="Create a ticket"),
    update=extend_schema(summary="Update a ticket"),
    partial_update=extend_schema(summary="Partially update a ticket"),
)
class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Tickets: a seat on a particular flight within an order."""

    queryset = Ticket.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        elif self.action == "retrieve":
            return TicketRetrieveSerializer
        return TicketSerializer

    def get_queryset(self):
        queryset = self.queryset

        flight = self.request.query_params.get("flight")
        order = self.request.query_params.get("order")

        if flight:
            queryset = queryset.filter(flight__id__in=params_to_ints(flight))

        if order:
            queryset = queryset.filter(order__id__in=params_to_ints(order))

        if self.action == "retrieve":
            queryset = queryset.select_related(
                "order",
                "flight__airplane__airplane_type",
                "flight__route__source",
                "flight__route__destination",
            ).prefetch_related("flight__crew")
        return queryset
