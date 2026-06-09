from django.db import models
from django.core.exceptions import ValidationError
from uuid import uuid4
from authentication.models import UserModel
from cloudinary_storage.storage import VideoMediaCloudinaryStorage, RawMediaCloudinaryStorage
from cloudinary_storage.validators import validate_video


# Create your models here.
def validate_file_size(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError(f"File size must not exceed {max_size / (1024 * 1024)} MB.")

def validate_video_size(file):
    max_size = 10 * 1024 * 1024  # 10 MB
    if file.size > max_size:
        raise ValidationError(f"Video size cannot exceed {max_size / (1024 * 1024)} MB.")


class ApartmentType(models.TextChoices):
    STUDIO = "STUDIO", "Studio"
    ONE_BED = "ONE_BED", "1 Bedroom"
    TWO_BED = "TWO_BED", "2 Bedroom"
    THREE_BED = "THREE_BED", "3 Bedroom"
    DUPLEX = "DUPLEX", "Duplex"


class DocumentType(models.TextChoices):
    C_OF_O = "C_OF_O", "Certificate of Origin"
    REFERENCE_LETTER = "REFERENCE_LETTER", "Reference Letter"


class Apartment(models.Model):
    """
    This model represent an apartment listing.
    """
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    owner = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, related_name="owned_apartments")
    name = models.CharField(max_length=100)
    apartment_type = models.CharField(max_length=20, choices=ApartmentType.choices, db_index=True)
    description = models.TextField(blank=True)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, db_index=True)
    video = models.FileField(storage=VideoMediaCloudinaryStorage(), upload_to="videos/", validators=[validate_video, validate_video_size])
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    agreement_fee = models.DecimalField(max_digits=10, decimal_places=2)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_file = models.FileField(storage=RawMediaCloudinaryStorage(), upload_to="documents/", validators=[validate_file_size])
    is_available = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ApartmentImage(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='images/', validators=[validate_file_size])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.apartment.name}"
