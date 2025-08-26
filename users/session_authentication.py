from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class OneSessionPerUserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if username and password:
            user = self.authenticate_user(username, password)
            if user:
                self._logout_old_sessions(user)
                return (user, None)
        return None

    def authenticate_user(self, username, password):
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid credentials")

    def _logout_old_sessions(self, user):
        # Delete all sessions for the user
        sessions = Session.objects.all()
        for session in sessions:
            data = session.get_decoded()
            if data.get("_auth_user_id") == str(user.pk):
                session.delete()
