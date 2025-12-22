class SecurityHeadersMiddleware:
    """
    Adds modern HTTP security headers required by security audits.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Permissions Policy (restrict browser features)
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "fullscreen=(self), payment=()"
        )

        # Cross-Origin protections
        response["Cross-Origin-Embedder-Policy"] = "require-corp"
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["Cross-Origin-Resource-Policy"] = "same-origin"

        return response
