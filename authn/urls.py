"""
URL configuration for authn app.
"""
from django.urls import path, include

from .views import GoogleLogin, GoogleLoginCallback

urlpatterns = [
    path('', include('dj_rest_auth.urls')),
    path('registration/', include('dj_rest_auth.registration.urls')),
    path('google/', GoogleLogin.as_view(), name="google_login"),
    path('google/callback/', GoogleLoginCallback.as_view(), name="google_login_callback"),
]
