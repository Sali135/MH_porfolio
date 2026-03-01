from django.contrib import admin

from .models import ContactMessage, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "is_featured", "url")
    list_filter = ("date", "is_featured")
    search_fields = ("title", "description")
    ordering = ("-date", "-id")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    ordering = ("-created_at",)
