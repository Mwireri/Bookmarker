from django.db import models

from images.models import Image
from taggit.models import Tag

from .models import Activity, User


def notifications_context(request):
    """Add unread notification count to all templates"""
    context = {}

    if request.user.is_authenticated:
        context["unread_notifications_count"] = Activity.objects.filter(
            user=request.user, is_read=False
        ).count()

    return context


def follow_suggestions_context(request):
    """Add follow suggestions to all templates for the sidebar"""
    context = {"follow_suggestions": []}

    if request.user.is_authenticated:
        # Get users the current user is already following
        following_ids = list(request.user.following.values_list("id", flat=True))
        excluded_ids = following_ids + [request.user.id]

        # Get users followed by people you follow (friends of friends)
        suggestions = (
            User.objects.filter(followers__in=following_ids)
            .exclude(id__in=excluded_ids)
            .annotate(mutual_count=models.Count("id"))
            .order_by("-mutual_count")
            .distinct()
        )[:3]

        suggestions = list(suggestions)

        # If we don't have enough, add popular users
        if len(suggestions) < 3:
            remaining = 3 - len(suggestions)
            suggested_ids = [u.id for u in suggestions]

            popular_users = (
                User.objects.exclude(id__in=excluded_ids + suggested_ids)
                .annotate(follower_count=models.Count("followers"))
                .order_by("-follower_count")
            )[:remaining]

            suggestions.extend(popular_users)

        context["follow_suggestions"] = suggestions

    return context


def trending_tags_context(request):
    # top 10 tags used on public images, ordered by usage count
    trending = (
        Tag.objects.filter(
            taggit_taggeditem_items__content_type__model="image",
            taggit_taggeditem_items__object_id__in=Image.objects.filter(
                is_public=True
            ).values_list("id", flat=True),
        )
        .annotate(usage_count=models.Count("taggit_taggeditem_items"))
        .order_by("-usage_count")[:3]
    )
    return {"trending_tags": trending}
