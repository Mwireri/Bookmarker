from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class LoginForm(forms.Form):
    username = forms.CharField(label="Username or email")
    password = forms.CharField(widget=forms.PasswordInput)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "about",
            "country",
            "date_of_birth",
            "profile_picture",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "+1234567890"}
            ),
            "about": forms.Textarea(attrs={"class": "form-textarea", "rows": 4}),
            "country": forms.TextInput(attrs={"class": "form-input"}),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "profile_picture": forms.FileInput(attrs={"class": "form-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["phone_number"].required = False
        self.fields["about"].required = False
        self.fields["country"].required = False
        self.fields["date_of_birth"].required = False
        self.fields["profile_picture"].required = False

        # store original email for comparison
        self._original_email = self.instance.email if self.instance.pk else None

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and email != self._original_email:
            User = get_user_model()
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        new_email = self.cleaned_data.get("email")
        if new_email and new_email != self._original_email:
            # don't change email directly. store as pending
            user.email = self._original_email
            user.pending_email = new_email
            user._email_changed = True
        else:
            user._email_changed = False

        if commit:
            user.save()
        return user


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter your email address",
                "autocomplete": "email",
            }
        ),
        help_text="Required. Enter a valid email address.",
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "First name (optional)",
                "autocomplete": "given-name",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Last name (optional)",
                "autocomplete": "family-name",
            }
        ),
    )

    # Honeypot field
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="Leave this field blank",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # styling password fields
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "Enter password",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        )

        self.fields["username"].help_text = (
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )

        self.fields["password1"].help_text = self.fields["password1"].help_text or ""

        # Add aria-describedby
        for field_name, field in self.fields.items():
            if field.help_text:
                field.widget.attrs["aria-describedby"] = f"{field_name}_help_text"

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_website(self):
        # Honeypot validation, if filled
        website = self.cleaned_data.get("website")
        if website:
            raise forms.ValidationError("Invalid form submission.")
        return website

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
        return user
