from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


class UserManagerTests(TestCase):
    """Кастомний менеджер: email замість username."""

    def setUp(self):
        self.model = get_user_model()

    def test_create_user_with_email(self):
        user = self.model.objects.create_user("test@example.com", "Pass12345")

        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("Pass12345"))

    def test_password_is_hashed(self):
        user = self.model.objects.create_user("hash@example.com", "Pass12345")

        self.assertNotEqual(user.password, "Pass12345")
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_email_domain_is_normalized(self):
        user = self.model.objects.create_user("test@EXAMPLE.COM", "Pass12345")

        self.assertEqual(user.email, "test@example.com")

    def test_email_local_part_keeps_case(self):
        user = self.model.objects.create_user("TeSt@example.com", "Pass12345")

        self.assertEqual(user.email, "TeSt@example.com")

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            self.model.objects.create_user("", "Pass12345")

    def test_create_user_without_email_message(self):
        with self.assertRaisesMessage(ValueError, "The given email must be set"):
            self.model.objects.create_user(None, "Pass12345")

    def test_new_user_is_not_staff_by_default(self):
        user = self.model.objects.create_user("plain@example.com", "Pass12345")

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser_flags(self):
        admin = self.model.objects.create_superuser(
            "admin@example.com", "Pass12345"
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_superuser_with_is_staff_false_raises_error(self):
        with self.assertRaisesMessage(
            ValueError, "Superuser must have is_staff=True."
        ):
            self.model.objects.create_superuser(
                "admin2@example.com", "Pass12345", is_staff=False
            )

    def test_create_superuser_with_is_superuser_false_raises_error(self):
        with self.assertRaisesMessage(
            ValueError, "Superuser must have is_superuser=True."
        ):
            self.model.objects.create_superuser(
                "admin3@example.com", "Pass12345", is_superuser=False
            )

    def test_extra_fields_are_saved(self):
        user = self.model.objects.create_user(
            "extra@example.com", "Pass12345", first_name="Olga"
        )

        self.assertEqual(user.first_name, "Olga")


class UserModelTests(TestCase):
    """Поле username прибране, автентифікація — за email."""

    def setUp(self):
        self.model = get_user_model()

    def test_username_field_is_email(self):
        self.assertEqual(self.model.USERNAME_FIELD, "email")

    def test_no_required_fields_besides_email(self):
        self.assertEqual(self.model.REQUIRED_FIELDS, [])

    def test_username_attribute_is_removed(self):
        field_names = [field.name for field in self.model._meta.get_fields()]

        self.assertNotIn("username", field_names)

    def test_email_is_unique(self):
        self.model.objects.create_user("dup@example.com", "Pass12345")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.model.objects.create_user("dup@example.com", "Pass12345")

    def test_get_by_natural_key_uses_email(self):
        user = self.model.objects.create_user("nat@example.com", "Pass12345")

        self.assertEqual(
            self.model.objects.get_by_natural_key("nat@example.com"), user
        )

    def test_orders_related_name(self):
        from airport.models import Order

        user = self.model.objects.create_user("rel@example.com", "Pass12345")
        order = Order.objects.create(user=user)

        self.assertIn(order, user.orders.all())
