import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .models import ContactMessage, Project


def _valid_test_image(name="test.gif"):
    return SimpleUploadedFile(
        name,
        (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


class HomeViewTests(TestCase):
    def _create_project(self, title, date, is_featured=False, description=None):
        return Project.objects.create(
            title=title,
            description=description or "Description de projet test",
            image=SimpleUploadedFile(
                f"{title}.jpg", b"fake-image-content", content_type="image/jpeg"
            ),
            url="https://example.com",
            date=date,
            is_featured=is_featured,
        )

    def setUp(self):
        self.recent_project = self._create_project(
            title="Portfolio Test",
            date=datetime.date(2026, 1, 2),
            is_featured=True,
        )
        self.old_project = self._create_project(
            title="Older Portfolio",
            date=datetime.date(2025, 12, 20),
        )

    def test_home_page_returns_200_and_contains_project(self):
        response = self.client.get(reverse("portfolio:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Portfolio Test")
        self.assertTemplateUsed(response, "home.html")

    def test_home_page_orders_projects_by_recent_date(self):
        response = self.client.get(reverse("portfolio:home"))
        projects = list(response.context["projects"])

        self.assertEqual(projects[0], self.recent_project)
        self.assertEqual(projects[1], self.old_project)

    def test_home_page_filters_projects_with_query(self):
        self._create_project(
            title="Django CRM",
            description="Gestion des clients",
            date=datetime.date(2026, 1, 3),
        )

        response = self.client.get(reverse("portfolio:home"), {"q": "crm"})

        self.assertContains(response, "Django CRM")
        self.assertNotContains(response, "Portfolio Test")
        self.assertEqual(response.context["project_count"], 1)

    def test_home_page_includes_featured_projects(self):
        response = self.client.get(reverse("portfolio:home"))
        featured_projects = list(response.context["featured_projects"])

        self.assertEqual(featured_projects, [self.recent_project])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_EMAIL="contact@example.com",
    DEFAULT_FROM_EMAIL="noreply@example.com",
)
class ContactViewTests(TestCase):
    def test_contact_page_returns_200(self):
        response = self.client.get(reverse("portfolio:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact.html")

    def test_contact_form_creates_message_and_sends_email(self):
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Collaboration",
            "message": "Bonjour, j'aimerais collaborer sur un projet.",
        }
        response = self.client.post(reverse("portfolio:contact"), payload, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertContains(response, "Votre message a ete envoye avec succes")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Collaboration", mail.outbox[0].subject)

    def test_contact_form_validation_errors(self):
        response = self.client.post(reverse("portfolio:contact"), {"name": "Alice"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "This field is required")

    def test_contact_form_honeypot_blocks_spam_submission(self):
        payload = {
            "name": "Bot",
            "email": "bot@example.com",
            "subject": "Spam",
            "message": "Spam message",
            "website": "https://spam.example.com",
        }
        response = self.client.post(reverse("portfolio:contact"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "Spam detection triggered")

    @patch("portfolio.views.send_mail", side_effect=RuntimeError("smtp down"))
    def test_contact_form_handles_email_failure(self, _mock_send_mail):
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "SMTP failure",
            "message": "Bonjour",
        }
        response = self.client.post(reverse("portfolio:contact"), payload, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertContains(
            response,
            "Message enregistre, mais la notification email est temporairement indisponible.",
        )

    @override_settings(
        CONTACT_FORM_RATE_LIMIT_COUNT=2,
        CONTACT_FORM_RATE_LIMIT_WINDOW_SECONDS=3600,
    )
    def test_contact_form_rate_limit_blocks_after_threshold(self):
        for index in range(2):
            self.client.post(
                reverse("portfolio:contact"),
                {
                    "name": f"Alice {index}",
                    "email": f"alice{index}@example.com",
                    "subject": f"Collaboration {index}",
                    "message": "Bonjour",
                },
            )

        response = self.client.post(
            reverse("portfolio:contact"),
            {
                "name": "Alice 3",
                "email": "alice3@example.com",
                "subject": "Collaboration 3",
                "message": "Bonjour",
            },
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 2)
        self.assertContains(response, "Trop de tentatives", status_code=429)


class ContactInboxTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="staff",
            password="test-pass-123",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username="regular",
            password="test-pass-123",
            is_staff=False,
        )
        self.unread_message = ContactMessage.objects.create(
            name="Alice",
            email="alice@example.com",
            subject="Unread subject",
            message="Unread message",
        )
        self.read_message = ContactMessage.objects.create(
            name="Bob",
            email="bob@example.com",
            subject="Read subject",
            message="Read message",
            is_read=True,
        )

    def test_contact_inbox_requires_staff(self):
        inbox_url = reverse("portfolio:contact_inbox")

        anonymous_response = self.client.get(inbox_url)
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn("/admin/login/", anonymous_response.url)

        self.client.login(username="regular", password="test-pass-123")
        regular_response = self.client.get(inbox_url)
        self.assertEqual(regular_response.status_code, 302)
        self.assertIn("/admin/login/", regular_response.url)

    def test_contact_inbox_export_requires_staff(self):
        export_url = reverse("portfolio:contact_inbox_export")

        anonymous_response = self.client.get(export_url)
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn("/admin/login/", anonymous_response.url)

    def test_staff_can_view_and_filter_contact_inbox(self):
        self.client.login(username="staff", password="test-pass-123")

        response = self.client.get(reverse("portfolio:contact_inbox"), {"status": "unread"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unread subject")
        self.assertNotContains(response, "Read subject")
        self.assertTemplateUsed(response, "contact_inbox.html")

    def test_staff_can_mark_message_read_and_unread(self):
        self.client.login(username="staff", password="test-pass-123")
        update_url = reverse(
            "portfolio:contact_inbox_update",
            args=[self.unread_message.id],
        )

        self.client.post(update_url, {"action": "read"})
        self.unread_message.refresh_from_db()
        self.assertTrue(self.unread_message.is_read)

        self.client.post(update_url, {"action": "unread"})
        self.unread_message.refresh_from_db()
        self.assertFalse(self.unread_message.is_read)

    def test_staff_can_export_filtered_messages_as_csv(self):
        self.client.login(username="staff", password="test-pass-123")

        response = self.client.get(
            reverse("portfolio:contact_inbox_export"),
            {"status": "unread"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        content = response.content.decode("utf-8")
        self.assertIn("Unread subject", content)
        self.assertNotIn("Read subject", content)


class DashboardProjectTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="dashstaff",
            password="test-pass-123",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username="dashregular",
            password="test-pass-123",
            is_staff=False,
        )
        self.project = Project.objects.create(
            title="Project Alpha",
            description="Premier projet",
            image=SimpleUploadedFile(
                "alpha.jpg", b"fake-image-content", content_type="image/jpeg"
            ),
            url="https://example.com/alpha",
            date=datetime.date(2026, 1, 1),
            is_featured=True,
        )

    def test_dashboard_requires_staff(self):
        dashboard_url = reverse("portfolio:dashboard_home")

        anonymous_response = self.client.get(dashboard_url)
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn("/admin/login/", anonymous_response.url)

        self.client.login(username="dashregular", password="test-pass-123")
        regular_response = self.client.get(dashboard_url)
        self.assertEqual(regular_response.status_code, 302)
        self.assertIn("/admin/login/", regular_response.url)

    def test_staff_can_view_dashboard(self):
        self.client.login(username="dashstaff", password="test-pass-123")
        response = self.client.get(reverse("portfolio:dashboard_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Portfolio")
        self.assertTemplateUsed(response, "dashboard/home.html")

    def test_staff_can_create_project_from_dashboard(self):
        self.client.login(username="dashstaff", password="test-pass-123")
        payload = {
            "title": "Project Beta",
            "description": "Nouveau projet",
            "image": _valid_test_image("beta.gif"),
            "url": "https://example.com/beta",
            "date": "2026-01-05",
            "is_featured": "on",
        }
        response = self.client.post(
            reverse("portfolio:dashboard_project_create"),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Project.objects.filter(title="Project Beta").exists())
        self.assertContains(response, "Projet cree avec succes.")

    def test_staff_can_update_project_from_dashboard(self):
        self.client.login(username="dashstaff", password="test-pass-123")
        payload = {
            "title": "Project Alpha Updated",
            "description": "Projet modifie",
            "url": "https://example.com/alpha-updated",
            "date": "2026-01-10",
            "is_featured": "",
        }
        response = self.client.post(
            reverse("portfolio:dashboard_project_update", args=[self.project.id]),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Project Alpha Updated")
        self.assertFalse(self.project.is_featured)
        self.assertContains(response, "Projet mis a jour.")

    def test_staff_can_delete_project_from_dashboard(self):
        self.client.login(username="dashstaff", password="test-pass-123")
        response = self.client.post(
            reverse("portfolio:dashboard_project_delete", args=[self.project.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())
        self.assertContains(response, "Projet supprime.")

    def test_dashboard_project_list_filters(self):
        Project.objects.create(
            title="Project Gamma",
            description="Second projet",
            image=SimpleUploadedFile(
                "gamma.jpg", b"fake-image-content", content_type="image/jpeg"
            ),
            url="https://example.com/gamma",
            date=datetime.date(2026, 1, 2),
            is_featured=False,
        )
        self.client.login(username="dashstaff", password="test-pass-123")

        response = self.client.get(
            reverse("portfolio:dashboard_projects"),
            {"q": "Gamma", "featured": "no"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project Gamma")
        self.assertNotContains(response, "Project Alpha")
