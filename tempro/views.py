# Importes de Utiles de Django
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.shortcuts import render
from django.db.models import Avg,Func
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.core import mail, serializers as srz
from django.utils.dateformat import format
# Importes de Utiles de RestFramework
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework import authentication,viewsets,status
from rest_framework.response import Response
# Importes de Funcionalidad
from .models import *
from .serializers import * # from .telegram.constantes import *
# Importes de Utiles de python
from datetime import datetime
from telebot import *
import json
import time
# Vista rest api para los registros de temperatura 
class RegistroTemperaturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=RegistroTemperaturaSerializer
    # Metodo get en base a multiples instancias
    def update(self):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    def get_queryset(self):
        perfil=Perfil.objects.get(usuario=self.request.user)
        instancia=perfil.instancia
        if (perfil.tipo=='S'):
            return RegistroTemperatura.objects.all().order_by('-id')
        else:
            return RegistroTemperatura.objects.filter(instancia=instancia).order_by('-id')
# Vista rest api para los nodos 
class NodoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=NodoSerializer
    # Metodo get en base a multiples instancias
    def get_queryset(self):
        perfil=Perfil.objects.get(usuario=self.request.user)
        instancia=perfil.instancia
        if (perfil.tipo=='S'):
            return Nodo.objects.all().order_by('-id')
        else:
            return Nodo.objects.filter(instancia=instancia).order_by('-id')
# Vista rest api para las suscripciones 
class SuscripcionVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=SuscripcionSerializer
    # Metodo get en base a multiples instancias
    def get_queryset(self):
        perfil=Perfil.objects.get(usuario=self.request.user)
        instancia=perfil.instancia
        if (perfil.tipo=='S'):
            return Suscripcion.objects.all().order_by('-id')
        else:
            return Suscripcion.objects.filter(instancia=instancia).order_by('-id')
# Funcion para enviar mensaje por el bot de alerta
def func_alertar(info):
    try:
        # Llave del bot de telegram asociado
        API_KEY_BOT='5260903251:AAFuenEYma01kNHnm6AO9BFioGDn-cNrXEY'
        bot=telebot.TeleBot(API_KEY_BOT)
        for suscripcion in Suscripcion.objects.filter(alertar=True).values():
            bot.send_message(suscripcion['chat'],info)
    except Exception as e:
        print(e)
# Funciones para enviar correos de alerta
def correo_temperatura_alta(nodo,promedio):
    subject='Alerta de temperatura alta (Tempro)'
    html_message=render_to_string('alerta_temperatura_alta.html',{'promedio': promedio,'nodo':nodo,'fecha': datetime.now()})
    recievers=[]
    for correo in Correo.objects.all():
        recievers.append(correo.email)
    email_from=settings.EMAIL_HOST_USER
    plain_message=strip_tags(html_message)
    mail.send_mail(subject,plain_message,email_from,recievers,html_message=html_message)
    correo=CorreoAlerta(nodo=nodo,tipo_alerta='A')
    correo.save()
def correo_temperatura_baja(nodo,promedio):
    subject='Alerta de temperatura baja (Tempro)'
    html_message=render_to_string('alerta_temperatura_baja.html',{'promedio': promedio,'nodo':nodo,'fecha': datetime.now()})
    recievers=[]
    for correos in Correo.objects.all():
        recievers.append(correos.email)
    email_from=settings.EMAIL_HOST_USER
    plain_message=strip_tags(html_message)
    mail.send_mail(subject,plain_message,email_from,recievers,html_message=html_message)
    correo=CorreoAlerta(nodo=nodo,tipo_alerta='B')
    correo.save()
# Rounder
class Round(Func):
    function='ROUND'
    arity=2
