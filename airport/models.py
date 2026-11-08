import pathlib
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


def image_path(instance, filename: str) -> str:
    """
    Build an upload path: upload/<model_name>/<slug>-<uuid><extension>

    Returns a string with forward slashes: Django stores this value in the
    database and serves it as part of a URL, so the separator must not
    depend on the operating system.
    """
    extension = pathlib.Path(filename).suffix
    slug = slugify(instance.name, allow_unicode=True) or instance._meta.model_name
    filename = f"{slug}-{uuid.uuid4()}{extension}"

    return f"upload/{instance._meta.model_name}/{filename}"


class Airport(models.Model):
    name = models.CharField(max_length=200)
    closest_big_city = models.CharField(max_length=200)
    image = models.ImageField(null=True, upload_to=image_path)

    class Meta:
        verbose_name_plural = "airports"

    def __str__(self):
        return f"{self.name} (in/near: {self.closest_big_city})"


class Route(models.Model):
    source = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes_from",
        null=False,
        blank=False
    )
    destination = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes_to",
        null=False,
        blank=False
    )
    distance = models.PositiveIntegerField()

    class Meta:
        verbose_name_plural = "routes"

    def __str__(self):
        return (
            f"Route #{self.id}: {self.source} -> "
            f"{self.destination} (distance={self.distance})"
        )


class Crew(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class AirplaneType(models.Model):
    name = models.CharField(
        max_length=200,
        null=False,
        blank=False
    )

    def __str__(self):
        return f"{self.name}"


class Airplane(models.Model):
    name = models.CharField(max_length=200)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(
        AirplaneType,
        on_delete=models.CASCADE,
        related_name="airplanes"
    )
    image = models.ImageField(null=True, upload_to=image_path)

    class Meta:
        verbose_name_plural = "airplanes"

    @property
    def seats(self):
        return self.rows * self.seats_in_row

    def __str__(self):
        return (
            f"Airplane {self.name}({self.rows}) "
            f"(rows:{self.rows}; seats per row:{self.seats_in_row})"
        )


class Flight(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="flights",
        null=False,
        blank=False
    )
    airplane = models.ForeignKey(
        "Airplane",
        on_delete=models.CASCADE,
        related_name="flights",
        null=False
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew)

    class Meta:
        verbose_name_plural = "flights"

    def __str__(self):
        return f"Flight #{self.id}(route - {self.route}; airplane - {self.airplane})"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        null=False,
    )

    class Meta:
        verbose_name_plural = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id}({self.user})"


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["flight", "row", "seat"],
                name="unique_ticket_seat_per_flight",
            )
        ]
        ordering = ["id"]

    @staticmethod
    def validate_seat(row: int, seat: int, airplane, error_to_raise):
        """Check that the row and the seat exist in the given airplane."""
        for value, attr_name, limit in (
            (row, "row", airplane.rows),
            (seat, "seat", airplane.seats_in_row),
        ):
            if not 1 <= value <= limit:
                raise error_to_raise(
                    {
                        attr_name: (
                            f"{attr_name} must be in range [1, {limit}], "
                            f"got {value}"
                        )
                    }
                )

    def clean(self):
        Ticket.validate_seat(
            self.row, self.seat, self.flight.airplane, ValidationError
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Ticket {self.id}(order {self.order.id}) - "
            f"(row/seat: {self.row}/{self.seat})"
        )
