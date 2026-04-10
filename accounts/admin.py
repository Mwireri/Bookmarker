from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User
from copy import deepcopy


@admin.register(User)
class UserAdmin(UserAdmin):
    model = User

    fieldsets = list(deepcopy(UserAdmin.fieldsets))
    # personal info
    fieldsets[1] = (
        "Personal info",
        {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "date_of_birth",
            )
        },
    )

    # additional info section
    fieldsets.append(
        ('Additional info', {
            'fields': [
                'country',
                'profile_picture',
            ],
        }),
    )

    fieldsets = tuple(fieldsets)

    add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('username', 'email', 'password1', 'password2'),
    }),
    )
