from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

CREATE_USER_URL = reverse("user:create")
ME_URL = reverse("user:manage_user")
TOKEN_URL = reverse("user:token_obtain_pair")
TOKEN_REFRESH_URL = reverse("user:token_refresh")
TOKEN_VERIFY_URL = reverse("user:token_verify")


class CreateUserViewTests(TestCase):
    """Реєстрація відкрита для всіх (permission_classes = ())."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_register_without_token(self):
        response = self.client.post(
            CREATE_USER_URL,
            {"email": "new@example.com", "password": "Pass12345"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_is_actually_created(self):
        self.client.post(
            CREATE_USER_URL,
            {"email": "created@example.com", "password": "Pass12345"},
        )

        self.assertTrue(
            get_user_model().objects.filter(email="created@example.com").exists()
        )

    def test_password_is_not_returned(self):
        response = self.client.post(
            CREATE_USER_URL,
            {"email": "secret@example.com", "password": "Pass12345"},
        )

        self.assertNotIn("password", response.data)

    def test_duplicate_email_is_rejected(self):
        get_user_model().objects.create_user("dup@example.com", "Pass12345")

        response = self.client.post(
            CREATE_USER_URL,
            {"email": "dup@example.com", "password": "Pass12345"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_password_is_rejected(self):
        response = self.client.post(
            CREATE_USER_URL,
            {"email": "short@example.com", "password": "123"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            get_user_model().objects.filter(email="short@example.com").exists()
        )


class ManageUserViewTests(TestCase):
    """/me/ повертає профіль власника токена."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            "me@example.com", "Pass12345"
        )
        self.client = APIClient()

    def test_auth_is_required(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_own_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")

    def test_post_is_not_allowed(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(ME_URL, {})

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_can_update_own_password(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(ME_URL, {"password": "NewPass123"})
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.check_password("NewPass123"))

    def test_can_update_own_email(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(ME_URL, {"email": "renamed@example.com"})
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.email, "renamed@example.com")

    def test_cannot_grant_itself_staff(self):
        self.client.force_authenticate(self.user)

        self.client.patch(ME_URL, {"is_staff": True})
        self.user.refresh_from_db()

        self.assertFalse(self.user.is_staff)


class JWTAuthTests(TestCase):
    """Логін за email замість username."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        get_user_model().objects.create_user("jwt@example.com", "Pass12345")

    def test_obtain_token_with_email(self):
        response = self.client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "Pass12345"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_token_with_wrong_password(self):
        response = self.client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "WrongPass"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        tokens = self.client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "Pass12345"}
        ).data

        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": tokens["refresh"]}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_verify_token(self):
        tokens = self.client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "Pass12345"}
        ).data

        response = self.client.post(
            TOKEN_VERIFY_URL, {"token": tokens["access"]}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_rejects_garbage_token(self):
        response = self.client.post(TOKEN_VERIFY_URL, {"token": "not-a-token"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_works_on_protected_endpoint(self):
        tokens = self.client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "Pass12345"}
        ).data

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        )
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "jwt@example.com")
