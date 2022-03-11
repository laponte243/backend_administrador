from datetime import timedelta, datetime
import paho.mqtt.client as mqtt
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Nodo, Sensor, Registro_temperatura, PuertaEstatus, Correo_alerta, Correo
from django.conf import settings
from django.db.models import Avg, Func, Count

broker = "localhost"

class Round(Func):
  function = 'ROUND'
  arity = 2


def on_message(client, userdata, msg):

    data = str(msg.payload.decode("utf-8")).split('|')
    try:
        nodo = Nodo.objects.get(MAC=data[0])
    except Nodo.DoesNotExist:
        nodo = Nodo(MAC=data[0])
        nodo.save()
    if msg.topic == "mensajes/temperatura" and data[2] != '-127' :
        try:
            nodo = Nodo.objects.get(MAC=data[0])
            sensor = Sensor.objects.get(serial=data[1])
            registro = Registro_temperatura(Nodo=nodo, Sensor=sensor, temperatura=data[2])
            registro.save()
            now = datetime.now()
            earlier = now - timedelta(hours=1)
            dataset = Registro_temperatura.objects.filter(created_at__range=(earlier, now)).aggregate(promedio=Round(Avg('temperatura'), 2))
            cantidad_envios = Correo_alerta.objects.filter(Nodo__id=nodo.id,created_at__range=(earlier, now)).aggregate(conteo=Count('id'))
            if cantidad_envios['conteo'] == 0:
                diff = 10000
            else:
                ultimo_envio = Correo_alerta.objects.filter(Nodo__id=nodo.id).values('created_at').order_by('-id')[0]
                diff = (now - ultimo_envio['created_at']).total_seconds() / 60.0
            if diff >= nodo.reenvio_correo:
                if dataset['promedio'] > nodo.temperatura_max:
                    correo_temperatura_alta(nodo,dataset['promedio'],cantidad_envios=cantidad_envios['conteo'])

                if dataset['promedio'] < nodo.temperatura_min:
                    correo_temperatura_baja(nodo,dataset['promedio'],cantidad_envios=cantidad_envios['conteo'])

        except Sensor.DoesNotExist:
            nodo = Nodo.objects.get(MAC=data[0])
            sensor = Sensor(serial=data[1],Nodo=nodo)
            sensor.save()
            # Comentario de Angel: Deberia de agregar el Nombre como 'Termocupla/"serial" ("id")'
            registro = Registro_temperatura(Nodo=nodo, Sensor=sensor, temperatura=data[2])
            registro.save()

    if msg.topic == "mensajes/puerta":
        try:
            nodo = Nodo.objects.get(MAC=data[0])
            Estatus = ''
            if (data[1] == '0'):
                Estatus = 'C'
            else:
                Estatus = 'A'
            registro_puerta = PuertaEstatus(estatus=Estatus, Nodo=nodo)
            registro_puerta.save()
        except Nodo.DoesNotExist:
            nodo = Nodo(MAC=data[0])
            nodo.save()
    pass

def correo_temperatura_alta(Nodo, promedio,cantidad_envios):
    subject = 'Alerta de temperatura alta (Tempro)'
    html_message = render_to_string('alerta_temperatura_alta.html', {'promedio': promedio,'nodo':Nodo,'fecha': datetime.now()})
    prioridad = []
    if cantidad_envios <= 3:
        prioridad.append(1)
    if cantidad_envios > 3:
        prioridad.append(1)
        prioridad.append(2)
    if cantidad_envios >= 6:
        prioridad.append(3)
    recievers = []
    for correos in Correo.objects.filter(prioridad__in=prioridad):
        recievers.append(correos.email)
    email_from = settings.EMAIL_HOST_USER
    plain_message = strip_tags(html_message)
    mail.send_mail(subject, plain_message, email_from, recievers, html_message=html_message)
    correo = Correo_alerta(Nodo=Nodo, tipo_alerta='A')
    correo.save()


def correo_temperatura_baja(Nodo, promedio, cantidad_envios):
    subject = 'Alerta de temperatura baja (Tempro)'
    html_message = render_to_string('alerta_temperatura_baja.html', {'promedio': promedio,'nodo':Nodo,'fecha': datetime.now()})
    prioridad = []
    if cantidad_envios <= 3:
        prioridad.append(1)
    if cantidad_envios > 3:
        prioridad.append(1)
        prioridad.append(2)
    if cantidad_envios >= 6:
        prioridad.append(3)
    recievers = []
    for correos in Correo.objects.filter(prioridad__in=prioridad):
        recievers.append(correos.email)
    email_from = settings.EMAIL_HOST_USER
    plain_message = strip_tags(html_message)
    mail.send_mail(subject, plain_message, email_from,recievers, html_message=html_message)
    correo = Correo_alerta(Nodo=Nodo, tipo_alerta='B')
    correo.save()

client = mqtt.Client()
client.on_message = on_message
client.connect(broker)
client.subscribe("mensajes/temperatura")
client.subscribe("mensajes/puerta")
