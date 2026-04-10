from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            redirect_authenticated_user=True, template_name="registration/login.html"
        ),
        name="login",
    ),
    path("", include("django.contrib.auth.urls")),
    path("home/", views.home, name="home"),
    # AJAX endpoints
    path("check-username/", views.check_username, name="check_username"),
    # Email verification
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    # left sidebar urls
    path("explore/", views.explore, name="explore"),
    path("explore/who-to-follow/", views.who_to_follow, name="who_to_follow"),
    path("notifications/", views.notifications, name="notifications"),
    path("profile/", views.profile, name="profile"),
    path(
        "search/",
        RedirectView.as_view(pattern_name="explore", query_string=True),
        name="search",
    ),
    # Profile URLs
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path(
        "profile/picture/update/",
        views.update_profile_picture,
        name="update_profile_picture",
    ),
    path("profile/followers/", views.followers_list, name="followers_list"),
    path("profile/following/", views.following_list, name="following_list"),
    path("profile/bookmarks/", views.user_bookmarks, name="user_bookmarks"),
    # Profile API endpoints for lazy loading
    path(
        "api/profile/bookmarks/",
        views.profile_bookmarks_api,
        name="profile_bookmarks_api",
    ),
    path("api/profile/likes/", views.profile_likes_api, name="profile_likes_api"),
    # Settings URLs
    path("settings/", views.settings, name="settings"),
    path("settings/account/", views.settings_account, name="settings_account"),
    path("settings/security/", views.settings_security, name="settings_security"),
    path(
        "settings/notifications/",
        views.settings_notifications,
        name="settings_notifications",
    ),
    path("settings/privacy/", views.settings_privacy, name="settings_privacy"),
    path(
        "settings/bookmarklet/", views.settings_bookmarklet, name="settings_bookmarklet"
    ),
    # Follow system
    path("user/<int:user_id>/follow/", views.follow_user, name="follow_user"),
    path("user/<str:username>/", views.user_profile, name="user_profile"),
    # Notification actions
    path(
        "notifications/mark-read/",
        views.mark_notifications_read,
        name="mark_notifications_read",
    ),
]
