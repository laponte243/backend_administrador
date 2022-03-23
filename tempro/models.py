from django.db import models

class Nodo(models.Model):
    nombre = models.CharField(max_length=120, null=True, help_text="Nombre del nodo")
    direccion_MAC = models.CharField(max_length=20, null=False, blank=True, help_text="MAC del nodo")
    temperatura_min = models.FloatField(null=True, blank=True)
    temperatura_max = models.FloatField(null=True, blank=True)
    reenvio_correo = models.IntegerField(null=True, blank=True, default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.direccion_MAC, self.nombre)

class Sensor(models.Model):
    serial = models.CharField(max_length=120, null=False, blank=False, help_text="Serial del sensor")
    nombre = models.CharField(max_length=120, null=True, blank=False, help_text="Nombre del sensor")
    nodo = models.ForeignKey(Nodo, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.serial, self.nombre)


class Puerta(models.Model):
    ESTADO = (
        ('A', 'Abierta'),
        ('C', 'Cerrada'),
    )
    estado = models.CharField(max_length=1, null=False, blank=False, choices=ESTADO)
    nodo = models.ForeignKey(Nodo, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class RegistroTemperatura(models.Model):
    nodo = models.ForeignKey(Nodo, null=False, on_delete=models.DO_NOTHING)
    sensor = models.ForeignKey(Sensor, null=False, on_delete=models.DO_NOTHING)
    temperatura = models.FloatField(null=False, blank=False,)
    created_at = models.DateTimeField(auto_now_add=True)
    def fecha_registro(self):
        return self.created_at.strftime('%d/%m/%Y %H')
    def as_json(self):
        return dict(
            nodo=self.Nodo.nombre,
            temperatura=self.temperatura,
            created_at=self.created_at.strftime('%d/%m/%Y %H'))

class Correo(models.Model):
    # PRIORIDAD = (
    #     ('1', 'Prioridad primera hora'),
    #     ('2', 'Prioridad segunda hora'),
    #     ('3', 'Prioridad tercera hora'),
    # )
    # prioridad = models.CharField(max_length=1, null=False, choices=PRIORIDAD)
    email = models.TextField(max_length=254, null=False, blank=False)
    nombre = models.CharField(max_length=120, null=True, blank=False, help_text="Nombre del receptor")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.email, self.nombre)


class CorreoAlerta(models.Model):
    TIPO = (
        ('A', 'Alta'),
        ('B', 'Baja'),
    )
    tipo_alerta = models.CharField(max_length=1, choices=TIPO, null=True)
    nodo = models.ForeignKey(Nodo, null=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)

class Error(models.Model):
    razon = models.TextField(max_length=254, null=False)
    origen = models.TextField(max_length=254, null=False)
    msg_mqtt = models.TextField(max_length=254, null=False)
    nodo = models.CharField(max_length=254, null=True, blank=True, default='N/A')
    sensor = models.CharField(max_length=254, null=True, blank=True, default='N/A')
    estado = models.CharField(max_length=254, null=True, blank=True, default='N/A')
    temperatura = models.CharField(max_length=254, null=True, blank=True, default='N/A')
    contador = models.IntegerField(null=False, blank=False, default=1)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return "%s %s"%(self.razon, self.origen)
