from django.db import models

class Nodo(models.Model):
    nombre = models.CharField(max_length=120, null=True, help_text="Nombre del nodo")
    MAC = models.CharField(max_length=20, help_text="MAC del nodo")
    temperatura_min = models.IntegerField(blank=True, null=True)
    temperatura_max = models.IntegerField(blank=True, null=True)
    reenvio_correo = models.IntegerField(blank=True, null=True, default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.MAC, self.nombre)

class Sensor(models.Model):
    serial = models.CharField(max_length=120, help_text="Serial del sensor")
    nombre = models.CharField(max_length=120, null=True, help_text="Nombre del sensor")
    Nodo = models.ForeignKey(Nodo, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.serial, self.nombre)


class PuertaEstatus(models.Model):
    ESTATUS = (
        ('A', 'Abierta'),
        ('C', 'Cerrada'),
    )
    estatus = models.CharField(max_length=1, choices=ESTATUS)
    Nodo = models.ForeignKey(Nodo, null=True,on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class Registro_temperatura(models.Model):
    Sensor = models.ForeignKey(Sensor, null=True,on_delete=models.DO_NOTHING)
    Nodo = models.ForeignKey(Nodo, null=True,on_delete=models.DO_NOTHING)
    temperatura = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def fecha_registro(self):
        return self.created_at.strftime('%d/%m/%Y %H')
    def as_json(self):
        return dict(
            nodo=self.Nodo.nombre,
            temperatura=self.temperatura,
            created_at=self.created_at.strftime('%d/%m/%Y %H'))

class Correo(models.Model):
    PRIORIDAD = (
        ('1', 'Prioridad primera hora'),
        ('2', 'Prioridad segunda hora'),
        ('3', 'Prioridad tercera hora'),
    )

    prioridad = models.CharField(max_length=1, choices=PRIORIDAD, null=True)
    email = models.EmailField(max_length=254)
    nombre = models.CharField(max_length=120, help_text="Nombre del receptor")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "%s %s" % (self.email, self.nombre)


class Correo_alerta(models.Model):
    ESTATUS = (
        ('A', 'Alta'),
        ('B', 'Baja'),
    )
    tipo_alerta = models.CharField(max_length=1, choices=ESTATUS, null=True)
    Nodo = models.ForeignKey(Nodo, null=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
