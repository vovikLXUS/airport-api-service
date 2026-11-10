from django.db import IntegrityError, transaction
from rest_framework import serializers

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


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ["id", "name"]


class AirplaneSerializer(serializers.ModelSerializer):
    seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Airplane
        fields = ["id", "name", "seats", "image"]


class AirplaneListSerializer(AirplaneSerializer):
    seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Airplane
        fields = ["id", "name", "seats", "image"]


class AirplaneRetrieveSerializer(AirplaneListSerializer):
    airplane_type = AirplaneTypeSerializer(read_only=True)

    class Meta:
        model = Airplane
        fields = ["id", "name", "seats", "rows", "seats_in_row", "airplane_type", "image"]


class AirplaneImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ["id", "image"]


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ["id", "name", "closest_big_city", "image"]


class AirportImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ["id", "image"]


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]

    def validate(self, attrs):
        data = super().validate(attrs)
        source = attrs.get("source", getattr(self.instance, "source", None))
        destination = attrs.get("destination", getattr(self.instance, "destination", None))

        if source and destination and source == destination:
            raise serializers.ValidationError(
                {"destination": "Destination must differ from source."}
            )
        return data


class RouteListSerializer(RouteSerializer):
    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]


class RouteRetrieveSerializer(RouteSerializer):
    source = AirportSerializer(read_only=True)
    destination = AirportSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ["id", "first_name", "last_name"]


class CrewListSerializer(CrewSerializer):
    class Meta:
        model = Crew
        fields = ["id", "last_name"]


class CrewRetrieveSerializer(CrewSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Crew
        fields = ["id", "full_name"]


class FlightSerializer(serializers.ModelSerializer):
    route = serializers.PrimaryKeyRelatedField(
        queryset=Route.objects.select_related("source", "destination")
    )

    class Meta:
        model = Flight
        fields = ["id", "route", "airplane", "departure_time", "arrival_time", "crew"]

    def validate(self, attrs):
        data = super().validate(attrs)
        instance = self.instance
        departure = attrs.get(
            "departure_time", getattr(instance, "departure_time", None)
        )
        arrival = attrs.get(
            "arrival_time", getattr(instance, "arrival_time", None)
        )

        if departure and arrival and arrival <= departure:
            raise serializers.ValidationError(
                {
                    "arrival_time":
                        "Arrival time must be later than departure time."
                }
            )
        return data


class FlightListSerializer(FlightSerializer):
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = [
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "crew",
            "tickets_available",
        ]


class FlightRetrieveSerializer(FlightSerializer):
    airplane = AirplaneRetrieveSerializer(read_only=True)
    crew = CrewRetrieveSerializer(many=True, read_only=True)
    route = RouteRetrieveSerializer(read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = [
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "crew",
            "tickets_available",
        ]



class TicketSerializer(serializers.ModelSerializer):
    """Write serializer used inside an order; the order itself is implicit."""

    flight = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.select_related(
            "route__source",
            "route__destination",
            "airplane",
        )
    )

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight"]

    def validate(self, attrs):
        data = super().validate(attrs)
        instance = self.instance
        row = attrs.get("row", getattr(instance, "row", None))
        seat = attrs.get("seat", getattr(instance, "seat", None))
        flight = attrs.get("flight", getattr(instance, "flight", None))

        Ticket.validate_seat(
            row, seat, flight.airplane, serializers.ValidationError
        )
        return data


class TicketListSerializer(TicketSerializer):
    flight = serializers.PrimaryKeyRelatedField(read_only=True)
    order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight", "order"]


class OrderShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "created_at"]


class TicketRetrieveSerializer(TicketSerializer):
    flight = FlightRetrieveSerializer(read_only=True)
    order = OrderShortSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight", "order"]


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, allow_empty=False)

    class Meta:
        model = Order
        fields = ["id", "created_at", "tickets"]

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets")

        try:
            with transaction.atomic():
                order = Order.objects.create(**validated_data)
                for ticket_data in tickets_data:
                    Ticket.objects.create(order=order, **ticket_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"tickets": "One of the requested seats is already taken."}
            )

        return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
