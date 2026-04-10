import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib.auth.hashers import make_password

logger = logging.getLogger(__name__)
UserModel = get_user_model()

class UsernameOrEmailBackend(ModelBackend):
    # username or an email address
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        candidate = (username or "").strip()

        try:
            user = UserModel.objects.get(
                Q(username__iexact=candidate) | Q(email__iexact=candidate)
            )
        except UserModel.DoesNotExist:
            # dummy hash to mitigate timing attacks
            make_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            #  this shouldn't happen because unique email
            logger.warning("Multiple users found for login candidate: %s", candidate)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None