from django.contrib import admin
from django.contrib.auth.models import Group
from .models import *

# Registrar en Admin
admin.site.register(Nodo)
admin.site.register(Sensor)
admin.site.register(Puerta)
admin.site.register(Correo)
admin.site.register(CorreoAlerta)
admin.site.register(RegistroTemperatura)
admin.site.register(Error)

# Eliminar del Admin
# admin.site.unregister(Group)