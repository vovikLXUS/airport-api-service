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


class FlightListSerializer(FlightSerializer):
    # the value comes from annotate() in FlightViewSet.get_queryset
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


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "created_at", "user"]


class TicketSerializer(serializers.ModelSerializer):
    flight = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.select_related(
            "route__source",
            "route__destination",
            "airplane",
        )
    )
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.select_related("user")
    )

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight", "order"]

    def validate(self, attrs):
        data = super().validate(attrs)
        Ticket.validate_seat(
            attrs["row"],
            attrs["seat"],
            attrs["flight"].airplane,
            serializers.ValidationError,
        )
        return data


class TicketListSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight", "order"]


class TicketRetrieveSerializer(TicketSerializer):
    flight = FlightRetrieveSerializer(read_only=True)
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight", "order"]
