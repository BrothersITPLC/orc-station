from django.contrib import admin

from .models import Checkin, Commodity, Declaracion, ManualPayment, PaymentMethod

# Register your models here.

admin.site.register(Declaracion)
admin.site.register(Checkin)
admin.site.register(Commodity)
admin.site.register(PaymentMethod)
admin.site.register(ManualPayment)
