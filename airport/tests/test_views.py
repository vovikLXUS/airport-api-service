from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

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
from rest_framework.exceptions import ParseError

from airport.views import params_to_ints

AIRPORT_URL = reverse("airport:airport-list")
ROUTE_URL = reverse("airport:route-list")
CREW_URL = reverse("airport:crew-list")
AIRPLANE_TYPE_URL = reverse("airport:airplanetype-list")
AIRPLANE_URL = reverse("airport:airplane-list")
FLIGHT_URL = reverse("airport:flight-list")
ORDER_URL = reverse("airport:order-list")
TICKET_URL = reverse("airport:ticket-list")


def results(response) -> list:
    """Responses are paginated (LimitOffsetPagination)."""
    return response.data["results"]


def names(response, field: str = "name") -> list:
    return [item[field] for item in results(response)]


def ids(response) -> list:
    return [item["id"] for item in results(response)]


class ParamsToIntsTests(TestCase):
    """Helper that parses parameters like ?routes=1,2,3."""

    def test_converts_comma_separated_string(self):
        self.assertEqual(params_to_ints("1,2,3"), [1, 2, 3])

    def test_single_value(self):
        self.assertEqual(params_to_ints("7"), [7])

    def test_non_numeric_value_is_rejected(self):
        with self.assertRaises(ParseError):
            params_to_ints("1,abc,3")

    def test_empty_string_is_rejected(self):
        with self.assertRaises(ParseError):
            params_to_ints("")


