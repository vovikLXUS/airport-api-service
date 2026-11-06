from django.conf import settings
from django.db import models


class Airport(models.Model):
    name = models.CharField(max_length=200)
    closest_big_city = models.CharField(max_length=200)


class Route(models.Model):
    source = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes-from",
        null=False,
        blank=False
    )
    destination = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes-to",
        null=False,
        blank=False
    )
    distance = models.IntegerField()

    class Meta:
        verbose_name_plural = "routes"

    def __str__(self):
        return (
            f"Route #{self.id}: {self.destination} -> "
            f"{self.source} (distance={self.distance})"
        )


class Crew(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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

    class Meta:
        verbose_name_plural = "airplanes"

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


class Ticket(models.Model):
    row = models.IntegerField(unique=True)
    seat = models.IntegerField(unique=True)
    flight = models.ForeignKey(
        Flight,
        on_delete=models.CASCADE,
        related_name="tickets",
        null=False,
        blank=False
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tickets",
        null=False,
        blank=False
    )

    class Meta:
        verbose_name_plural = "tickets"
        constraints = [
            models.UniqueConstraint(fields=[
                "row", "seat", "flight", "order"
            ],
                name="unique_ticket_seat_trip")
        ]
        ordering = ["seat"]

    def __str__(self):
        return (
            f"Ticket {self.id}(order {'order'.id}) - "
            f"(row/seat: {self.row}/{self.seat})"
        )
