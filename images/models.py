from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager


class Image(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="images_created",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    url = models.URLField(max_length=2000)
    image = models.ImageField(upload_to="images/%Y/%m/%d/")
    caption = models.TextField(blank=True)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    users_like = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="images_liked", blank=True
    )
    total_likes = models.PositiveIntegerField(default=0, db_index=True)
    tags = TaggableManager(blank=True)

    class Meta:
        indexes = [models.Index(fields=["-created"])]
        ordering = ["-created"]
        unique_together = [["user", "slug"]]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("images:detail", args=[self.id, self.slug])
