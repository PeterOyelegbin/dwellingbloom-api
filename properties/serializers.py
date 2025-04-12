from rest_framework import serializers
from authentication.serializers import SignupSerializer
from .models import Apartment

class ApartmentSerializer(serializers.ModelSerializer):
    owner = SignupSerializer(read_only=True)
    
    class Meta:
        model = Apartment
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

class ApartmentSearchSerializer(serializers.Serializer):
    city = serializers.CharField(required=False)
    bedrooms = serializers.IntegerField(required=False, min_value=0)
    