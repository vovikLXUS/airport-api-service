from django.db.models import prefetch_related_objects
from django.shortcuts import render
from rest_framework import viewsets, mixins
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
    TicketSerializer, RouteListSerializer, RouteRetrieveSerializer, CrewRetrieveSerializer, CrewListSerializer,
    AirplaneListSerializer, AirplaneRetrieveSerializer, FlightListSerializer, FlightRetrieveSerializer,
    TicketListSerializer, TicketRetrieveSerializer
)


class AirportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer


class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Route.objects.all().select_related()

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteRetrieveSerializer
        return RouteSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "retrieve":
            queryset = queryset.select_related("source", "destination")
        return queryset


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Crew.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return CrewListSerializer
        elif self.action == "retrieve":
            return CrewRetrieveSerializer
        return CrewSerializer


class AirplaneTypeViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "retrieve":
            queryset = queryset.select_related("airplane_type")
        return queryset


class AirplaneViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Airplane.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        elif self.action == "retrieve":
            return AirplaneRetrieveSerializer
        return AirplaneSerializer


class FlightViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Flight.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        elif self.action == "retrieve":
            return FlightRetrieveSerializer
        return FlightSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "list":
            queryset = queryset.prefetch_related("crew")
        elif self.action == "retrieve":
            queryset = queryset.select_related(
                "airplane__airplane_type",
                "route__source",
                "route__destination",
            ).prefetch_related("crew")
        return queryset


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


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

        if self.action == "retrieve":
            queryset = queryset.select_related(
                "order",
                "flight__airplane__airplane_type",
                "flight__route__source",
                "flight__route__destination",
            ).prefetch_related("flight__crew")
        return queryset
