from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Call the default exception handler first
    response = exception_handler(exc, context)

    # Handle ProtectedError separately if it's not already handled
    if isinstance(exc, ProtectedError):
        return Response(
            {
                "error": "Cannot delete this resource because it is referenced by other records."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # If the response is None, handle other uncaught exceptions
    if response is None:
        response = handle_other_exceptions(exc)

    return response


def handle_other_exceptions(exc):
    # Custom handling for other exceptions
    return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
