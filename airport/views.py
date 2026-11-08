from django.db.models import Count, F, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins
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
    FlightListSerializer,
    FlightRetrieveSerializer,
    TicketListSerializer,
    TicketRetrieveSerializer,
)


def params_to_ints(qs: str) -> list[int]:
    """'1,3,5' -> [1, 3, 5]. Нечислові значення ігноруються."""
    return [int(str_id) for str_id in qs.split(",") if str_id.strip().isdigit()]


class AirportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Airport.objects.all().order_by("id")
    serializer_class = AirportSerializer

    def get_queryset(self):
        queryset = self.queryset

        name = self.request.query_params.get("name")
        city = self.request.query_params.get("city")

        if name:
            queryset = queryset.filter(name__icontains=name)

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина назви аеропорту (ex. ?name=бориспіль)",
            ),
            OpenApiParameter(
                "city",
                type=OpenApiTypes.STR,
                description="Частина назви найближчого міста (ex. ?city=київ)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
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
            queryset = queryset.filter(source_id__in=params_to_ints(source))

        if destination:
            queryset = queryset.filter(
                destination_id__in=params_to_ints(destination)
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "source",
                type={"type": "array", "items": {"type": "number"}},
                description="Id аеропортів відправлення (ex. ?source=3,5)",
            ),
            OpenApiParameter(
                "destination",
                type={"type": "array", "items": {"type": "number"}},
                description="Id аеропортів призначення (ex. ?destination=8)",
            ),
            OpenApiParameter(
                "from_city",
                type=OpenApiTypes.STR,
                description="Місто відправлення (ex. ?from_city=київ)",
            ),
            OpenApiParameter(
                "to_city",
                type=OpenApiTypes.STR,
                description="Місто призначення (ex. ?to_city=frankfurt)",
            ),
            OpenApiParameter(
                "min_distance",
                type=OpenApiTypes.INT,
                description="Мінімальна відстань, км (ex. ?min_distance=1000)",
            ),
            OpenApiParameter(
                "max_distance",
                type=OpenApiTypes.INT,
                description="Максимальна відстань, км (ex. ?max_distance=3000)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина імені або прізвища (ex. ?name=kov)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AirplaneTypeViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = AirplaneType.objects.all().order_by("id")
    serializer_class = AirplaneTypeSerializer

    def get_queryset(self):
        queryset = self.queryset

        name = self.request.query_params.get("name")

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина назви типу (ex. ?name=wide)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AirplaneViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Airplane.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        elif self.action == "retrieve":
            return AirplaneRetrieveSerializer
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
                airplane_type_id__in=params_to_ints(airplane_type)
            )

        if min_seats or max_seats:
            # seats — це @property, у БД такої колонки немає,
            # тому рахуємо її на боці бази через F()
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина назви літака (ex. ?name=boeing)",
            ),
            OpenApiParameter(
                "airplane_type",
                type={"type": "array", "items": {"type": "number"}},
                description="Id типів літака (ex. ?airplane_type=1,2)",
            ),
            OpenApiParameter(
                "min_seats",
                type=OpenApiTypes.INT,
                description="Мінімальна кількість місць (ex. ?min_seats=200)",
            ),
            OpenApiParameter(
                "max_seats",
                type=OpenApiTypes.INT,
                description="Максимальна кількість місць (ex. ?max_seats=400)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FlightViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Flight.objects.all().order_by("departure_time")

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        elif self.action == "retrieve":
            return FlightRetrieveSerializer
        return FlightSerializer

    def get_queryset(self):
        queryset = self.queryset

        route = self.request.query_params.get("route")
        airplane_type = self.request.query_params.get("airplane_type")
        crew = self.request.query_params.get("crew")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        from_city = self.request.query_params.get("from_city")
        to_city = self.request.query_params.get("to_city")
        available = self.request.query_params.get("available")

        if route:
            queryset = queryset.filter(route_id__in=params_to_ints(route))

        if airplane_type:
            queryset = queryset.filter(
                airplane__airplane_type_id__in=params_to_ints(airplane_type)
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

        if available and available.lower() in ("true", "1", "yes"):
            queryset = queryset.annotate(
                tickets_available=(
                    F("airplane__rows")
                    * F("airplane__seats_in_row")
                    - Count("tickets")
                )
            ).filter(tickets_available__gt=0)

        if self.action == "list":
            queryset = queryset.prefetch_related("crew")
        elif self.action == "retrieve":
            queryset = queryset.select_related(
                "airplane__airplane_type",
                "route__source",
                "route__destination",
            ).prefetch_related("crew")

        # фільтр по crew — це M2M, джойн може продублювати рейси
        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "route",
                type={"type": "array", "items": {"type": "number"}},
                description="Id маршрутів (ex. ?route=2,5)",
            ),
            OpenApiParameter(
                "airplane_type",
                type={"type": "array", "items": {"type": "number"}},
                description="Id типів літака (ex. ?airplane_type=2)",
            ),
            OpenApiParameter(
                "crew",
                type={"type": "array", "items": {"type": "number"}},
                description="Id членів екіпажу (ex. ?crew=5,18)",
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Точна дата вильоту (ex. ?date=2026-11-12)",
            ),
            OpenApiParameter(
                "date_from",
                type=OpenApiTypes.DATE,
                description="Виліт не раніше (ex. ?date_from=2026-11-10)",
            ),
            OpenApiParameter(
                "date_to",
                type=OpenApiTypes.DATE,
                description="Виліт не пізніше (ex. ?date_to=2026-11-15)",
            ),
            OpenApiParameter(
                "from_city",
                type=OpenApiTypes.STR,
                description="Місто відправлення (ex. ?from_city=київ)",
            ),
            OpenApiParameter(
                "to_city",
                type=OpenApiTypes.STR,
                description="Місто призначення (ex. ?to_city=seoul)",
            ),
            OpenApiParameter(
                "available",
                type=OpenApiTypes.BOOL,
                description="Лише рейси з вільними місцями (ex. ?available=true)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = self.queryset

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "date_from",
                type=OpenApiTypes.DATE,
                description="Створені не раніше (ex. ?date_from=2026-11-01)",
            ),
            OpenApiParameter(
                "date_to",
                type=OpenApiTypes.DATE,
                description="Створені не пізніше (ex. ?date_to=2026-11-30)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Ticket.objects.all()

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
            queryset = queryset.filter(flight_id__in=params_to_ints(flight))

        if order:
            queryset = queryset.filter(order_id__in=params_to_ints(order))

        if self.action == "retrieve":
            queryset = queryset.select_related(
                "order",
                "flight__airplane__airplane_type",
                "flight__route__source",
                "flight__route__destination",
            ).prefetch_related("flight__crew")

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "flight",
                type={"type": "array", "items": {"type": "number"}},
                description="Id рейсів (ex. ?flight=14,23)",
            ),
            OpenApiParameter(
                "order",
                type={"type": "array", "items": {"type": "number"}},
                description="Id замовлень (ex. ?order=3)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
