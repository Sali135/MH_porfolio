import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Post


class BlogViewsTests(TestCase):
    def _create_post(self, title, description="Contenu de test", date=None):
        return Post.objects.create(
            title=title,
            description=description,
            image=SimpleUploadedFile(
                f"{title}.jpg", b"fake-image-content", content_type="image/jpeg"
            ),
            date=date or datetime.date.today(),
        )

    def setUp(self):
        self.post = self._create_post(
            title="Mon premier post",
            date=datetime.date(2026, 1, 1),
        )

    def test_slug_is_generated_from_title(self):
        self.assertEqual(self.post.slug, "mon-premier-post")

    def test_slug_is_unique_for_duplicate_titles(self):
        duplicate = self._create_post("Mon premier post")
        self.assertNotEqual(duplicate.slug, self.post.slug)
        self.assertTrue(duplicate.slug.startswith("mon-premier-post"))

    def test_posts_page_returns_200_and_contains_post(self):
        response = self.client.get(reverse("blog:posts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mon premier post")
        self.assertTemplateUsed(response, "blog.html")

    def test_posts_support_search(self):
        self._create_post("Python avance", description="Guide de productivite")

        response = self.client.get(reverse("blog:posts"), {"q": "premier"})

        self.assertContains(response, "Mon premier post")
        self.assertNotContains(response, "Python avance")

    def test_posts_are_paginated(self):
        for index in range(1, 9):
            self._create_post(f"Post {index}")

        response = self.client.get(reverse("blog:posts"))
        self.assertEqual(len(response.context["posts"]), 6)
        self.assertTrue(response.context["page_obj"].has_next())

        second_page = self.client.get(reverse("blog:posts"), {"page": 2})
        self.assertEqual(second_page.status_code, 200)
        self.assertGreater(len(second_page.context["posts"]), 0)

    def test_post_detail_returns_200(self):
        response = self.client.get(reverse("blog:post_detail", args=[self.post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contenu de test")
        self.assertTemplateUsed(response, "post_detail.html")

    def test_post_detail_returns_404_for_unknown_slug(self):
        response = self.client.get(reverse("blog:post_detail", args=["inexistant"]))
        self.assertEqual(response.status_code, 404)

    def test_legacy_post_detail_redirects_to_slug_url(self):
        legacy_url = reverse("blog:post_detail_legacy", args=[self.post.id])
        modern_url = reverse("blog:post_detail", args=[self.post.slug])
        response = self.client.get(legacy_url)

        self.assertRedirects(response, modern_url, status_code=301, target_status_code=200)
