from django.contrib import admin

from .models import Truck, TruckOwner

# Register your models here.
admin.site.register(Truck)
admin.site.register(TruckOwner)
