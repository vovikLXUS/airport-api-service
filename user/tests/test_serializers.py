from django.contrib.auth import get_user_model
from django.test import TestCase

from user.serializers import AuthTokenSerializer, UserSerializer


class UserSerializerTests(TestCase):
    """Кастомні create() та update() — хешування пароля."""

    def test_create_hashes_password(self):
        serializer = UserSerializer(
            data={"email": "new@example.com", "password": "Pass12345"}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        self.assertTrue(user.check_password("Pass12345"))
        self.assertNotEqual(user.password, "Pass12345")

    def test_password_is_write_only(self):
        user = get_user_model().objects.create_user(
            "wo@example.com", "Pass12345"
        )

        data = UserSerializer(user).data

        self.assertNotIn("password", data)

    def test_short_password_is_rejected(self):
        serializer = UserSerializer(
            data={"email": "short@example.com", "password": "1234"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_invalid_email_is_rejected(self):
        serializer = UserSerializer(
            data={"email": "not-an-email", "password": "Pass12345"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_is_staff_is_read_only(self):
        serializer = UserSerializer(
            data={
                "email": "staff@example.com",
                "password": "Pass12345",
                "is_staff": True,
            }
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        self.assertFalse(user.is_staff)

    def test_update_rehashes_password(self):
        user = get_user_model().objects.create_user(
            "upd@example.com", "OldPass123"
        )

        serializer = UserSerializer(
            user, data={"password": "NewPass123"}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertTrue(updated.check_password("NewPass123"))
        self.assertFalse(updated.check_password("OldPass123"))

    def test_update_without_password_keeps_old_one(self):
        user = get_user_model().objects.create_user(
            "keep@example.com", "OldPass123"
        )

        serializer = UserSerializer(
            user, data={"email": "renamed@example.com"}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertEqual(updated.email, "renamed@example.com")
        self.assertTrue(updated.check_password("OldPass123"))


class AuthTokenSerializerTests(TestCase):
    """Кастомний серіалайзер логіну за email."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "auth@example.com", "Pass12345"
        )

    def test_valid_credentials(self):
        serializer = AuthTokenSerializer(
            data={"email": "auth@example.com", "password": "Pass12345"}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["user"], self.user)

    def test_wrong_password_is_rejected(self):
        serializer = AuthTokenSerializer(
            data={"email": "auth@example.com", "password": "WrongPass"}
        )

        self.assertFalse(serializer.is_valid())

    def test_unknown_email_is_rejected(self):
        serializer = AuthTokenSerializer(
            data={"email": "ghost@example.com", "password": "Pass12345"}
        )

        self.assertFalse(serializer.is_valid())

    def test_missing_password_is_rejected(self):
        serializer = AuthTokenSerializer(data={"email": "auth@example.com"})

        self.assertFalse(serializer.is_valid())

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        self.user.save()

        serializer = AuthTokenSerializer(
            data={"email": "auth@example.com", "password": "Pass12345"}
        )

        self.assertFalse(serializer.is_valid())
