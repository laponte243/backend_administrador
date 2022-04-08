# Importes de Restframework
from rest_framework import fields, serializers
# Importes de Django
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils.translation import gettext as _
# Raiz
from .models import *
""" Clases creadas para rest tempro """
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