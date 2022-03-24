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

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import datetime
from django_tables2 import RequestConfig
from django_tables2.export.export import TableExport

from .tables import *
from .models import *

import json

class Round(Func):
  function = 'ROUND'
  arity = 2

@login_required()
def user_dashboard(request):
    now = datetime.now()
    earlier = now - timedelta(hours=12)
    dataset = RegistroTemperatura.objects.values('Nodo__nombre').filter(created_at__range=(earlier,now)).annotate(promedio=Round(Avg('temperatura'),2))
    categories = list()
    promedios = list()
    for entry in dataset:
        categories.append(entry['Nodo__nombre'])
        promedios.append(entry['promedio'])
    datax = []
    nodos = Nodo.objects.all()
    for nodo in nodos:
        datay = []
        registros = RegistroTemperatura.objects.filter(Nodo__id=nodo.id).values('created_at__date').annotate(
            promedio=Avg('temperatura'))
        for registro in registros:
            datay.append({'name': registro['created_at__date'], 'y': registro['promedio']})
        datax.append({
            "name": nodo.nombre,
            "data": datay
        })
    arreglo = json.dumps(datax, cls=DjangoJSONEncoder)

    return render(request, 'dashboard.html',{ 'categories': json.dumps(categories),'promedios': json.dumps(promedios),'series':arreglo})

def sign_in(request):
    msg = []
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('user_dashboard')
            else:
                msg.append('Tu cuenta esta desactivada')
    else:
        msg.append('Datos incorrectos, intenta otra vez')
    return render(request, 'login.html', {'errors': msg})


@login_required()
def registered_users(request):
    users = User.objects.all()

    context = {
        'users': users
    }
    return render(request, 'users.html', context)


@login_required()
def user_deactivate(request, user_id):
    user = User.objects.get(pk=user_id)
    user.is_active = False
    user.save()
    messages.success(request, "Cuenta desactivada de manera satisfactoria!")
    return redirect('system_users')


@login_required()
def user_activate(request, user_id):
    user = User.objects.get(pk=user_id)
    user.is_active = True
    user.save()
    messages.success(request, "Cuenta activada de manera satisfactoria!")
    return redirect('system_users')

@login_required()
def sign_up(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('system_users')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required()
def registros(request):
    table = Temp_table(RegistroTemperatura.objects.all(), order_by="-created_at")
    RequestConfig(request, paginate={"per_page": 15}).configure(table)
    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response("table.{}".format(export_format))
    return render(request, "registro_temperatura.html", {"table": table})

@login_required()
def log_puerta(request):
    table = Door_table(EstadoPuerta.objects.all(), order_by="-created_at")
    RequestConfig(request, paginate={"per_page": 15}).configure(table)
    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response("table.{}".format(export_format))
    return render(request, "log_puerta.html", {"table": table})


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
            tfha = timezone.now().replace(microsecond=0, second=0)
            if tfha.minute > 30:
                tfha = tfha.replace(minute=30)
            else:
                tfha = tfha.replace(minute=0)
            thdh = tfha-timezone.timedelta(hours=12)
            trad = [thdh,tfha]
            rudh = RegistroTemperatura.objects.filter(nodo=data['nodo'],created_at__range=trad)
            promedio = {'nodo': nodo.id, 'max':nodo.temperatura_max, 'min':nodo.temperatura_min, 'grafica':[]}
            vuelta = 0
            while vuelta < 24:
                thmh = tfha-timezone.timedelta(minutes=30)
                tram = [thmh,tfha]
                promedio['grafica'].append({'fecha': tfha.date(),'hora': tfha.time(), 'promedio':round(rudh.filter(created_at__range=tram).aggregate(promedio=Avg('temperatura'))['promedio'],4)})
                tfha = tfha-timezone.timedelta(minutes=30)
                vuelta += 1
            return Response(promedio)
        except:
            return Response('Error')
    else:
        return Response('Error al intentar encontrar el nodo')