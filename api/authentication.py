from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from api.models import UserToken

class UserTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Token "):
            return None  # DRF will continue, user = Anonymous

        token_value = auth.split(" ")[1]

        try:
            token = UserToken.objects.select_related("user").get(
                token=token_value,
                is_active=True
            )
        except UserToken.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive token")

        token.mark_used()
        return (token.user, token)