class UnauthenticatedApiTests(TestCase):
    """Every airport-service endpoint is closed without a token."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_is_required(self):
        for url in (
            AIRPORT_URL,
            ROUTE_URL,
            CREW_URL,
            AIRPLANE_TYPE_URL,
            AIRPLANE_URL,
            FLIGHT_URL,
            ORDER_URL,
            TICKET_URL,
        ):
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code, status.HTTP_401_UNAUTHORIZED
                )


class PermissionApiTests(TestCase):
    """A regular user can read, an admin can write."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "Pass12345"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com", "Pass12345"
        )
        self.client = APIClient()

    def test_user_can_list(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(AIRPORT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_create(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            AIRPORT_URL, {"name": "Changi", "closest_big_city": "Singapore"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            AIRPORT_URL, {"name": "Changi", "closest_big_city": "Singapore"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_update(self):
        airport = Airport.objects.create(name="Changi", closest_big_city="SG")
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("airport:airport-detail", args=[airport.id]),
            {"name": "Renamed"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AirportFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user("a@test.com", "Pass12345")
        )
        Airport.objects.create(name="Boryspil", closest_big_city="Kyiv")
        Airport.objects.create(name="Zhuliany", closest_big_city="Kyiv")
        Airport.objects.create(name="Changi", closest_big_city="Singapore")

    def test_no_filters_returns_all(self):
        response = self.client.get(AIRPORT_URL, {"limit": 100})

        self.assertEqual(response.data["count"], 3)

    def test_filter_by_city(self):
        response = self.client.get(AIRPORT_URL, {"city": "kyiv", "limit": 100})

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_city_is_case_insensitive(self):
        response = self.client.get(AIRPORT_URL, {"city": "KYIV"})

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_name_partial_match(self):
        response = self.client.get(AIRPORT_URL, {"name": "chan"})

        self.assertEqual(names(response), ["Changi"])

    def test_filters_combine(self):
        response = self.client.get(
            AIRPORT_URL, {"city": "kyiv", "name": "bory"}
        )

        self.assertEqual(names(response), ["Boryspil"])

    def test_filter_with_no_match_returns_empty(self):
        response = self.client.get(AIRPORT_URL, {"city": "atlantis"})

        self.assertEqual(response.data["count"], 0)


class RouteFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user("r@test.com", "Pass12345")
        )
        self.kyiv = Airport.objects.create(
            name="Boryspil", closest_big_city="Kyiv"
        )
        self.lviv = Airport.objects.create(name="Lviv", closest_big_city="Lviv")
        self.fra = Airport.objects.create(
            name="Frankfurt", closest_big_city="Frankfurt"
        )
        self.short = Route.objects.create(
            source=self.lviv, destination=self.fra, distance=1040
        )
        self.long = Route.objects.create(
            source=self.kyiv, destination=self.fra, distance=5000
        )

    def test_filter_by_source(self):
        response = self.client.get(ROUTE_URL, {"source": self.lviv.id})

        self.assertEqual(ids(response), [self.short.id])

    def test_filter_by_several_sources(self):
        response = self.client.get(
            ROUTE_URL, {"source": f"{self.lviv.id},{self.kyiv.id}"}
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_destination(self):
        response = self.client.get(ROUTE_URL, {"destination": self.fra.id})

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_from_city(self):
        response = self.client.get(ROUTE_URL, {"from_city": "lviv"})

        self.assertEqual(ids(response), [self.short.id])

    def test_filter_by_to_city(self):
        response = self.client.get(ROUTE_URL, {"to_city": "frankfurt"})

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_min_distance(self):
        response = self.client.get(ROUTE_URL, {"min_distance": 2000})

        self.assertEqual(ids(response), [self.long.id])

    def test_filter_by_max_distance(self):
        response = self.client.get(ROUTE_URL, {"max_distance": 2000})

        self.assertEqual(ids(response), [self.short.id])

    def test_distance_range(self):
        response = self.client.get(
            ROUTE_URL, {"min_distance": 1000, "max_distance": 2000}
        )

        self.assertEqual(ids(response), [self.short.id])

    def test_list_returns_airport_ids_retrieve_returns_objects(self):
        list_response = self.client.get(ROUTE_URL)
        detail_response = self.client.get(
            reverse("airport:route-detail", args=[self.short.id])
        )

        self.assertIsInstance(results(list_response)[0]["source"], int)
        self.assertEqual(detail_response.data["source"]["name"], "Lviv")


class CrewFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user("c@test.com", "Pass12345")
        )
        Crew.objects.create(first_name="Oleksandr", last_name="Kovalenko")
        Crew.objects.create(first_name="Kovtun", last_name="Melnyk")
        Crew.objects.create(first_name="Marie", last_name="Laurent")

    def test_filter_matches_last_name(self):
        response = self.client.get(CREW_URL, {"name": "kovalenko"})

        self.assertEqual(response.data["count"], 1)

    def test_filter_matches_first_name(self):
        response = self.client.get(CREW_URL, {"name": "marie"})

        self.assertEqual(response.data["count"], 1)

    def test_filter_matches_both_fields(self):
        response = self.client.get(CREW_URL, {"name": "kov"})

        self.assertEqual(response.data["count"], 2)

    def test_list_returns_last_name_only(self):
        response = self.client.get(CREW_URL, {"name": "marie"})

        self.assertEqual(set(results(response)[0].keys()), {"id", "last_name"})

    def test_retrieve_returns_full_name(self):
        crew = Crew.objects.get(last_name="Laurent")

        response = self.client.get(
            reverse("airport:crew-detail", args=[crew.id])
        )

        self.assertEqual(response.data["full_name"], "Marie Laurent")


class AirplaneTypeFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user("t@test.com", "Pass12345")
        )
        AirplaneType.objects.create(name="Narrow-body")
        AirplaneType.objects.create(name="Wide-body")
        AirplaneType.objects.create(name="Regional")

    def test_filter_by_name(self):
        response = self.client.get(AIRPLANE_TYPE_URL, {"name": "body"})

        self.assertEqual(response.data["count"], 2)

    def test_filter_is_case_insensitive(self):
        response = self.client.get(AIRPLANE_TYPE_URL, {"name": "REGIONAL"})

        self.assertEqual(names(response), ["Regional"])


class AirplaneFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user("p@test.com", "Pass12345")
        )
        self.narrow = AirplaneType.objects.create(name="Narrow-body")
        self.wide = AirplaneType.objects.create(name="Wide-body")
        self.small = Airplane.objects.create(
            name="Embraer E175",
            rows=20,
            seats_in_row=4,
            airplane_type=self.narrow,
        )  # 80 seats
        self.big = Airplane.objects.create(
            name="Boeing 777-300ER",
            rows=44,
            seats_in_row=10,
            airplane_type=self.wide,
        )  # 440 seats

    def test_filter_by_name(self):
        response = self.client.get(AIRPLANE_URL, {"name": "boeing"})

        self.assertEqual(ids(response), [self.big.id])

    def test_filter_by_airplane_type(self):
        response = self.client.get(
            AIRPLANE_URL, {"airplane_type": self.narrow.id}
        )

        self.assertEqual(ids(response), [self.small.id])

    def test_filter_by_several_types(self):
        response = self.client.get(
            AIRPLANE_URL, {"airplane_type": f"{self.narrow.id},{self.wide.id}"}
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_min_seats(self):
        response = self.client.get(AIRPLANE_URL, {"min_seats": 100})

        self.assertEqual(ids(response), [self.big.id])

    def test_filter_by_max_seats(self):
        response = self.client.get(AIRPLANE_URL, {"max_seats": 100})

        self.assertEqual(ids(response), [self.small.id])

    def test_seats_range(self):
        response = self.client.get(
            AIRPLANE_URL, {"min_seats": 50, "max_seats": 100}
        )

        self.assertEqual(ids(response), [self.small.id])

    def test_list_shows_calculated_seats(self):
        response = self.client.get(AIRPLANE_URL, {"name": "embraer"})

        self.assertEqual(results(response)[0]["seats"], 80)

    def test_retrieve_nests_airplane_type(self):
        response = self.client.get(
            reverse("airport:airplane-detail", args=[self.small.id])
        )

        self.assertEqual(response.data["airplane_type"]["name"], "Narrow-body")


class FlightViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "f@test.com", "Pass12345"
        )
        self.client.force_authenticate(self.user)

        self.kyiv = Airport.objects.create(
            name="Boryspil", closest_big_city="Kyiv"
        )
        self.lviv = Airport.objects.create(name="Lviv", closest_big_city="Lviv")
        self.fra = Airport.objects.create(
            name="Frankfurt", closest_big_city="Frankfurt"
        )

        self.route_lviv_fra = Route.objects.create(
            source=self.lviv, destination=self.fra, distance=1040
        )
        self.route_kyiv_fra = Route.objects.create(
            source=self.kyiv, destination=self.fra, distance=1500
        )

        self.narrow = AirplaneType.objects.create(name="Narrow-body")
        self.wide = AirplaneType.objects.create(name="Wide-body")
        self.tiny = Airplane.objects.create(
            name="Cessna", rows=2, seats_in_row=2, airplane_type=self.narrow
        )  # 4 seats
        self.jumbo = Airplane.objects.create(
            name="Airbus A380", rows=10, seats_in_row=10, airplane_type=self.wide
        )  # 100 seats

        self.crew_member = Crew.objects.create(
            first_name="Olga", last_name="Shevchenko"
        )

        base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.early = Flight.objects.create(
            route=self.route_lviv_fra,
            airplane=self.tiny,
            departure_time=base + timedelta(days=1),
            arrival_time=base + timedelta(days=1, hours=3),
        )
        self.late = Flight.objects.create(
            route=self.route_kyiv_fra,
            airplane=self.jumbo,
            departure_time=base + timedelta(days=5),
            arrival_time=base + timedelta(days=5, hours=3),
        )
        self.early.crew.add(self.crew_member)

    def test_filter_by_routes(self):
        response = self.client.get(
            FLIGHT_URL, {"routes": self.route_lviv_fra.id}
        )

        self.assertEqual(ids(response), [self.early.id])

    def test_filter_by_several_routes(self):
        response = self.client.get(
            FLIGHT_URL,
            {"routes": f"{self.route_lviv_fra.id},{self.route_kyiv_fra.id}"},
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_exact_date(self):
        date = self.early.departure_time.date().isoformat()

        response = self.client.get(FLIGHT_URL, {"date": date})

        self.assertEqual(ids(response), [self.early.id])

    def test_filter_by_date_from(self):
        date = self.late.departure_time.date().isoformat()

        response = self.client.get(FLIGHT_URL, {"date_from": date})

        self.assertEqual(ids(response), [self.late.id])

    def test_filter_by_date_to(self):
        date = self.early.departure_time.date().isoformat()

        response = self.client.get(FLIGHT_URL, {"date_to": date})

        self.assertEqual(ids(response), [self.early.id])

    def test_filter_by_date_range(self):
        response = self.client.get(
            FLIGHT_URL,
            {
                "date_from": self.early.departure_time.date().isoformat(),
                "date_to": self.late.departure_time.date().isoformat(),
            },
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_from_city(self):
        response = self.client.get(FLIGHT_URL, {"from_city": "lviv"})

        self.assertEqual(ids(response), [self.early.id])

    def test_filter_by_to_city(self):
        response = self.client.get(FLIGHT_URL, {"to_city": "frankfurt"})

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_airplane_type(self):
        response = self.client.get(
            FLIGHT_URL, {"airplane_type": self.wide.id}
        )

        self.assertEqual(ids(response), [self.late.id])

    def test_filter_by_crew(self):
        response = self.client.get(FLIGHT_URL, {"crew": self.crew_member.id})

        self.assertEqual(ids(response), [self.early.id])

    def test_filter_by_crew_does_not_duplicate_flights(self):
        second = Crew.objects.create(first_name="Ivan", last_name="Petrenko")
        self.early.crew.add(second)

        response = self.client.get(
            FLIGHT_URL, {"crew": f"{self.crew_member.id},{second.id}"}
        )

        self.assertEqual(response.data["count"], 1)

    def test_filters_combine(self):
        response = self.client.get(
            FLIGHT_URL,
            {
                "from_city": "kyiv",
                "date_from": self.late.departure_time.date().isoformat(),
            },
        )

        self.assertEqual(ids(response), [self.late.id])

    def test_tickets_available_without_tickets(self):
        response = self.client.get(FLIGHT_URL, {"routes": self.early.route_id})

        self.assertEqual(results(response)[0]["tickets_available"], 4)

    def test_tickets_available_decreases_with_sold_tickets(self):
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(row=1, seat=1, flight=self.early, order=order)
        Ticket.objects.create(row=1, seat=2, flight=self.early, order=order)

        response = self.client.get(FLIGHT_URL, {"routes": self.early.route_id})

        self.assertEqual(results(response)[0]["tickets_available"], 2)

    def test_tickets_available_is_not_affected_by_crew_filter(self):
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(row=1, seat=1, flight=self.early, order=order)
        second = Crew.objects.create(first_name="Ivan", last_name="Petrenko")
        self.early.crew.add(second)

        response = self.client.get(
            FLIGHT_URL, {"crew": f"{self.crew_member.id},{second.id}"}
        )

        self.assertEqual(results(response)[0]["tickets_available"], 3)

    def test_available_filter_hides_full_flights(self):
        order = Order.objects.create(user=self.user)
        for row in (1, 2):
            for seat in (1, 2):
                Ticket.objects.create(
                    row=row, seat=seat, flight=self.early, order=order
                )

        response = self.client.get(FLIGHT_URL, {"available": "true"})

        self.assertEqual(ids(response), [self.late.id])

    def test_available_false_does_not_filter(self):
        response = self.client.get(FLIGHT_URL, {"available": "false"})

        self.assertEqual(response.data["count"], 2)

    def test_list_returns_related_ids(self):
        response = self.client.get(FLIGHT_URL, {"routes": self.early.route_id})

        self.assertIsInstance(results(response)[0]["route"], int)

    def test_retrieve_returns_nested_objects(self):
        response = self.client.get(
            reverse("airport:flight-detail", args=[self.early.id])
        )

        self.assertEqual(response.data["route"]["source"]["name"], "Lviv")
        self.assertEqual(response.data["airplane"]["name"], "Cessna")
        self.assertEqual(
            response.data["crew"][0]["full_name"], "Olga Shevchenko"
        )
        self.assertEqual(response.data["tickets_available"], 4)

    def test_default_ordering_is_by_departure_time(self):
        response = self.client.get(FLIGHT_URL)

        self.assertEqual(ids(response), [self.early.id, self.late.id])


class OrderViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "owner@test.com", "Pass12345"
        )
        self.other = get_user_model().objects.create_user(
            "other@test.com", "Pass12345"
        )
        self.client.force_authenticate(self.user)

        self.own_order = Order.objects.create(user=self.user)
        self.foreign_order = Order.objects.create(user=self.other)

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

    def payload(self, *seats):
        return {
            "tickets": [
                {"row": row, "seat": seat, "flight": self.flight.id}
                for row, seat in seats
            ]
        }

    def test_list_returns_only_own_orders(self):
        response = self.client.get(ORDER_URL)

        self.assertEqual(ids(response), [self.own_order.id])

    def test_foreign_order_is_not_retrievable(self):
        response = self.client.get(
            reverse("airport:order-detail", args=[self.foreign_order.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_order_with_tickets(self):
        response = self.client.post(
            ORDER_URL, self.payload((1, 1), (1, 2)), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["tickets"]), 2)

    def test_create_assigns_current_user(self):
        response = self.client.post(
            ORDER_URL, self.payload((2, 1)), format="json"
        )

        self.assertEqual(
            Order.objects.get(id=response.data["id"]).user, self.user
        )

    def test_order_without_tickets_is_rejected(self):
        response = self.client.post(
            ORDER_URL, {"tickets": []}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seat_out_of_range_is_rejected(self):
        response = self.client.post(
            ORDER_URL, self.payload((99, 1)), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nothing_is_saved_when_one_ticket_is_invalid(self):
        orders_before = Order.objects.count()

        self.client.post(
            ORDER_URL, self.payload((1, 1), (99, 1)), format="json"
        )

        self.assertEqual(Order.objects.count(), orders_before)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_taken_seat_is_rejected_and_nothing_is_saved(self):
        self.client.post(ORDER_URL, self.payload((3, 3)), format="json")
        orders_before = Order.objects.count()
        tickets_before = Ticket.objects.count()

        response = self.client.post(
            ORDER_URL, self.payload((4, 4), (3, 3)), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), orders_before)
        self.assertEqual(Ticket.objects.count(), tickets_before)

    def test_orders_cannot_be_updated(self):
        response = self.client.patch(
            reverse("airport:order-detail", args=[self.own_order.id]),
            {"user": self.other.id},
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_list_includes_tickets(self):
        self.client.post(ORDER_URL, self.payload((5, 5)), format="json")

        response = self.client.get(ORDER_URL)

        self.assertIn("tickets", results(response)[0])

    def test_filter_by_date_from(self):
        old = Order.objects.create(user=self.user)
        Order.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        today = timezone.now().date().isoformat()

        response = self.client.get(ORDER_URL, {"date_from": today})

        self.assertNotIn(old.id, ids(response))

    def test_filter_by_date_to(self):
        past = (timezone.now() - timedelta(days=1)).date().isoformat()

        response = self.client.get(ORDER_URL, {"date_to": past})

        self.assertEqual(response.data["count"], 0)

    def test_invalid_date_returns_400(self):
        response = self.client.get(ORDER_URL, {"date_from": "garbage"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TicketViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "tk@test.com", "Pass12345"
        )
        self.other = get_user_model().objects.create_user(
            "tk-other@test.com", "Pass12345"
        )
        self.client.force_authenticate(self.user)

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
        self.first_flight = Flight.objects.create(
            route=route,
            airplane=airplane,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=3),
        )
        self.second_flight = Flight.objects.create(
            route=route,
            airplane=airplane,
            departure_time=departure + timedelta(days=1),
            arrival_time=departure + timedelta(days=1, hours=3),
        )
        self.first_order = Order.objects.create(user=self.user)
        self.second_order = Order.objects.create(user=self.user)
        self.foreign_order = Order.objects.create(user=self.other)

        self.first_ticket = Ticket.objects.create(
            row=1, seat=1, flight=self.first_flight, order=self.first_order
        )
        self.second_ticket = Ticket.objects.create(
            row=2, seat=2, flight=self.second_flight, order=self.second_order
        )
        self.foreign_ticket = Ticket.objects.create(
            row=3, seat=3, flight=self.first_flight, order=self.foreign_order
        )

    def test_foreign_tickets_are_hidden(self):
        response = self.client.get(TICKET_URL, {"limit": 100})

        self.assertNotIn(self.foreign_ticket.id, ids(response))
        self.assertEqual(response.data["count"], 2)

    def test_foreign_ticket_is_not_retrievable(self):
        response = self.client.get(
            reverse("airport:ticket-detail", args=[self.foreign_ticket.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tickets_are_read_only(self):
        response = self.client.post(
            TICKET_URL,
            {"row": 5, "seat": 5, "flight": self.first_flight.id},
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_tickets_cannot_be_updated(self):
        response = self.client.patch(
            reverse("airport:ticket-detail", args=[self.first_ticket.id]),
            {"seat": 6},
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_filter_by_flight(self):
        response = self.client.get(
            TICKET_URL, {"flight": self.first_flight.id}
        )

        self.assertEqual(ids(response), [self.first_ticket.id])

    def test_filter_by_several_flights(self):
        response = self.client.get(
            TICKET_URL,
            {"flight": f"{self.first_flight.id},{self.second_flight.id}"},
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_order(self):
        response = self.client.get(TICKET_URL, {"order": self.second_order.id})

        self.assertEqual(ids(response), [self.second_ticket.id])

    def test_non_numeric_filter_returns_400(self):
        response = self.client.get(TICKET_URL, {"flight": "abc"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_ids(self):
        response = self.client.get(
            TICKET_URL, {"flight": self.first_flight.id}
        )

        self.assertIsInstance(results(response)[0]["flight"], int)

    def test_retrieve_returns_nested_flight_and_order(self):
        response = self.client.get(
            reverse("airport:ticket-detail", args=[self.first_ticket.id])
        )

        self.assertEqual(response.data["flight"]["id"], self.first_flight.id)
        self.assertEqual(response.data["order"]["id"], self.first_order.id)
