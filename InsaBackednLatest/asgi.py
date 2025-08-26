"""
ASGI config for InsaBackednLatest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import sys

from django.core.asgi import get_asgi_application


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InsaBackednLatest.settings")
    if "migrate" in sys.argv:
        from django.db import connection

        connection.settings_dict["RUNNING_MIGRATION"] = True
    try:
        from django.core.management import execute_from_command_line

        execute_from_command_line(sys.argv)
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc


if __name__ == "__main__":
    main()

# application = get_asgi_application()
