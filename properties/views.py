from rest_framework import viewsets, status, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter
from utils.logger_config import general_logger
from utils.page_config import ListPagination
from utils.validation_helper import extract_validation_error_message
from .models import Apartment
from .serializers import *
import hashlib

# Create your views here.
@extend_schema(tags=['Apartment'])
class ApartmentViewSet(viewsets.ViewSet):
    """
    Apartment Management Endpoint

    A viewset for adding, viewing, updating, and deleting apartment instances."
    """
    serializer_class = ApartmentSerializer
    parser_classes   = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.AllowAny()]
        elif self.action in ['verify_apartment', 'destroy']:
            return [permissions.IsAdminUser()]
        else:
            return [permissions.IsAuthenticated()]

    @extend_schema(request={'multipart/form-data': ApartmentSerializer})
    def create(self, request):
        """
        Create an apartment endpoint.

        Owners only. Accepts multipart/form-data to support image uploads.
        """
        if request.user.role != 'OWNER':
            return Response(
                {'success': False, 'status': 403, 'message': 'Permission denied!'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.serializer_class(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save(owner=request.user)
            cache.delete_pattern("public_apartments_*")
            return Response(
                {'success': True, 'status': 201, 'message': 'Apartment created successfully', 'data': serializer.data},
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error creating apartment: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            general_logger.error("Exception error creating apartment: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', type=str, description='Search by city'),
            OpenApiParameter(name='page', type=int, description='Page number'),
            OpenApiParameter(name='page_size', type=int, description='Results per page (max 100)'),
        ],
    )
    def list(self, request):
        """
        List apartments endpoint.

        - Admins see all apartments.
        - Owners see only their own apartments.
        - Public users see only verified and available apartments.
        Supports search by city via ?search=
        Supports pagination via ?page= and ?page_size=
        """
        try:
            # Sanitise inputs before building the cache key to prevent key flooding
            search_query = request.query_params.get('search', '').strip()[:100]  # max 100 chars
            page_num = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            is_public_request = not (request.user.is_authenticated and (request.user.is_staff or request.user.role == 'OWNER'))
            # Hash the search term so the Redis key length is always fixed
            search_hash = hashlib.md5(search_query.encode()).hexdigest()
            cache_key = f'public_apartments_{search_hash}_p{page_num}_s{page_size}'
            if is_public_request:
                cached_data = cache.get(cache_key)
                if cached_data:
                    return Response(cached_data, status=status.HTTP_200_OK)
            apartments = Apartment.objects.select_related('owner').prefetch_related('images').all().order_by('id')
            if request.user.is_authenticated and request.user.is_staff:
                pass
            elif request.user.is_authenticated and request.user.role == 'OWNER':
                apartments = apartments.filter(owner=request.user.id)
            else:
                apartments = apartments.filter(is_verified=True, is_available=True)
            if search_query:
                apartments = apartments.filter(Q(name__icontains=search_query) | Q(city__icontains=search_query) | Q(state__icontains=search_query))
            paginator = ListPagination()
            paginated_apartments = paginator.paginate_queryset(apartments, request)
            serializer = ApartmentSummarySerializer(paginated_apartments, many=True)
            response_data = {
                "success": True,
                "status": 200,
                "message": "Apartments listed successfully",
                "pagination": {
                    "total":    paginator.page.paginator.count,
                    "page":     paginator.page.number,
                    "pages":    paginator.page.paginator.num_pages,
                    "has_next": paginator.page.has_next(),
                    "has_prev": paginator.page.has_previous(),
                },
                "data": serializer.data,
            }
            if is_public_request:
                cache.set(cache_key, response_data, timeout=settings.CACHE_TTL_MINUTES * 60)
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("Exception error listing apartments: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema()
    def retrieve(self, request, pk=None):
        """
        Retrieve an apartment endpoint.

        Retrieves apartment data using apartment ID.
        Owners can only retrieve their own apartments.
        """
        try:
            # Build base filter
            filters = {'id': pk}
            # Owners are restricted to their own apartments
            if request.user.is_authenticated and request.user.role == 'OWNER':
                filters['owner'] = request.user.id
            apartment = Apartment.objects.select_related('owner').prefetch_related('images').get(**filters)
            serializer = self.serializer_class(apartment)
            return Response(
                { 'success': True, 'status': 200, 'message': 'Appartment retrieved successfully', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except Apartment.DoesNotExist:
            return Response(
                {"success": False, "status": 404, "error": "Apartment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            general_logger.error("Exception error retrieving apartment (pk=%s): %s", pk, e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(request=OwnerApartmentUpdateSerializer)
    def partial_update(self, request, pk=None):
        try:
            """
            Update an apartment endpoint.

            Owners can only update limited fields of their own apartments.
            Admins can update any field of any apartment.
            """
            if request.user.is_staff:
                apartment = Apartment.objects.select_related('owner').prefetch_related('images').get(id=pk)
                serializer = AdminApartmentUpdateSerializer(apartment, data=request.data, partial=True)
            elif request.user.role == 'OWNER':
                apartment = Apartment.objects.select_related('owner').prefetch_related('images').get(id=pk, owner=request.user.id)
                serializer = OwnerApartmentUpdateSerializer(apartment, data=request.data, partial=True)
            else:
                return Response(
                    {"success": False, "status": 403, "error": "You do not have permission to update apartments."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            cache.delete_pattern("public_apartments_*")
            general_logger.info("This (data=%s) for apartment (pk=%s) was updated successfully by user (%s)", serializer.data, pk, request.user)
            return Response(
                {'success': True, 'status': 200, 'message': 'Apartment updated successfully', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except Apartment.DoesNotExist:
            return Response(
                {"success": False, "status": 404, "error": "Apartment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error updating apartment (pk=%s): %s", pk, e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            general_logger.error("Exception error updating apartment (pk=%s): %s", pk, e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(request=None)
    def verify_apartment(self, request, pk=None):
        """
        Verify an apartment endpoint.

        Admins can only verify a specific apartment.
        """
        try:
            apartment = Apartment.objects.get(id=pk)
            apartment.is_verified = True
            apartment.save()
            cache.delete_pattern("public_apartments_*")
            general_logger.info("Apartment (id=%s) was verified successfully by %s", pk, request.user)
            return Response(
                {'success': True, 'status': 200, 'message': 'Apartment verified successfully'},
                status=status.HTTP_200_OK
            )
        except Apartment.DoesNotExist:
            return Response(
                {"success": False, "status": 404, "error": "Apartment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            general_logger.error("Exception error verifying apartment (id=%s): %s", pk, e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema()
    def destroy(self, request, pk=None):
        """
        Delete an apartment endpoint.

        Admins only.
        """
        try:
            apartment = Apartment.objects.get(id=pk)
            # Delete files from storage before deleting the record
            if apartment.video:
                apartment.video.delete(save=False)
            if apartment.document_file:
                apartment.document_file.delete(save=False)
            for image in ApartmentImage.objects.filter(apartment=apartment):
                if image.image:
                    image.image.delete(save=False)
            apartment.delete()
            cache.delete_pattern("public_apartments_*")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Apartment.DoesNotExist:
            return Response(
                {"success": False, "status": 404, "error": "Apartment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            general_logger.error("Exception error deleting apartment (pk=%s): %s", pk, e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
