from django.db.models import Count, F, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
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
    TicketRetrieveSerializer
)

ADMIN_ONLY = "Доступно лише адміністратору (is_staff)."


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
        summary="Список аеропортів",
        description=(
            "Аеропорти з назвою та найближчим великим містом. "
            "Підтримує пошук за підрядком у назві та в місті."
        ),
        parameters=[
            OpenApiParameter(
                "city",
                type=OpenApiTypes.STR,
                description="Частина назви міста (ex. ?city=київ)",
            ),
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина назви аеропорту (ex. ?name=бориспіль)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Аеропорт за id",
        description="Детальна інформація про один аеропорт.",
    ),
    create=extend_schema(summary="Створити аеропорт", description=ADMIN_ONLY),
    update=extend_schema(summary="Оновити аеропорт", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Частково оновити аеропорт", description=ADMIN_ONLY
    ),
)
class AirportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Довідник аеропортів."""

    queryset = Airport.objects.all().order_by("id")
    serializer_class = AirportSerializer

    def get_queryset(self):
        queryset = self.queryset
        city = self.request.query_params.get("city")
        name = self.request.query_params.get("name")

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="Список маршрутів",
        description=(
            "Маршрути між парами аеропортів із відстанню в кілометрах. "
            "У списку аеропорти подані як id; "
            "повні об'єкти — у відповіді на retrieve."
        ),
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
        ],
    ),
    retrieve=extend_schema(
        summary="Маршрут за id",
        description=(
            "Маршрут із розгорнутими об'єктами аеропортів "
            "відправлення та призначення."
        ),
    ),
    create=extend_schema(summary="Створити маршрут", description=ADMIN_ONLY),
    update=extend_schema(summary="Оновити маршрут", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Частково оновити маршрут", description=ADMIN_ONLY
    ),
)
class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Маршрути між аеропортами."""

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
        summary="Список екіпажу",
        description=(
            "Скорочений перелік членів екіпажу. "
            "Пошук за ім'ям шукає збіг і в імені, і в прізвищі."
        ),
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина імені або прізвища (ex. ?name=kov)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Член екіпажу за id",
        description="Повертає повне ім'я (first_name + last_name).",
    ),
    create=extend_schema(
        summary="Додати члена екіпажу", description=ADMIN_ONLY
    ),
    update=extend_schema(
        summary="Оновити члена екіпажу", description=ADMIN_ONLY
    ),
    partial_update=extend_schema(
        summary="Частково оновити члена екіпажу", description=ADMIN_ONLY
    ),
)
class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Члени екіпажу, яких призначають на рейси."""

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
        summary="Список типів літаків",
        description="Категорії літаків: narrow-body, wide-body, regional тощо.",
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Частина назви типу (ex. ?name=wide)",
            ),
        ],
    ),
    retrieve=extend_schema(summary="Тип літака за id"),
    create=extend_schema(summary="Створити тип літака", description=ADMIN_ONLY),
    update=extend_schema(summary="Оновити тип літака", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Частково оновити тип літака", description=ADMIN_ONLY
    ),
)
class AirplaneTypeViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Довідник типів літаків."""

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
        summary="Список літаків",
        description=(
            "Літаки з обчисленою місткістю (seats = rows × seats_in_row). "
            "Фільтри за місткістю працюють на боці БД."
        ),
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
                description="Мінімум місць у літаку (ex. ?min_seats=200)",
            ),
            OpenApiParameter(
                "max_seats",
                type=OpenApiTypes.INT,
                description="Максимум місць у літаку (ex. ?max_seats=400)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Літак за id",
        description=(
            "Детальна картка: кількість рядів, місць у ряду "
            "та розгорнутий тип літака."
        ),
    ),
    create=extend_schema(summary="Створити літак", description=ADMIN_ONLY),
    update=extend_schema(summary="Оновити літак", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Частково оновити літак", description=ADMIN_ONLY
    ),
)
class AirplaneViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Парк літаків."""

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
                airplane_type__id__in=params_to_ints(airplane_type)
            )

        if min_seats or max_seats:
            # seats - це @property, колонки в БД немає,
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


@extend_schema_view(
    list=extend_schema(
        summary="Список рейсів",
        description=(
            "Рейси з полем tickets_available — скільки місць ще вільно "
            "(місткість літака мінус продані квитки). "
            "Фільтри можна комбінувати: "
            "?from_city=київ&date_from=2026-11-10&available=true"
        ),
        parameters=[
            OpenApiParameter(
                "routes",
                type={"type": "array", "items": {"type": "number"}},
                description="Id маршрутів (ex. ?routes=2,5)",
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
        ],
    ),
    retrieve=extend_schema(
        summary="Рейс за id",
        description=(
            "Повна картка рейсу: розгорнутий маршрут із аеропортами, "
            "літак із типом, склад екіпажу та кількість вільних місць."
        ),
    ),
    create=extend_schema(summary="Створити рейс", description=ADMIN_ONLY),
    update=extend_schema(summary="Оновити рейс", description=ADMIN_ONLY),
    partial_update=extend_schema(
        summary="Частково оновити рейс", description=ADMIN_ONLY
    ),
)
class FlightViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Рейси: маршрут + літак + час вильоту та прильоту."""

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
            # вільні місця = місткість літака - кількість проданих квитків;
            # distinct=True потрібен, бо фільтр по crew (M2M) дублює рядки
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
        summary="Мої замовлення",
        description=(
            "Повертає лише замовлення поточного користувача. "
            "Чужі замовлення недоступні навіть адміністратору через API."
        ),
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
        ],
    ),
    retrieve=extend_schema(
        summary="Замовлення за id",
        description="Доступне, лише якщо замовлення належить поточному користувачу.",
    ),
    create=extend_schema(
        summary="Створити замовлення",
        description=(
            "Поле user заповнюється автоматично з токена — "
            "передавати його в тілі запиту не потрібно."
        ),
    ),
    update=extend_schema(summary="Оновити замовлення"),
    partial_update=extend_schema(summary="Частково оновити замовлення"),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Замовлення поточного користувача."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer

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
        summary="Список квитків",
        description=(
            "Квитки з номером ряду та місця. "
            "Пара (рейс, ряд, місце) унікальна: "
            "одне місце не можна продати двічі на один рейс."
        ),
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
        ],
    ),
    retrieve=extend_schema(
        summary="Квиток за id",
        description="Квиток із розгорнутими даними рейсу та замовлення.",
    ),
    create=extend_schema(summary="Створити квиток"),
    update=extend_schema(summary="Оновити квиток"),
    partial_update=extend_schema(summary="Частково оновити квиток"),
)
class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Квитки: місце на конкретному рейсі в межах замовлення."""

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
