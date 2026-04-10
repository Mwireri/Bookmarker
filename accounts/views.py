import redis
from datetime import timedelta
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from images.models import Image
from .forms import LoginForm, UserProfileForm, UserRegistrationForm
from .models import User, Activity, FollowRelationship


r = redis.Redis(
    host=django_settings.REDIS_HOST,
    port=django_settings.REDIS_PORT,
    db=django_settings.REDIS_DB,
)


def send_email_verification(request, user, token):
    """send email verification link to the user's pending email"""
    verification_url = request.build_absolute_uri(
        reverse("verify_email", kwargs={"token": token})
    )

    subject = "Confirm your email change - ImageMark"
    message = f"""
Hi {user.get_full_name() or user.username},

You requested to change your email address on ImageMark to: {user.pending_email}

Please click the link below to confirm this change:
{verification_url}

This link will expire in 24 hours.

If you didn't request this change, you can safely ignore this email.

Thanks,
The ImageMark Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                django_settings, "DEFAULT_FROM_EMAIL", "noreply@imagemark.com"
            ),
            recipient_list=[user.pending_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def verify_email(request, token):
    """Verify and confirm email change"""
    user = get_object_or_404(User, email_verification_token=token)

    if user.is_email_token_valid(token):
        old_email = user.email
        new_email = user.pending_email
        user.confirm_email_change()
        messages.success(
            request,
            f"Your email has been successfully changed from {old_email} to {new_email}.",
        )
    else:
        messages.error(
            request,
            "This verification link has expired or is invalid. Please request a new one.",
        )

    if request.user.is_authenticated:
        return redirect("settings_account")
    return redirect("login")


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.UsernameOrEmailBackend")
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def user_login(request):
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("home")

    # prevent open redirect attacks
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        next_url = reverse("home")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd["username"],
                password=cd["password"],
            )

            if user is None:
                form.add_error(None, "Invalid username/email or password")
                return render(
                    request, "registration/login.html", {"form": form, "next": next_url}
                )

            login(request, user)

            # remember me
            remember = request.POST.get("remember_me") == "on"
            if not remember:
                request.session.set_expiry(0)

            messages.success(request, "Welcome back!")
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, "registration/login.html", {"form": form, "next": next_url})


@require_GET
def check_username(request):
    """AJAX to check if username is available"""
    username = request.GET.get("username", "").strip()

    if not username:
        return JsonResponse({"available": False, "error": "Username is required"})

    import re

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return JsonResponse({"available": False, "error": "Invalid username format"})

    queryset = User.objects.filter(username__iexact=username)
    if request.user.is_authenticated:
        queryset = queryset.exclude(pk=request.user.pk)

    available = not queryset.exists()
    return JsonResponse({"available": available})


def _get_redis_view_map(image_ids):
    if not image_ids:
        return {}

    keys = [f"image:{image_id}:views" for image_id in image_ids]
    try:
        values = r.mget(keys)
    except redis.RedisError:
        return {}

    view_map = {}
    for image_id, raw_value in zip(image_ids, values):
        if raw_value is None:
            continue
        try:
            view_map[image_id] = int(raw_value)
        except (TypeError, ValueError):
            continue
    return view_map


def _attach_display_views(images):
    image_ids = [image.id for image in images]
    view_map = _get_redis_view_map(image_ids)

    for image in images:
        image.display_views = view_map.get(image.id, image.views)


def _attach_liked_state(images, user):
    if not user.is_authenticated or not images:
        for image in images:
            image.is_liked_by_user = False
        return
    image_ids = [img.id for img in images]
    liked_ids = set(
        Image.objects.filter(id__in=image_ids, users_like=user).values_list(
            "id", flat=True
        )
    )
    for image in images:
        image.is_liked_by_user = image.id in liked_ids


def home(request):
    """Home with paginated images feed"""
    page_number = request.GET.get("page", 1)
    per_page = 12

    if request.user.is_authenticated:
        following_ids = request.user.following.values_list("id", flat=True)
        images_qs = (
            Image.objects.filter(
                Q(user_id__in=following_ids) | Q(user=request.user) | Q(is_public=True)
            )
            .select_related("user")
            .only(
                "id",
                "title",
                "slug",
                "image",
                "caption",
                "created",
                "total_likes",
                "views",
                "user__id",
                "user__username",
                "user__first_name",
                "user__last_name",
                "user__profile_picture",
            )
            .distinct()
            .order_by("-created")
        )
        user_liked_ids = set(
            Image.objects.filter(users_like=request.user).values_list("id", flat=True)
        )
    else:
        images_qs = (
            Image.objects.filter(is_public=True)
            .select_related("user")
            .only(
                "id",
                "title",
                "slug",
                "image",
                "caption",
                "created",
                "total_likes",
                "views",
                "user__id",
                "user__username",
                "user__first_name",
                "user__last_name",
                "user__profile_picture",
            )
            .order_by("-created")
        )
        user_liked_ids = set()

    paginator = Paginator(images_qs, per_page)

    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    _attach_display_views(page.object_list)

    for image in page.object_list:
        image.is_liked_by_user = image.id in user_liked_ids

    # infinite scroll
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/image_feed.html",
            {"images": page.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    context = {
        "page_title": "Home",
        "current_section": "home",
        "images": page.object_list,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
    }
    return render(request, "account/home.html", context)


# shared fields for public image queries
_PUBLIC_IMAGE_FIELDS = (
    "id",
    "title",
    "slug",
    "image",
    "caption",
    "created",
    "total_likes",
    "views",
    "user__id",
    "user__username",
    "user__first_name",
    "user__last_name",
    "user__profile_picture",
)

SORT_OPTIONS = {"likes": "-total_likes", "date": "-created"}
PERIOD_DAYS = {"week": 7, "month": 30}


def _public_images_base():
    return (
        Image.objects.filter(is_public=True)
        .select_related("user")
        .only(*_PUBLIC_IMAGE_FIELDS)
    )


def _apply_period_filter(qs, period):
    days = PERIOD_DAYS.get(period)
    if days:
        qs = qs.filter(created__gte=timezone.now() - timedelta(days=days))
    return qs


def explore(request):
    query = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()
    sort = request.GET.get("sort", "")
    period = request.GET.get("period", "all")
    is_searching = bool(query or tag)

    context = {
        "page_title": "Explore",
        "current_section": "explore",
        "search_query": query,
        "active_tag": tag,
        "current_sort": sort,
        "current_period": period,
        "is_searching": is_searching,
    }

    if is_searching:
        # results mode
        qs = _public_images_base()

        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(caption__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__name__iexact=query)
            ).distinct()

        if tag:
            qs = qs.filter(tags__name__iexact=tag)

        qs = _apply_period_filter(qs, period)

        order = SORT_OPTIONS.get(sort, "-total_likes")
        images = list(qs.order_by(order)[:60])

        _attach_display_views(images)
        _attach_liked_state(images, request.user)

        context["images"] = images
        context["result_count"] = len(images)
    else:
        # discovery mode
        base = _public_images_base()
        trending_images = list(base.order_by("-total_likes")[:12])
        fresh_images = list(base.order_by("-created")[:12])

        _attach_display_views(trending_images)
        _attach_display_views(fresh_images)
        _attach_liked_state(trending_images + fresh_images, request.user)

        context["trending_images"] = trending_images
        context["fresh_images"] = fresh_images
        context["creators"] = get_follow_suggestions(request.user, limit=5)

    return render(request, "account/explore.html", context)


@login_required
def notifications(request):
    """Activity stream/notifications page with pagination"""
    page_number = request.GET.get("page", 1)
    per_page = 20

    activities_qs = (
        Activity.objects.filter(user=request.user)
        .select_related("actor", "target_content_type")
        .order_by("-created_at")
    )

    # unread count for badge
    unread_count = activities_qs.filter(is_read=False).count()

    paginator = Paginator(activities_qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    context = {
        "page_title": "Notifications",
        "current_section": "notifications",
        "activities": page.object_list,
        "unread_count": unread_count,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
    }

    # infinite scroll
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/activity_list.html",
            {"activities": page.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    return render(request, "account/notifications.html", context)


@login_required
def bookmarks(request):
    context = {"page_title": "My Bookmarks", "current_section": "bookmarks"}
    return render(request, "account/my_bookmarks.html", context)


@login_required
def profile(request):
    """User profile overview"""
    bookmarks_count = request.user.images_created.count()
    likes_count = request.user.images_liked.count()

    context = {
        "page_title": "Profile",
        "current_section": "profile",
        "follower_count": request.user.get_followers_count(),
        "following_count": request.user.get_following_count(),
        "bookmarks_count": bookmarks_count,
        "likes_count": likes_count,
    }
    return render(request, "account/profile.html", context)


@login_required
@require_GET
def profile_bookmarks_api(request):
    """API for user's bookmarked images"""
    page_number = request.GET.get("page", 1)
    per_page = 12

    bookmarks_qs = (
        request.user.images_created.select_related("user")
        .only(
            "id",
            "title",
            "slug",
            "image",
            "caption",
            "created",
            "total_likes",
            "views",
            "user__id",
            "user__username",
            "user__first_name",
            "user__last_name",
            "user__profile_picture",
        )
        .order_by("-created")
    )

    paginator = Paginator(bookmarks_qs, per_page)

    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({"html": "", "has_next": False})

    _attach_display_views(page.object_list)

    # Get user's liked image IDs for like button state
    user_liked_ids = set(request.user.images_liked.values_list("id", flat=True))
    for image in page.object_list:
        image.is_liked_by_user = image.id in user_liked_ids

    html = render_to_string(
        "account/partials/image_grid.html",
        {"images": page.object_list},
        request=request,
    )

    return JsonResponse(
        {
            "html": html,
            "has_next": page.has_next(),
            "next_page": page.next_page_number() if page.has_next() else None,
            "total_count": paginator.count,
        }
    )


