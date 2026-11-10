from django.urls import path, include
from rest_framework import routers

from airport.views import (
    AirportViewSet,
    RouteViewSet,
    CrewViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    FlightViewSet,
    OrderViewSet,
    TicketViewSet,
)


router = routers.DefaultRouter()
router.register("airports", AirportViewSet)
router.register("routes", RouteViewSet)
router.register("crew", CrewViewSet)
router.register("airplane-types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("flights", FlightViewSet)
router.register("orders", OrderViewSet)
router.register("tickets", TicketViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "airport"
