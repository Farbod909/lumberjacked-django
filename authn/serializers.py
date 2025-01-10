from dj_rest_auth.serializers import LoginSerializer
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers


class CustomLoginSerializer(LoginSerializer):
    username = None

class CustomRegisterSerializer(RegisterSerializer):
    username = None
