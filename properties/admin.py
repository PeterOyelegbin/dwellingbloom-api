from django.contrib import admin
from .models import Apartment

# Register your models here.
@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "landlord", "apartment_type", "state", "is_available", "updated_at")
    list_filter = ("landlord", "apartment_type", "state", "is_available", "is_verified")
    search_fields = ("name", "landlord", "city", "state")
