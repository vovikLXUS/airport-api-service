import pathlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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
    image_path,
)

UUID_RE = (
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def sample_airport(**params) -> Airport:
    defaults = {"name": "Boryspil", "closest_big_city": "Kyiv"}
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_route(**params) -> Route:
    defaults = {
        "source": sample_airport(name="Lviv", closest_big_city="Lviv"),
        "destination": sample_airport(
            name="Frankfurt", closest_big_city="Frankfurt"
        ),
        "distance": 1040,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)


def sample_airplane(**params) -> Airplane:
    defaults = {
        "name": "Boeing 737-800",
        "rows": 10,
        "seats_in_row": 6,
        "airplane_type": AirplaneType.objects.create(name="Narrow-body"),
    }
    defaults.update(params)
    return Airplane.objects.create(**defaults)


def sample_flight(**params) -> Flight:
    departure = timezone.now()
    defaults = {
        "route": sample_route(),
        "airplane": sample_airplane(),
        "departure_time": departure,
        "arrival_time": departure + timedelta(hours=3),
    }
    defaults.update(params)
    return Flight.objects.create(**defaults)


class ImagePathTests(TestCase):
    """image_path() is the custom upload path builder for ImageField."""

    def test_path_starts_with_upload_and_model_name(self):
        airplane = sample_airplane(name="Boeing 737-800")

        path = image_path(airplane, "photo.jpg")

        self.assertTrue(path.startswith("upload/airplane/"))

    def test_model_name_differs_per_model(self):
        airport = sample_airport(name="Changi")

        path = image_path(airport, "photo.jpg")

        self.assertTrue(path.startswith("upload/airport/"))

    def test_filename_is_not_duplicated(self):
        airplane = sample_airplane(name="Boeing 737-800")

        path = image_path(airplane, "photo.jpg")

        self.assertEqual(len(path.split("/")), 3)
        self.assertEqual(path.count(".jpg"), 1)

    def test_extension_is_preserved(self):
        airplane = sample_airplane()

        self.assertTrue(image_path(airplane, "photo.png").endswith(".png"))
        self.assertTrue(image_path(airplane, "photo.JPEG").endswith(".JPEG"))

    def test_filename_contains_slug_and_uuid(self):
        airplane = sample_airplane(name="Boeing 737-800")

        path = image_path(airplane, "photo.jpg")
        filename = path.split("/")[-1]

        self.assertRegex(filename, rf"^boeing-737-800-{UUID_RE}\.jpg$")

    def test_two_calls_give_different_names(self):
        airplane = sample_airplane()

        self.assertNotEqual(
            image_path(airplane, "photo.jpg"),
            image_path(airplane, "photo.jpg"),
        )

    def test_cyrillic_name_is_kept_in_slug(self):
        airport = sample_airport(name="Бориспіль", closest_big_city="Київ")

        filename = image_path(airport, "photo.jpg").split("/")[-1]

        self.assertTrue(filename.startswith("бориспіль-"))

    def test_name_without_sluggable_chars_falls_back_to_model_name(self):
        airport = sample_airport(name="!!! ???", closest_big_city="Kyiv")

        filename = image_path(airport, "photo.jpg").split("/")[-1]

        self.assertTrue(filename.startswith("airport-"))

    def test_path_uses_forward_slashes_only(self):
        airplane = sample_airplane()

        path = image_path(airplane, "photo.jpg")

        self.assertNotIn("\\", path)
        self.assertIsInstance(path, str)

    def test_path_is_relative(self):
        airplane = sample_airplane()

        self.assertFalse(pathlib.PurePosixPath(
            image_path(airplane, "photo.jpg")
        ).is_absolute())


class AirplaneModelTests(TestCase):
    """seats is a computed property with no column in the database."""

    def test_seats_is_rows_multiplied_by_seats_in_row(self):
        airplane = sample_airplane(rows=10, seats_in_row=6)

        self.assertEqual(airplane.seats, 60)

    def test_seats_changes_with_rows(self):
        airplane = sample_airplane(rows=10, seats_in_row=6)
        airplane.rows = 20

        self.assertEqual(airplane.seats, 120)

    def test_str(self):
        airplane = sample_airplane(name="Boeing 737-800", rows=10, seats_in_row=6)

        self.assertIn("Boeing 737-800", str(airplane))
        self.assertIn("rows:10", str(airplane))
        self.assertIn("seats per row:6", str(airplane))


class CrewModelTests(TestCase):
    """full_name is a custom property used by the serializer."""

    def test_full_name(self):
        crew = Crew.objects.create(first_name="Olga", last_name="Shevchenko")

        self.assertEqual(crew.full_name, "Olga Shevchenko")

    def test_str_equals_full_name(self):
        crew = Crew.objects.create(first_name="Olga", last_name="Shevchenko")

        self.assertEqual(str(crew), crew.full_name)


class AirportModelTests(TestCase):
    def test_str_contains_name_and_city(self):
        airport = sample_airport(name="Boryspil", closest_big_city="Kyiv")

        self.assertEqual(str(airport), "Boryspil (in/near: Kyiv)")


class RouteModelTests(TestCase):
    def test_str_direction_is_source_to_destination(self):
        source = sample_airport(name="Lviv", closest_big_city="Lviv")
        destination = sample_airport(name="Frankfurt", closest_big_city="FRA")
        route = Route.objects.create(
            source=source, destination=destination, distance=1040
        )

        result = str(route)

        self.assertLess(result.index("Lviv"), result.index("Frankfurt"))
        self.assertIn("distance=1040", result)

    def test_related_names(self):
        route = sample_route()

        self.assertIn(route, route.source.routes_from.all())
        self.assertIn(route, route.destination.routes_to.all())


class FlightModelTests(TestCase):
    def test_str_contains_route_and_airplane(self):
        flight = sample_flight()

        result = str(flight)

        self.assertIn(f"Flight #{flight.id}", result)
        self.assertIn(str(flight.route), result)
        self.assertIn(str(flight.airplane), result)

    def test_crew_is_many_to_many(self):
        flight = sample_flight()
        first = Crew.objects.create(first_name="A", last_name="B")
        second = Crew.objects.create(first_name="C", last_name="D")

        flight.crew.set([first, second])

        self.assertEqual(flight.crew.count(), 2)
        self.assertIn(flight, first.flights.all())


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "order@test.com", "Pass12345"
        )

    def test_str_contains_user(self):
        order = Order.objects.create(user=self.user)

        self.assertIn(str(self.user), str(order))

    def test_created_at_is_set_automatically(self):
        order = Order.objects.create(user=self.user)

        self.assertIsNotNone(order.created_at)

    def test_ordering_is_newest_first(self):
        first = Order.objects.create(user=self.user)
        second = Order.objects.create(user=self.user)

        self.assertEqual(list(Order.objects.all()), [second, first])


class TicketModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "ticket@test.com", "Pass12345"
        )
        self.order = Order.objects.create(user=self.user)
        self.flight = sample_flight()

    def test_str_contains_order_row_and_seat(self):
        ticket = Ticket.objects.create(
            row=3, seat=4, flight=self.flight, order=self.order
        )

        result = str(ticket)

        self.assertIn(f"order {self.order.id}", result)
        self.assertIn("3/4", result)

    def test_same_seat_on_same_flight_is_forbidden(self):
        Ticket.objects.create(
            row=3, seat=4, flight=self.flight, order=self.order
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Ticket.objects.create(
                    row=3, seat=4, flight=self.flight, order=self.order
                )

    def test_row_above_airplane_rows_is_rejected(self):
        ticket = Ticket(
            row=99, seat=1, flight=self.flight, order=self.order
        )

        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_seat_above_seats_in_row_is_rejected(self):
        ticket = Ticket(
            row=1, seat=99, flight=self.flight, order=self.order
        )

        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_zero_and_negative_values_are_rejected(self):
        for row, seat in ((0, 1), (1, 0), (-1, 1)):
            with self.subTest(row=row, seat=seat):
                ticket = Ticket(
                    row=row, seat=seat, flight=self.flight, order=self.order
                )

                with self.assertRaises(ValidationError):
                    ticket.full_clean()

    def test_boundary_values_are_allowed(self):
        airplane = self.flight.airplane

        ticket = Ticket.objects.create(
            row=airplane.rows,
            seat=airplane.seats_in_row,
            flight=self.flight,
            order=self.order,
        )

        self.assertIsNotNone(ticket.id)

    def test_error_message_names_the_wrong_field(self):
        ticket = Ticket(
            row=99, seat=1, flight=self.flight, order=self.order
        )

        with self.assertRaises(ValidationError) as context:
            ticket.full_clean()

        self.assertIn("row", context.exception.message_dict)

    def test_same_seat_on_another_flight_is_allowed(self):
        other_flight = sample_flight()
        Ticket.objects.create(
            row=3, seat=4, flight=self.flight, order=self.order
        )

        ticket = Ticket.objects.create(
            row=3, seat=4, flight=other_flight, order=self.order
        )

        self.assertIsNotNone(ticket.id)

    def test_another_seat_on_same_flight_is_allowed(self):
        Ticket.objects.create(
            row=3, seat=4, flight=self.flight, order=self.order
        )

        ticket = Ticket.objects.create(
            row=3, seat=5, flight=self.flight, order=self.order
        )

        self.assertIsNotNone(ticket.id)

    def test_ordering_is_by_id(self):
        second = Ticket.objects.create(
            row=2, seat=1, flight=self.flight, order=self.order
        )
        first = Ticket.objects.create(
            row=1, seat=1, flight=self.flight, order=self.order
        )

        self.assertEqual(
            list(Ticket.objects.all()), sorted([second, first], key=lambda t: t.id)
        )

    def test_related_names(self):
        ticket = Ticket.objects.create(
            row=1, seat=1, flight=self.flight, order=self.order
        )

        self.assertIn(ticket, self.flight.tickets.all())
        self.assertIn(ticket, self.order.tickets.all())
