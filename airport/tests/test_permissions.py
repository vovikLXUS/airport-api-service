from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from airport.permissions import IsAdminAllOrIsAuthenticatedReadOnly


class IsAdminAllOrIsAuthenticatedReadOnlyTests(TestCase):
    """
    Custom permission class: an admin has full access,
    an authenticated user can only read, anonymous clients get nothing.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsAdminAllOrIsAuthenticatedReadOnly()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "Pass12345"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com", "Pass12345"
        )

    def has_permission(self, method: str, user) -> bool:
        request = getattr(self.factory, method.lower())("/")
        request.user = user
        return self.permission.has_permission(request, view=None)

    def test_anonymous_cannot_read(self):
        self.assertFalse(self.has_permission("get", AnonymousUser()))

    def test_anonymous_cannot_write(self):
        self.assertFalse(self.has_permission("post", AnonymousUser()))

    def test_authenticated_user_can_read(self):
        for method in ("get", "head", "options"):
            with self.subTest(method=method):
                self.assertTrue(self.has_permission(method, self.user))

    def test_authenticated_user_cannot_write(self):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertFalse(self.has_permission(method, self.user))

    def test_admin_can_read(self):
        self.assertTrue(self.has_permission("get", self.admin))

    def test_admin_can_write(self):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertTrue(self.has_permission(method, self.admin))

    def test_staff_without_superuser_can_write(self):
        staff = get_user_model().objects.create_user(
            "staff@test.com", "Pass12345", is_staff=True
        )

        self.assertTrue(self.has_permission("post", staff))
