from django.contrib import admin
from django.contrib.auth.models import Group
from .models import Nodo, Sensor, Correo, Correo_alerta, Registro_temperatura, PuertaEstatus # Comentario angel: Deberia ser "import *"

admin.site.register(Nodo)
admin.site.register(Sensor)
admin.site.register(Correo)
admin.site.register(Correo_alerta)
admin.site.register(Registro_temperatura)
admin.site.register(PuertaEstatus)

admin.site.unregister(Group)
