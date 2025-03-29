"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import authentication.urls

# Swagger UI
schema_view = get_schema_view(
   openapi.Info(
      title="Dwelling Bloom API",
      default_version='v1',
      description="Dwelling Bloom is a real estate platform designed to simplify the process of renting or buying properties in Nigeria eliminating the fraudulent agent and uneccessary fees. This API provides the backend infrastructure necessary for user authentication, property management, interaction with a database of available properties, and payment.",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(name="Peter Oyelegbin", url="https://peteroyelegbin.com.ng", email="info@peteroyelegbin.com.ng"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API DOCS URL
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API URLS
    path('api/v1/', include(authentication.urls)),
]
