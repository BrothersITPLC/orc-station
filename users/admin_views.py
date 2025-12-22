from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters


@method_decorator(ratelimit(key='ip', rate='5/5m', method='POST', block=True), name='dispatch')
@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(sensitive_post_parameters(), name='dispatch')
class RateLimitedAdminLoginView(LoginView):
    """
    Custom admin login view with rate limiting.
    Limits login attempts to 5 per 5 minutes per IP address.
    """
    template_name = 'admin/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'site_header': 'ORC Administration',
            'site_title': 'ORC Admin',
        })
        return context
