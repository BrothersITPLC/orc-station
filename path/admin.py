from django.contrib import admin

# Register your models here.
from .models import Path, PathStation

admin.site.register(Path)
admin.site.register(PathStation)
