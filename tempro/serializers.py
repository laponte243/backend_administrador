# Rest's imports
from rest_framework import fields, serializers
# Django's imports
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils.translation import gettext as _
# Raiz
from .models import *

class RegistroTemperaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroTemperatura
        fields = '__all__'

class NodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nodo
        fields = '__all__'

class SuscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suscripcion
        fields = '__all__'