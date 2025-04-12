from django.db import models
from uuid import uuid4
from authentication.models import UserModel

# Create your models here.
class ApartmentType(models.TextChoices):
    STUDIO = "STUDIO", "Studio"
    ONE_BED = "ONE_BED", "1 Bedroom"
    TWO_BED = "TWO_BED", "2 Bedroom"
    THREE_BED = "THREE_BED", "3 Bedroom"
    DUPLEX = "DUPLEX", "Duplex"
    
class Apartment(models.Model):
    """
    This model represent an apartment listing.
    """
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    owner = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, related_name="owned_apartments")
    name = models.CharField(max_length=100)
    apartment_type = models.CharField(max_length=20, choices=ApartmentType.choices)
    description = models.TextField(blank=True)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    images = models.ImageField(upload_to="apartment_images/")
    video_url = models.FileField(upload_to="apartment_videos/")
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    aggrement_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    