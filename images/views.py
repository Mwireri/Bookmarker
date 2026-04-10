import redis
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.models import Activity
from .forms import ImageForm
from .models import Image


r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


@login_required
def image_create(request):
    if request.method == "POST":
        form = ImageForm(request.POST, user=request.user)
        if form.is_valid():
            image = form.save(commit=False)
            image.user = request.user
            image.save()
            messages.success(request, "Image bookmarked successfully!")
            return redirect(image.get_absolute_url())
    else:
        form = ImageForm(data=request.GET, user=request.user)

    return render(
        request,
        "images/image/create.html",
        {"form": form}
    )


@login_required
def image_detail(request, id, slug):
    image = get_object_or_404(Image, id=id, slug=slug)
    key = f"image:{id}:views"

    r.setnx(key, image.views)
    total_views = int(r.incr(key))
    return render(
        request,
        "images/image/detail.html",
        {
            "image": image,
            "total_views": total_views,
        }
    )


@login_required
@require_POST
def image_like(request):
    image_id = request.POST.get("id")

    if not image_id:
        return JsonResponse(
            {"status": "error", "message": "Image ID required"}, status=400
        )

    image = get_object_or_404(Image, id=image_id)

    if image.users_like.filter(id=request.user.id).exists():
        image.users_like.remove(request.user)
        image.total_likes -= 1
        image.save(update_fields=["total_likes"])
        liked = False
    else:
        image.users_like.add(request.user)
        image.total_likes += 1
        image.save(update_fields=["total_likes"])
        liked = True
        # activity notification for the image owner
        Activity.create_activity(
            user=image.user,
            actor=request.user,
            verb="like",
            target=image,
        )

    return JsonResponse(
        {"status": "ok", "liked": liked, "total_likes": image.total_likes}
    )
