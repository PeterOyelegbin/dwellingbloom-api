from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
# from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from utils import CustomJWTAuthentication, send_async_email, cache, general_logger, bvn_verification, generate_email_activation_link, verify_email_activation_link
from .models import Apartment
from .serializers import ApartmentSerializer, ApartmentSearchSerializer

# Create your views here.
class ApartmentViewSet(viewsets.ViewSet):
    """
    Apartment Management Endpoint

    A viewset for adding, viewing, updating, and deleting apartment instances."
    """
    queryset = Apartment.objects.get()
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # search_fields = ["name", "city", "state"]
    # ordering_fields = ["bedrooms", "created_at",]
    # ordering = ["-created_at"]
    
    # @action(detail=False, methods=["post"], serializer_class=ApartmentSearchSerializer)
    # def search(self, request):
    #     serializer = ApartmentSearchSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     data = serializer.validated_data

    #     queryset = self.get_queryset()

    #     if "city" in data:
    #         queryset = queryset.filter(city__icontains=data["city"])

    #     if "bedrooms" in data:
    #         queryset = queryset.filter(bedrooms=data["bedrooms"])

    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)

    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

    @swagger_auto_schema(request_body=ApartmentSerializer, responses={201: 'CREATED', 400: 'BAD REQUEST', 403: 'FORBIDDEN'})
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            if not request.user.is_owner:
                response_data = {
                    'success': False,
                    'status': 403,
                    'message': 'Permission denied!',
                }
                return Response(response_data, status=status.HTTP_403_FORBIDDEN)
            serializer.is_valid(raise_exception=True)
            serializer.save(owner=request.user.id)
            response_data = {
                'success': True,
                'status': 201,
                'message': 'Appartment created successfully',
                'data': serializer.data,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "Validation error: Apartment could not be created."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST'})
    def list(self, request):
        try:
            if request.user.is_owner:
                queryset = Apartment.objects.filter(owner=request.user.id)
                serializer = self.serializer_class(queryset, many=True)
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Appartment list retrieved successfully',
                    'data': serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            queryset = Apartment.objects.filter(is_available=True)
            page = self.paginate_queryset(queryset)
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Appartment list retrieved successfully',
                'data': self.get_paginated_response(serializer.data)
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "An error occured: Apartment list could not be retrieved."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST'})
    def retrieve(self, request, pk):
        try:
            if request.user.is_owner:
                queryset = Apartment.objects.filter(pk=pk, owner=request.user.id)
                serializer = self.serializer_class(queryset, many=True)
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Appartment retrieved successfully',
                    'data': serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            queryset = Apartment.objects.filter(pk=pk, is_available=True)
            page = self.paginate_queryset(queryset)
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Appartment retrieved successfully',
                'data': self.get_paginated_response(serializer.data)
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "An error occured: Apartment could not be retrieved."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    @swagger_auto_schema(request_body=ApartmentSerializer, responses={200: 'OK', 400: 'BAD REQUEST'})
    def update(self, request, pk):
        try:
            if request.user.is_owner:
                queryset = Apartment.objects.filter(pk=pk, owner=request.user.id)
                serializer = self.serializer_class(queryset, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Appartment updated successfully',
                    'data': serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            elif request.user.is_admin:
                queryset = Apartment.objects.filter(pk=pk)
                serializer = self.serializer_class(queryset, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Appartment updated successfully',
                    'data': serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'success': False,
                    'status': 403,
                    'message': 'Permisinon denied!'
                }
                return Response(response_data, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "An error occured: Apartment could not be updated."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
    @swagger_auto_schema(responses={205: 'RESET CONTENT', 400: 'BAD REQUEST', 403: 'FORBIDDEN', 404: 'NOT FOUND'})
    def destroy(self, request, pk):
        try:
            if not request.user.is_admin:
                response_data = {
                    'success': False,
                    'status': 403,
                    'message': 'Permission denied!',
                }
                return Response(response_data, status=status.HTTP_403_FORBIDDEN)
            queryset = Apartment.objects.get(pk=pk)
            queryset.delete()
            response_data = {
                'success': True,
                'status': 205,
                'message': 'Appartment deleted successfully',
            }
            return Response(response_data, status=status.HTTP_205_RESET_CONTENT)
        except Apartment.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'message': 'Apartment not found',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "An error occured: Apartment could not be deleted."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        