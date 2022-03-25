from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.db.models import Avg, Func, Count
from django.contrib.auth.models import User
from django.utils.html import strip_tags
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core import mail
from django.core import serializers
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework import authentication, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import datetime
from django_tables2 import RequestConfig
from django_tables2.export.export import TableExport

from .tables import *
from .models import *
from .serializers import *

import json
from django.utils.dateformat import format

class RegistroTemperaturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    hoy = timezone.now()
    dias = hoy-timezone.timedelta(days=3)
    rango = [dias,hoy]
    queryset = RegistroTemperatura.objects.filter(created_at__range=rango).order_by('-id')
    serializer_class = RegistroTemperaturaSerializer

class NodoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    queryset = Nodo.objects.all()
    serializer_class = NodoSerializer

# class NodoVS(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     # authentication_classes = [TokenAuthentication]
#     queryset = Nodo.objects.all()
#     serializer_class = NodoSerializer

def correo_temperatura_alta(nodo, promedio):
    subject = 'Alerta de temperatura alta (Tempro)'
    html_message = render_to_string('alerta_temperatura_alta.html', {'promedio': promedio,'nodo':nodo,'fecha': datetime.now()})
    recievers = []
    for correo in Correo.objects.all():
        recievers.append(correo.email)
    email_from = settings.EMAIL_HOST_USER
    plain_message = strip_tags(html_message)
    mail.send_mail(subject, plain_message, email_from, recievers, html_message=html_message)
    correo = CorreoAlerta(nodo=nodo, tipo_alerta='A')
    correo.save()


def correo_temperatura_baja(nodo, promedio):
    subject = 'Alerta de temperatura baja (Tempro)'
    html_message = render_to_string('alerta_temperatura_baja.html', {'promedio': promedio,'nodo':nodo,'fecha': datetime.now()})
    recievers = []
    for correos in Correo.objects.all():
        recievers.append(correos.email)
    email_from = settings.EMAIL_HOST_USER
    plain_message = strip_tags(html_message)
    mail.send_mail(subject, plain_message, email_from,recievers, html_message=html_message)
    correo = CorreoAlerta(nodo=nodo, tipo_alerta='B')
    correo.save()

class Round(Func):
  function = 'ROUND'
  arity = 2

@api_view(["POST", "GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def cambio_temp(request): # , MAC, serial, temperatura
    error = False
    try:
        data = request.data
        nodo = None
        sensor = None
        nodo, created = Nodo.objects.get_or_create(direccion_MAC=data['mac'])
        if created:
            sensor = Sensor.objects.create(nodo=nodo, serial=data['serial'])
            sensor.nombre = 'Sensor#%s'%(str(sensor.id))
            sensor.save()
            nodo.nombre = 'Nodo#%s'%(str(nodo.id))
            nodo.save()
        else:
            sensor, created = Sensor.objects.get_or_create(nodo=nodo, serial=data['serial'])
            if created:
                sensor.nombre = 'Sensor#%s'%(str(sensor.id))
                sensor.save()
        registro = RegistroTemperatura.objects.create(nodo=nodo,sensor=sensor,temperatura=data['temperatura'])
        ahora = timezone.now()
        antes = ahora-timezone.timedelta(hours=1)
        rango = [antes,ahora]
        prueba = RegistroTemperatura.objects.filter(nodo=nodo,sensor=sensor,created_at__range=rango)
        recientes = prueba.aggregate(promedio=Avg('temperatura'))
    except:
        error = True
    try:
        if recientes['promedio'] > nodo.temperatura_max:
            correo_temperatura_alta(nodo,recientes['promedio'])
    except:
        pass
    try:
        if recientes['promedio'] < nodo.temperatura_min:
            correo_temperatura_baja(nodo,recientes['promedio'])
    except:
        pass
    if error:
        return Response('Error')
    else:
        return Response(registro.values())

@api_view(["POST", "GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def cambio_puer(request):
    try:
        data = request.data
        nodo = None
        puerta = None
        estado = None
        if (data['estado'] == '0'):
            estado = 'C'
        else:
            estado = 'A'
        nodo, created = Nodo.objects.get_or_create(direccion_MAC=data['mac'])
        if created:
            puerta = Puerta.objects.create(nodo=nodo, estado=estado)
            puerta.save()
            nodo.nombre = 'Nodo#%s'%(str(nodo.id))
            nodo.save()
        else:
            puerta, created = Puerta.objects.get_or_create(nodo=nodo)
            puerta.estado = estado
            puerta.save()
        return Response(puerta.values())
    except:
        return Response('Error')


@api_view(["POST", "GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def errores(request):
    data = request.data
    try:
        ahora = timezone.now()
        antes = ahora-timezone.timedelta(hours=1)
        rango = [antes,ahora]
        errores = Error.objects.filter(fecha_hora__range=rango)
        error, created = Error.objects.get_or_create(
            razon=data['error'],
            msg_mqtt=data['receive'],
            origen=data['topic'],
            nodo=data['mac'],
            sensor=data['serial'],
            temperatura=data['temperatura'],
            estado=data['estado'])
        if created:
            if data['topic'] == 'temperatura':
                error.origen = data['topic']
                if len(data['receive'].split('|')) != 3:
                    error.nodo = 'N/A'
                    error.sensor = 'N/A'
                    error.temperatura = 'N/A'
                else:
                    error.nodo = data['mac']
                    error.sensor = data['serial']
                    error.temperatura = data['temperatura']
            if data['topic'] == 'puerta':
                error.origen = data['topic']
                if len(data['receive'].split('|')) != 2:
                    error.nodo = 'N/A'
                    error.estado = 'N/A'
                else:
                    error.nodo = data['mac']
                    error.estado = data['estado']
            else:
                error.topic = data['topic']
            error.save()
        else:
            print('Error reicidente')
            error.contador += 1
            error.save()
        return Response(True)
    except:
        return Response(False)

@api_view(["POST", "GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def obtener_grafica(request):
    data = request.data
    if not data:
        data['nodo'] = 1
    try:
        nodo = Nodo.objects.get(id=data['nodo'])
    except:
        nodo = None
    if nodo:
        try:
            ahora = timezone.now().replace(microsecond=0, second=0)
            if ahora.minute > 30:
                ahora = ahora.replace(minute=30)
            else:
                ahora = ahora.replace(minute=0)
            antes_12 = ahora-timezone.timedelta(hours=12)
            rango_mayor = [antes_12,ahora]
            registros = RegistroTemperatura.objects.filter(nodo=data['nodo'],created_at__range=rango_mayor).order_by('created_at')
            registro_final = registros.latest('-created_at').created_at
            promedio = {'nodo': nodo.id, 'max':nodo.temperatura_max, 'min':nodo.temperatura_min, 'grafica':[]}
            vuelta = 0
            crear = True
            while crear:
                antes_30 = ahora-timezone.timedelta(minutes=30)
                rango_menor = [antes_30,ahora]
                grupos = registros.filter(created_at__range=rango_menor)
                if not grupos:
                    break
                promedio['grafica'].append({'fecha_hora': ahora.timestamp(), 'promedio':round(grupos.aggregate(promedio=Avg('temperatura'))['promedio'],4)})
                ahora = ahora-timezone.timedelta(minutes=30)
                vuelta += 1
            return Response(promedio)
        except:
            return Response('Error')
    else:
        return Response('Error al intentar encontrar el nodo')