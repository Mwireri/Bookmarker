from django.contrib import admin

from .models import Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "slug",
        "is_public",
        "total_likes",
        "views",
        "created",
    ]
    list_filter = ["is_public", "created", "updated"]
    search_fields = ["title", "caption", "description"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["user"]
    date_hierarchy = "created"
    ordering = ["-created"]
    readonly_fields = ["views", "total_likes"]