@login_required
@require_GET
def profile_likes_api(request):
    """endpoint for user's liked images"""
    page_number = request.GET.get("page", 1)
    per_page = 12

    likes_qs = (
        request.user.images_liked.select_related("user")
        .only(
            "id",
            "title",
            "slug",
            "image",
            "caption",
            "created",
            "total_likes",
            "views",
            "user__id",
            "user__username",
            "user__first_name",
            "user__last_name",
            "user__profile_picture",
        )
        .order_by("-created")
    )

    paginator = Paginator(likes_qs, per_page)

    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({"html": "", "has_next": False})

    _attach_display_views(page.object_list)

    for image in page.object_list:
        image.is_liked_by_user = True

    html = render_to_string(
        "account/partials/image_grid.html",
        {"images": page.object_list},
        request=request,
    )

    return JsonResponse(
        {
            "html": html,
            "has_next": page.has_next(),
            "next_page": page.next_page_number() if page.has_next() else None,
            "total_count": paginator.count,
        }
    )


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=request.user)

    context = {"page_title": "Edit Profile", "current_section": "profile", "form": form}
    return render(request, "account/edit_profile.html", context)


@login_required
def followers_list(request):
    """List of followers"""
    page_number = request.GET.get("page", 1)
    per_page = 20

    followers_qs = request.user.followers.select_related().order_by(
        "-follower_relationships__created_at"
    )

    # Get ID of users the current user is following for follow button state
    following_ids = set(request.user.following.values_list("id", flat=True))

    paginator = Paginator(followers_qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    followers_with_status = [
        {"user": follower, "is_following": follower.id in following_ids}
        for follower in page.object_list
    ]

    context = {
        "page_title": "Followers",
        "current_section": "profile",
        "users": followers_with_status,
        "count": paginator.count,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
        "list_type": "followers",
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/user_list.html",
            {"users": followers_with_status},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    return render(request, "account/followers_list.html", context)


@login_required
def following_list(request):
    """List of users the current user is following"""
    page_number = request.GET.get("page", 1)
    per_page = 20

    following_qs = request.user.following.select_related().order_by(
        "-following_relationships__created_at"
    )

    paginator = Paginator(following_qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    following_with_status = [
        {"user": followed, "is_following": True} for followed in page.object_list
    ]

    context = {
        "page_title": "Following",
        "current_section": "profile",
        "users": following_with_status,
        "count": paginator.count,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
        "list_type": "following",
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/user_list.html",
            {"users": following_with_status},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    return render(request, "account/following_list.html", context)


@login_required
def user_bookmarks(request):
    """User's bookmarks"""
    context = {
        "page_title": "My Bookmarks",
        "current_section": "profile",
    }
    return render(request, "account/user_bookmarks.html", context)


@login_required
def settings(request):
    """settings landing page"""
    context = {
        "page_title": "Settings",
        "current_section": "settings",
    }
    return render(request, "account/settings/index.html", context)


@login_required
def settings_account(request):
    """Account settings page"""
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()

            # email change verification
            if getattr(user, "_email_changed", False) and user.pending_email:
                token = user.generate_email_verification_token()
                # Send verification email
                send_email_verification(request, user, token)
                messages.info(
                    request,
                    f"A verification link has been sent to {user.pending_email}. "
                    "Please check your inbox to confirm the email change.",
                )

            messages.success(request, "Account settings updated successfully!")
            return redirect("settings_account")
    else:
        form = UserProfileForm(instance=request.user)

    context = {
        "page_title": "Account Settings",
        "current_section": "settings",
        "current_settings_section": "account",
        "form": form,
    }
    return render(request, "account/settings/account.html", context)


@login_required
def settings_security(request):
    """Security settings page"""
    context = {
        "page_title": "Security Settings",
        "current_section": "settings",
        "current_settings_section": "security",
    }
    return render(request, "account/settings/security.html", context)


@login_required
def settings_notifications(request):
    """Notification settings page"""
    context = {
        "page_title": "Notification Settings",
        "current_section": "settings",
        "current_settings_section": "notifications",
    }
    return render(request, "account/settings/notifications.html", context)


@login_required
def settings_privacy(request):
    """Privacy settings page"""
    context = {
        "page_title": "Privacy Settings",
        "current_section": "settings",
        "current_settings_section": "privacy",
    }
    return render(request, "account/settings/privacy.html", context)


@login_required
def settings_bookmarklet(request):
    """bookmarklet settings page"""
    site_url = request.build_absolute_uri("/").rstrip("/")

    context = {
        "page_title": "Bookmarklet",
        "current_section": "settings",
        "current_settings_section": "bookmarklet",
        "site_url": site_url,
        "bookmarklet_version": "1.0",  # Update this when bookmarklet changes
    }
    return render(request, "account/settings/bookmarklet.html", context)


@login_required
def update_profile_picture(request):
    if request.method != "POST" or not request.FILES.get("profile_picture"):
        messages.error(request, "Invalid request or no image provided.")
        return JsonResponse(
            {"success": False, "message": "Invalid request or no image provided."}
        )

    uploaded_file = request.FILES["profile_picture"]

    if uploaded_file.size > 5 * 1024 * 1024:
        messages.error(request, "File size must be less than 5MB.")
        return JsonResponse(
            {"success": False, "message": "File size must be less than 5MB."}
        )

    if not uploaded_file.content_type.startswith("image/"):
        messages.error(request, "Please upload a valid image file.")
        return JsonResponse(
            {"success": False, "message": "Please upload a valid image file."}
        )

    try:
        if request.user.profile_picture:
            request.user.profile_picture.delete(save=False)

        request.user.profile_picture = uploaded_file
        request.user.save()

        messages.success(request, "Profile picture updated successfully!")
        return JsonResponse(
            {
                "success": True,
                "image_url": request.user.profile_picture.url,
                "message": "Profile picture updated successfully!",
                "reload": True,  # Add this flag to trigger reload
            }
        )
    except Exception as e:
        error_message = f"Error updating profile picture: {str(e)}"
        messages.error(request, error_message)
        return JsonResponse({"success": False, "message": error_message})


@login_required
@require_POST
def follow_user(request, user_id):
    """AJAX endpoint to follow or unfollow a user"""
    try:
        target_user = get_object_or_404(User, id=user_id)

        if target_user == request.user:
            return JsonResponse(
                {"success": False, "error": "You cannot follow yourself."}, status=400
            )

        is_following = FollowRelationship.objects.filter(
            follower=request.user, following=target_user
        ).exists()

        if is_following:
            # unfollow
            FollowRelationship.objects.filter(
                follower=request.user, following=target_user
            ).delete()
            action = "unfollowed"
        else:
            # follow
            FollowRelationship.objects.create(
                follower=request.user, following=target_user
            )
            # create activity notification for the followed user
            Activity.create_activity(
                user=target_user,
                actor=request.user,
                verb="follow",
                target=request.user,  # The target is the actor (follower) for profile linking
            )
            action = "followed"

        return JsonResponse(
            {
                "success": True,
                "action": action,
                "is_following": not is_following,
                "follower_count": target_user.get_followers_count(),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def user_profile(request, username):
    """View another user's public profile"""
    profile_user = get_object_or_404(User, username=username)

    is_following = False
    if request.user.is_authenticated and request.user != profile_user:
        is_following = FollowRelationship.objects.filter(
            follower=request.user, following=profile_user
        ).exists()

    # Get user's public bookmarks with pagination
    page_number = request.GET.get("page", 1)
    per_page = 12

    bookmarks_qs = (
        profile_user.images_created.filter(is_public=True)
        .select_related("user")
        .order_by("-created")
    )

    paginator = Paginator(bookmarks_qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    _attach_display_views(page.object_list)

    context = {
        "page_title": f"{profile_user.username}'s Profile",
        "current_section": "profile",
        "profile_user": profile_user,
        "is_following": is_following,
        "is_own_profile": request.user == profile_user,
        "follower_count": profile_user.get_followers_count(),
        "following_count": profile_user.get_following_count(),
        "bookmarks_count": profile_user.images_created.filter(is_public=True).count(),
        "likes_count": profile_user.images_liked.count(),
        "images": page.object_list,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
    }

    # AJAX requests for infinite scroll
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/image_grid.html",
            {"images": page.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    return render(request, "account/user_profile.html", context)


@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all or specific notifications as read"""
    notification_id = request.POST.get("notification_id")

    if notification_id:
        # Mark specific notification as read
        Activity.objects.filter(id=notification_id, user=request.user).update(
            is_read=True
        )
    else:
        # Mark all as read
        Activity.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return JsonResponse({"success": True})


def get_follow_suggestions(user, limit=5):
    if not user.is_authenticated:
        # for anonymous users, return most popular users
        return User.objects.annotate(follower_count=Count("followers")).order_by(
            "-follower_count"
        )[:limit]

    # Get users the current user is already following
    following_ids = user.following.values_list("id", flat=True)
    excluded_ids = list(following_ids) + [user.id]

    # get users followed by people you follow
    friends_of_friends = (
        User.objects.filter(followers__in=following_ids)
        .exclude(id__in=excluded_ids)
        .annotate(mutual_count=Count("id"))
        .order_by("-mutual_count")
    )[:limit]

    suggestions = list(friends_of_friends)

    # If not enough suggestions, add popular users
    if len(suggestions) < limit:
        remaining = limit - len(suggestions)
        suggested_ids = [u.id for u in suggestions]

        popular_users = (
            User.objects.exclude(id__in=excluded_ids + suggested_ids)
            .annotate(follower_count=Count("followers"))
            .order_by("-follower_count")
        )[:remaining]

        suggestions.extend(popular_users)

    return suggestions


@login_required
def who_to_follow(request):
    """Full page of follow suggestions"""
    page_number = request.GET.get("page", 1)
    per_page = 20

    following_ids = list(request.user.following.values_list("id", flat=True))
    excluded_ids = following_ids + [request.user.id]

    # Friends of friends first, then popular users
    suggestions_qs = (
        User.objects.exclude(id__in=excluded_ids)
        .annotate(follower_count=Count("followers"))
        .order_by("-follower_count")
    )

    paginator = Paginator(suggestions_qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"html": "", "has_next": False})
        page = paginator.page(1)

    users_with_status = [{"user": u, "is_following": False} for u in page.object_list]

    context = {
        "page_title": "Who to Follow",
        "current_section": "explore",
        "users": users_with_status,
        "count": paginator.count,
        "page_obj": page,
        "has_next": page.has_next(),
        "next_page": page.next_page_number() if page.has_next() else None,
        "list_type": "suggestions",
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "account/partials/user_list.html",
            {"users": users_with_status},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page.has_next(),
                "next_page": page.next_page_number() if page.has_next() else None,
            }
        )

    return render(request, "account/who_to_follow.html", context)
