from rest_framework import serializers
from authentication.serializers import SignupSerializer
from .models import Apartment, ApartmentImage


class ApartmentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ApartmentImage
        fields = ['id', 'image']


class ApartmentSerializer(serializers.ModelSerializer):
    owner = SignupSerializer(read_only=True)
    images = ApartmentImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    
    class Meta:
        model = Apartment
        fields = "__all__"
        read_only_fields = ("is_verified", "created_at", "updated_at")
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        apartment = super().create(validated_data)
        for image in uploaded_images:
            ApartmentImage.objects.create(apartment=apartment, image=image)
        return apartment


class ApartmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ("id", "name", "apartment_type", "bedrooms", "bathrooms", "city", "state", "monthly_rent", "images")


class OwnerApartmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ("monthly_rent", "agreement_fee", "is_available")


class AdminApartmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ("__all__")
        read_only_fields = ("id", "owner", "created_at", "updated_at")
