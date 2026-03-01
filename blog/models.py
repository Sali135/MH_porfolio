from django.db import models
import datetime
from django.utils.text import slugify


class Post(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="blog/images")
    date = models.DateField(default=datetime.date.today)
    slug = models.SlugField(max_length=120, unique=True, blank=True, null=True)

    class Meta:
        ordering = ("-date", "-id")

    def _build_unique_slug(self) -> str:
        base_slug = slugify(self.title)[:100] or "post"
        candidate = base_slug
        index = 2
        while Post.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
            suffix = f"-{index}"
            candidate = f"{base_slug[: 120 - len(suffix)]}{suffix}"
            index += 1
        return candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
