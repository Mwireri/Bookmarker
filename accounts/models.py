import secrets

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number must be entered in the format: '+999999999'",
            )
        ],
    )
    about = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="users/%Y/%m/%d/", blank=True, null=True
    )

    # Pending email change
    pending_email = models.EmailField(blank=True, null=True)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)

    following = models.ManyToManyField(
        "self",
        through="FollowRelationship",
        symmetrical=False,
        related_name="followers",
    )

    def __str__(self):
        return f"{self.email}"

    def get_followers_count(self):
        return self.followers.count()

    def get_following_count(self):
        return self.following.count()

    def get_bookmarks_count(self):
        # to do
        return 0

    def generate_email_verification_token(self):
        """Generate a secure token for email verification"""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = timezone.now()
        self.save(
            update_fields=["email_verification_token", "email_verification_sent_at"]
        )
        return self.email_verification_token

    def is_email_token_valid(self, token):
        """Check if the email verification token is valid (within 24 hours)"""
        if not self.email_verification_token or self.email_verification_token != token:
            return False
        if not self.email_verification_sent_at:
            return False
        # Token expires after 24 hours
        expiry = self.email_verification_sent_at + timezone.timedelta(hours=24)
        return timezone.now() < expiry

    def confirm_email_change(self):
        """Confirm the pending email change"""
        if self.pending_email:
            self.email = self.pending_email
            self.pending_email = None
            self.email_verification_token = None
            self.email_verification_sent_at = None
            self.save()
            return True
        return False


class FollowRelationship(models.Model):
    follower = models.ForeignKey(
        User, related_name="following_relationships", on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        User, related_name="follower_relationships", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class Activity(models.Model):
    """
    Activity stream model for tracking user actions.
    """

    VERB_CHOICES = [
        ("follow", "started following you"),
        ("like", "liked your image"),
        ("comment", "commented on your image"),
        ("bookmark", "bookmarked an image"),
    ]

    user = models.ForeignKey(
        User,
        related_name="notifications",
        on_delete=models.CASCADE,
        help_text="The user who receives this notification",
    )
    actor = models.ForeignKey(
        User,
        related_name="actions",
        on_delete=models.CASCADE,
        help_text="The user who performed the action",
    )
    verb = models.CharField(max_length=20, choices=VERB_CHOICES)

    # Generic foreign key to support different target types (User, Image, etc.)
    target_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, blank=True, null=True
    )
    target_object_id = models.PositiveIntegerField(blank=True, null=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        target_str = f" {self.target}" if self.target else ""
        return f"{self.actor.username} {self.get_verb_display()}{target_str}"

    @classmethod
    def create_activity(cls, user, actor, verb, target=None):
        """
        Create a new activity. prevents duplicate notifications for the same action.
        no  notification creation if user is the actor.
        """
        if user == actor:
            return None

        activity_kwargs = {
            "user": user,
            "actor": actor,
            "verb": verb,
        }

        if target:
            activity_kwargs["target_content_type"] = ContentType.objects.get_for_model(
                target
            )
            activity_kwargs["target_object_id"] = target.pk

        return cls.objects.create(**activity_kwargs)


class NotificationPreference(models.Model):
    """user preferences for notifications"""

    FREQUENCY_CHOICES = [
        ("immediate", "Immediately"),
        ("daily", "Daily digest"),
        ("weekly", "Weekly digest"),
        ("never", "Never"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )

    # email notifications
    email_new_follower = models.BooleanField(default=True)
    email_likes = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_weekly_digest = models.BooleanField(default=True)

    # Push notifications
    push_enabled = models.BooleanField(default=True)

    # frequency
    notification_frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="immediate"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"
