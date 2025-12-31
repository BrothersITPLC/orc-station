from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.http import HttpResponseRedirect


@method_decorator(ratelimit(key='ip', rate='5/5m', method='POST', block=True), name='dispatch')
@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(sensitive_post_parameters(), name='dispatch')
class RateLimitedAdminLoginView(LoginView):
    """
    Custom admin login view with rate limiting and session isolation.
    
    Features:
    - Limits login attempts to 5 per 5 minutes per IP address
    - Clears frontend JWT sessions when logging into admin
    - Ensures only one account active per browser (admin OR frontend)
    """
    template_name = 'admin/login.html'
    
    def form_valid(self, form):
        """Override to clear frontend JWT sessions on successful admin login."""
        response = super().form_valid(form)
        
        user = form.get_user()
        
        # Clear frontend JWT sessions for this user
        # This prevents concurrent frontend and admin logins
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            from rest_framework_simplejwt.tokens import RefreshToken
            from users.models import UserSession
            from django.utils import timezone
            
            # Blacklist all JWT refresh tokens for this user
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for token in outstanding_tokens:
                try:
                    # Check if not already blacklisted
                    if not BlacklistedToken.objects.filter(token=token).exists():
                        RefreshToken(token.token).blacklist()
                except Exception:
                    pass  # Token might be expired or already blacklisted
            
            # Deactivate all frontend sessions
            UserSession.objects.filter(user=user, is_active=True).update(
                is_active=False,
                logged_out_at=timezone.now()
            )
            
            # Clear user's session token
            user.session_token = None
            user.save(update_fields=['session_token'])
            
        except Exception as e:
            # Log but don't fail admin login
            print(f"Warning: Could not clear frontend sessions on admin login: {e}")
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'site_header': 'ORC Administration',
            'site_title': 'ORC Admin',
        })
        return context