# Funcion tipo vista para registrar las temperaturas
@api_view(["POST","GET"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def cambio_temp(request):
    error=False
    try:
        data=request.data
        nodo=None
        sensor=None
        instancia=None
        nodo,created=Nodo.objects.get_or_create(direccion_MAC=data['mac'])
        if created:
            instancia=Instancia.objects.all().first()
            sensor=Sensor.objects.create(nodo=nodo,serial=data['serial'])
            sensor.nombre='Sensor#%s'%(str(sensor.id))
            sensor.instancia=instancia
            sensor.save()
            nodo.nombre='Nodo#%s'%(str(nodo.id))
            sensor.instancia=instancia
            nodo.save()
        else:
            instancia=Instancia.objects.all().first()
            sensor,created=Sensor.objects.get_or_create(nodo=nodo,serial=data['serial'])
            if created:
                sensor.nombre='Sensor#%s'%(str(sensor.id))
                sensor.instancia=instancia
                sensor.save()
        if not instancia:
            instancia=Instancia.objects.get(instancia__id=nodo.instancia.id)
        registro=RegistroTemperatura.objects.create(instancia=instancia,nodo=nodo,sensor=sensor,temperatura=data['temperatura'])
        ahora=timezone.now()
        antes=ahora-timezone.timedelta(hours=1)
        rango=[antes,ahora]
        prueba=RegistroTemperatura.objects.filter(nodo=nodo,created_at__range=rango)
        recientes=prueba.aggregate(promedio=Avg('temperatura'))
    except:
        error=True
    try:
        if recientes['promedio']>nodo.temperatura_max and (registro.id%2)==0:
            # correo_temperatura_alta(nodo,recientes['promedio'])
            func_alertar('¡Temperatura alta (%sºc) en %s!'%(round(recientes['promedio'],2),nodo.nombre))
    except:
        pass
    try:
        if recientes['promedio']<nodo.temperatura_min and (registro.id%2)==0:
            # correo_temperatura_baja(nodo,recientes['promedio'])
            func_alertar('¡Temperatura baja (%sºc) en %s!'%(round(recientes['promedio'],2),nodo.nombre))
    except:
        pass
    if error:
        return Response('Error',status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(registro.values())
# Funcion tipo vista para registrar un cambio al estado de la puerta de la cava
@api_view(["POST"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def cambio_puer(request):
    try:
        data=request.data
        nodo=None
        puerta=None
        estado=None
        if (data['estado']=='0'):
            estado='C'
        else:
            estado='A'
        nodo,created=Nodo.objects.get_or_create(direccion_MAC=data['mac'])
        if created:
            instancia=Instancia.objects.all().first()
            puerta=Puerta.objects.create(nodo=nodo,estado=estado)
            puerta.save()
            nodo.nombre='Nodo#%s'%(str(nodo.id))
            nodo.save()
        else:
            puerta,created=Puerta.objects.get_or_create(nodo=nodo)
            if created:
                instancia=Instancia.objects.all().first()
            puerta.estado=estado
            puerta.save()
        return Response(puerta.values())
    except:
        return Response('Error',status=status.HTTP_400_BAD_REQUEST)
# Funcion tipo vista para registrar errores
@api_view(["POST"])
@csrf_exempt
@permission_classes([AllowAny])
def errores(request):
    data=request.data
    try:
        ahora=timezone.now()
        antes=ahora-timezone.timedelta(hours=1)
        rango=[antes,ahora]
        errores=Error.objects.filter(fecha_hora__range=rango)
        error,created=Error.objects.get_or_create(
            razon=data['error'],
            msg_mqtt=data['receive'],
            origen=data['topic'],
            nodo=data['mac'],
            sensor=data['serial'],
            temperatura=data['temperatura'],
            estado=data['estado'])
        if created:
            if data['topic']=='temperatura':
                error.origen=data['topic']
                if len(data['receive'].split('|')) != 3:
                    error.nodo='N/A'
                    error.sensor='N/A'
                    error.temperatura='N/A'
                else:
                    error.nodo=data['mac']
                    error.sensor=data['serial']
                    error.temperatura=data['temperatura']
            if data['topic']=='puerta':
                error.origen=data['topic']
                if len(data['receive'].split('|')) != 2:
                    error.nodo='N/A'
                    error.estado='N/A'
                else:
                    error.nodo=data['mac']
                    error.estado=data['estado']
            else:
                error.topic=data['topic']
            error.save()
        else:
            error.contador+=1
            error.save()
        return Response(True)
    except:
        return Response(False,status=status.HTTP_400_BAD_REQUEST)
# Funcion tipo vista para obtener los valores de las graficas
@api_view(["POST"])
@csrf_exempt
@permission_classes([AllowAny])
def obtener_grafica(request):
    data=request.data
    nodos=None
    try:
        # Para las graficas del bot
        if data['todos']=='True':
            nodos=Nodo.objects.all()
            suscripcion=Suscripcion.objects.get(chat=data['chat'])
        # Para las graficas de la pagina
        else:
            nodos=Nodo.objects.filter(id=data['nodo'])
    except:
        try:
            nodos=Nodo.objects.filter(id=data['nodo'])
        except:
            nodos=None
    # Verificar que existan el/los nodo/os
    if nodos:
        graficas=[]
        for nodo in nodos:
            ahora=timezone.now().replace(microsecond=0,second=0)
            if ahora.minute>=30:
                ahora=ahora.replace(minute=30)
            else:
                ahora=ahora.replace(minute=0)
            antes_24h=ahora-timezone.timedelta(hours=24)
            rango_mayor=[antes_24h,ahora]
            registros_nodo=RegistroTemperatura.objects.filter(nodo=nodo)
            registros=registros_nodo.filter(created_at__range=rango_mayor).order_by('created_at')
            # Verificacion para asegurar que existan suficientes registros de temperatura para crear una grafica
            if len(registros)>1:
                registro_final=registros.latest('-created_at').created_at
                promedio={'nodo': nodo.id,'nombre':nodo.nombre,'max':nodo.temperatura_max,'min':nodo.temperatura_min,'grafica':[],'ultima_hora':None,'ultima_temp':None}
                vuelta=0
                crear=True
                # Ciclo for para crear el Json
                while crear:
                    antes_30m=ahora-timezone.timedelta(minutes=30)
                    rango_menor=[antes_30m,ahora]
                    grupos=registros.filter(created_at__range=rango_menor)
                    if not grupos:
                        ahora=ahora-timezone.timedelta(minutes=30)
                        vuelta+=1
                        if vuelta==49:
                            break
                        continue
                    promedio['grafica'].append({'fecha_hora': ahora.timestamp(),'promedio':round(grupos.aggregate(promedio=Avg('temperatura'))['promedio'],4)})
                    ahora=ahora-timezone.timedelta(minutes=30)
                    vuelta+=1
                    if vuelta==49:
                        break
                try:
                    if data['todos']=='True':
                        ultima=registros_nodo.last()
                        promedio['ultima_temp']=ultima.temperatura
                        promedio['ultima_hora']=ultima.created_at
                        graficas.append(promedio)
                except:
                    return Response(promedio)
        # Verificar si el chat esta registrado
        if suscripcion:
            return Response(graficas,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response('Error al intentar encontrar el nodo',status=status.HTTP_404_NOT_FOUND)
# Funcion tipo vista para activar las alertas en los chats
@api_view(["POST"])
@csrf_exempt
@permission_classes([AllowAny])
def suscribir(request):
    try:
        data=request.data
        if data:
            suscripcion=Suscripcion.objects.get(chat=data['chat_id'])
            if data['cambiar_alertar'] != 'False':
                suscripcion.alertar=not suscripcion.alertar
                suscripcion.save()
                return Response({'cambiado_a':suscripcion.alertar},status=status.HTTP_202_ACCEPTED)
            else:
                return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
    except Exception as e:
        return Response('%s'%(e),status=status.HTTP_400_BAD_REQUEST)
# Funcion tipo vista para obtener promedio de los ultimos 3 dias
@api_view(["POST"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def promedio_tres_dias(request):
    data=request.data
    if not data:
        data['nodo']=1
    try:
        nodo=Nodo.objects.get(id=data['nodo'])
    except:
        nodo=None
    if nodo:
        try:
            ahora=timezone.now().replace(microsecond=0,second=0)
            if ahora.minute>30:
                ahora=ahora.replace(minute=30)
            else:
                ahora=ahora.replace(minute=0)
            antes_30h=ahora-timezone.timedelta(hours=30)
            rango_mayor=[antes_30h,ahora]
            registros=RegistroTemperatura.objects.filter(nodo=data['nodo'],created_at__range=rango_mayor).order_by('created_at')
            registro_final=registros.latest('-created_at').created_at
            promedio={'nodo': nodo.id,'max':nodo.temperatura_max,'min':nodo.temperatura_min,'promedios':[]}
            vuelta=0
            crear=True
            # Ciclo para crear el Json
            while crear:
                antes_30m=ahora-timezone.timedelta(minutes=30)
                rango_menor=[antes_30m,ahora]
                grupos=registros.filter(created_at__range=rango_menor)
                if not grupos:
                    break
                promedio['promedios'].append({'fecha_hora': ahora.timestamp(),'promedio':round(grupos.aggregate(promedio=Avg('temperatura'))['promedio'],4)})
                ahora=ahora-timezone.timedelta(minutes=30)
                vuelta+=1
            return Response(promedio)
        except:
            return Response('Error',status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response('Error al intentar encontrar el nodo',status=status.HTTP_400_BAD_REQUEST)