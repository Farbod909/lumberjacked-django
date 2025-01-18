"""
URL configuration for lumberjacked project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authn.urls')),
    path('browsable-api-auth/', include('rest_framework.urls')),
    path('api/', include('api.urls'))
]
