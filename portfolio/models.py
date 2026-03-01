from django.db import models
from datetime import date


class Project(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=250)
    image = models.ImageField(upload_to="portfolio/images")
    url = models.URLField(blank=True)
    date = models.DateField(default=date.today)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ("-date", "-id")

    def __str__(self) -> str:
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=140)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.name} - {self.subject}"
