from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.utils import timezone

from airport.models import (
    Airplane,
    AirplaneType,
    Airport,
    Crew,
    Flight,
    Order,
    Route,
    Ticket,
)
from airport.serializers import (
    AirplaneListSerializer,
    AirplaneRetrieveSerializer,
    AirplaneSerializer,
    CrewListSerializer,
    CrewRetrieveSerializer,
    FlightListSerializer,
    FlightRetrieveSerializer,
    RouteListSerializer,
    RouteRetrieveSerializer,
    TicketRetrieveSerializer,
)


class AirplaneSerializersTests(TestCase):
    """Computed seats field and the nested airplane_type."""

    def setUp(self):
        self.airplane_type = AirplaneType.objects.create(name="Narrow-body")
        self.airplane = Airplane.objects.create(
            name="Boeing 737-800",
            rows=10,
            seats_in_row=6,
            airplane_type=self.airplane_type,
        )

    def test_seats_is_calculated(self):
        data = AirplaneSerializer(self.airplane).data

        self.assertEqual(data["seats"], 60)

    def test_list_serializer_hides_rows_and_type(self):
        data = AirplaneListSerializer(self.airplane).data

        self.assertEqual(set(data.keys()), {"id", "name", "seats", "image"})

    def test_retrieve_serializer_nests_airplane_type(self):
        data = AirplaneRetrieveSerializer(self.airplane).data

        self.assertEqual(
            data["airplane_type"],
            {"id": self.airplane_type.id, "name": "Narrow-body"},
        )
        self.assertEqual(data["rows"], 10)
        self.assertEqual(data["seats_in_row"], 6)


class CrewSerializersTests(TestCase):
    def setUp(self):
        self.crew = Crew.objects.create(
            first_name="Olga", last_name="Shevchenko"
        )

    def test_list_serializer_returns_last_name_only(self):
        data = CrewListSerializer(self.crew).data

        self.assertEqual(set(data.keys()), {"id", "last_name"})

    def test_retrieve_serializer_returns_full_name(self):
        data = CrewRetrieveSerializer(self.crew).data

        self.assertEqual(data["full_name"], "Olga Shevchenko")

    def test_full_name_is_read_only(self):
        serializer = CrewRetrieveSerializer(data={"full_name": "Hacked Name"})
        serializer.is_valid()

        self.assertNotIn("full_name", serializer.validated_data)


class RouteSerializersTests(TestCase):
    def setUp(self):
        self.source = Airport.objects.create(
            name="Lviv", closest_big_city="Lviv"
        )
        self.destination = Airport.objects.create(
            name="Frankfurt", closest_big_city="Frankfurt"
        )
        self.route = Route.objects.create(
            source=self.source, destination=self.destination, distance=1040
        )

    def test_list_serializer_returns_airport_ids(self):
        data = RouteListSerializer(self.route).data

        self.assertEqual(data["source"], self.source.id)
        self.assertEqual(data["destination"], self.destination.id)

    def test_retrieve_serializer_nests_airports(self):
        data = RouteRetrieveSerializer(self.route).data

        self.assertEqual(data["source"]["name"], "Lviv")
        self.assertEqual(data["destination"]["closest_big_city"], "Frankfurt")


class FlightSerializersTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "flight@test.com", "Pass12345"
        )
        airport_source = Airport.objects.create(
            name="Lviv", closest_big_city="Lviv"
        )
        airport_destination = Airport.objects.create(
            name="Frankfurt", closest_big_city="Frankfurt"
        )
        self.route = Route.objects.create(
            source=airport_source,
            destination=airport_destination,
            distance=1040,
        )
        self.airplane = Airplane.objects.create(
            name="Boeing 737-800",
            rows=2,
            seats_in_row=2,
            airplane_type=AirplaneType.objects.create(name="Narrow-body"),
        )
        departure = timezone.now()
        self.flight = Flight.objects.create(
            route=self.route,
            airplane=self.airplane,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=3),
        )
        self.crew = Crew.objects.create(first_name="Olga", last_name="Shevchenko")
        self.flight.crew.add(self.crew)

    @staticmethod
    def annotated(flight_id):
        return Flight.objects.annotate(
            tickets_available=(
                F("airplane__rows")
                * F("airplane__seats_in_row")
                - Count("tickets", distinct=True)
            )
        ).get(id=flight_id)

    def test_list_serializer_shows_tickets_available(self):
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(row=1, seat=1, flight=self.flight, order=order)

        data = FlightListSerializer(self.annotated(self.flight.id)).data

        self.assertEqual(data["tickets_available"], 3)

    def test_tickets_available_equals_capacity_when_no_tickets(self):
        data = FlightListSerializer(self.annotated(self.flight.id)).data

        self.assertEqual(data["tickets_available"], 4)

    def test_list_serializer_returns_related_ids(self):
        data = FlightListSerializer(self.annotated(self.flight.id)).data

        self.assertEqual(data["route"], self.route.id)
        self.assertEqual(data["airplane"], self.airplane.id)
        self.assertEqual(list(data["crew"]), [self.crew.id])

    def test_retrieve_serializer_nests_everything(self):
        data = FlightRetrieveSerializer(self.annotated(self.flight.id)).data

        self.assertEqual(data["route"]["source"]["name"], "Lviv")
        self.assertEqual(data["airplane"]["name"], "Boeing 737-800")
        self.assertEqual(data["crew"][0]["full_name"], "Olga Shevchenko")
        self.assertEqual(data["tickets_available"], 4)


class TicketSerializersTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "ticket@test.com", "Pass12345"
        )
        route = Route.objects.create(
            source=Airport.objects.create(name="Lviv", closest_big_city="Lviv"),
            destination=Airport.objects.create(
                name="Frankfurt", closest_big_city="Frankfurt"
            ),
            distance=1040,
        )
        airplane = Airplane.objects.create(
            name="Boeing 737-800",
            rows=10,
            seats_in_row=6,
            airplane_type=AirplaneType.objects.create(name="Narrow-body"),
        )
        departure = timezone.now()
        self.flight = Flight.objects.create(
            route=route,
            airplane=airplane,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=3),
        )
        self.order = Order.objects.create(user=self.user)
        self.ticket = Ticket.objects.create(
            row=3, seat=4, flight=self.flight, order=self.order
        )

    def test_retrieve_serializer_nests_flight_and_order(self):
        data = TicketRetrieveSerializer(self.ticket).data

        self.assertEqual(data["flight"]["id"], self.flight.id)
        self.assertEqual(data["flight"]["route"]["source"]["name"], "Lviv")
        self.assertEqual(data["order"]["id"], self.order.id)
