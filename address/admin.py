from django.contrib import admin

from .models import RegionOrCity, Woreda, ZoneOrSubcity

# Register your models here.

admin.site.register(RegionOrCity)
admin.site.register(ZoneOrSubcity)
admin.site.register(Woreda)
