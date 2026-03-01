from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "slug")
    list_filter = ("date",)
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-date", "-id")
