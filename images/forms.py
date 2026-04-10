from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image as PILImage

from .models import Image

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MIN_IMAGE_WIDTH = 300
MIN_IMAGE_HEIGHT = 300


class ImageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Image
        fields = ["title", "caption", "description", "url", "is_public"]
        widgets = {
            "url": forms.URLInput(
                attrs={"placeholder": "https://example.com/image.jpg"}
            ),
            "title": forms.TextInput(attrs={"placeholder": "Give your image a title"}),
            "caption": forms.TextInput(attrs={"placeholder": "Add caption (optional)"}),
            "description": forms.Textarea(
                attrs={"placeholder": "Add a description...", "rows": 3}
            ),
        }

    def clean_url(self):
        url = self.cleaned_data.get("url")
        valid_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
        extension = urlparse(url).path.split(".")[-1].lower()
        if extension not in valid_extensions:
            raise forms.ValidationError("The URL must point to an image file.")
        return url

    def clean(self):
        cleaned_data = super().clean()
        url = cleaned_data.get("url")
        title = cleaned_data.get("title")

        if self.user and url:
            # check duplicate URL
            if Image.objects.filter(user=self.user, url=url).exists():
                raise forms.ValidationError("You have already bookmarked this image.")

            # Check for duplicate slug
            if title:
                slug = slugify(title)
                if Image.objects.filter(user=self.user, slug=slug).exists():
                    raise forms.ValidationError(
                        "You already have an image with this title. Please use a different title."
                    )

        return cleaned_data

    def save(self, commit=True):
        """
        Download and save the image from the URL.
        TODO; add celery to download images asynchronously.
        """
        image = super().save(commit=False)
        url = self.cleaned_data["url"]

        try:
            # add a user-agent header to avoid being blocked by some servers
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response = urlopen(request, timeout=10)

            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                raise forms.ValidationError("The URL does not point to a valid image.")

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    "Image file size exceeds the maximum limit of 5MB."
                )

            image_content = response.read()

            # check image dimensions
            try:
                pil_image = PILImage.open(BytesIO(image_content))
                width, height = pil_image.size
                if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                    raise forms.ValidationError(
                        f"Image is too small ({width}x{height}). "
                        f"Minimum dimensions are {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels."
                    )
            except forms.ValidationError:
                raise
            except Exception:
                raise forms.ValidationError("Could not read image dimensions.")

            # generate filename from URL
            image_name = urlparse(url).path.rsplit("/", 1)[-1]
            if not image_name or "." not in image_name:
                extension = content_type.split("/")[-1].replace("jpeg", "jpg")
                image_name = f"image.{extension}"

            image.image.save(image_name, ContentFile(image_content), save=False)

        except HTTPError as e:
            raise forms.ValidationError(f"Could not download image: HTTP {e.code}")
        except URLError as e:
            raise forms.ValidationError(f"Could not download image: {e.reason}")
        except TimeoutError:
            raise forms.ValidationError("Image download timed out. Please try again.")

        if commit:
            image.save()
        return image
