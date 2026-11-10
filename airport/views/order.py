from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from airport.models import Order, Ticket
from airport.serializers import (
    OrderListSerializer,
    OrderSerializer,
    TicketListSerializer,
    TicketRetrieveSerializer,
)
from airport.views.base import param_to_date, params_to_ints


@extend_schema_view(
    list=extend_schema(
        summary="List my orders",
        description=(
            "Returns only the orders of the current user, each with its "
            "tickets. Other users' orders are not reachable through the API."
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
        summary="Create an order with tickets",
        description=(
            "Books one or more seats in a single atomic request. The user "
            "field is filled from the token. If any seat is already taken or "
            "out of range, nothing is written: neither the order nor the "
            "other tickets."
        ),
    ),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Orders of the current user, each holding one or more tickets."""

    queryset = Order.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return OrderListSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=param_to_date(date_from, "date_from")
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=param_to_date(date_to, "date_to")
            )

        if self.action in ("list", "retrieve"):
            queryset = queryset.prefetch_related("tickets__flight")

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List my tickets",
        description=(
            "Tickets that belong to the current user, with their row and "
            "seat number. Tickets are created through an order, so this "
            "endpoint is read-only."
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
)
class TicketViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """Tickets: a seat on a particular flight within an order."""

    queryset = Ticket.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TicketRetrieveSerializer
        return TicketListSerializer

    def get_queryset(self):
        queryset = self.queryset.filter(order__user=self.request.user)

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
