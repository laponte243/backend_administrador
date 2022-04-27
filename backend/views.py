# Importes de Rest framework
from os import stat_result
import re
from rest_framework import permissions,viewsets,status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import SessionAuthentication,BasicAuthentication,TokenAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Importes de Django
from django.apps import apps
from django.db.models import *
from django.contrib.auth import *
from django.core import serializers as sr
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse,HttpResponse,request
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
# Raiz
from .serializers import *
from .models import *
from .menu import *
from .vistas import *
# Recuperar contraseña
from knox.views import LoginView as KnoxLoginView
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.template.loader import render_to_string
# Utiles
from django_renderpdf.views import PDFView
from email import header
from urllib import response
from numpy import indices
import pandas as pd
import csv
import xlwt
import requests
import datetime
import random
import string
# Acceso de KNOX
class LoginView(KnoxLoginView):
    permission_classes=(permissions.AllowAny,)
    def post(self,request,format=None):
        serializer=AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.validated_data['user']
        login(request,user)
        # return super(LoginView,self).post(request,format=None)
        temp_list=super(LoginView,self).post(request,format=None)
        temp_list.data["user_id"]=user.id
        temp_list.data["first_name"]=user.first_name
        temp_list.data["last_name"]=user.last_name
        temp_list.data["last_login"]=user.last_login
        return Response({"data": temp_list.data})
# Vista creada para el modelo de Group
class GroupVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    queryset=Group.objects.all().order_by('name')
    serializer_class=GroupMSerializer
# Vista creada para el modelo de Permission
class PermissionVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    queryset=Permission.objects.all()
    serializer_class=PermissionMSerializer
# Vista modificada para el modelo mixim de User
class UserVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=UsuarioMSerializer
    # Motodo de crear no permitido
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','escribir'):
            datos=request.data
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo == 'S' or ((perfil.tipo == 'A' or perfil.tipo == 'U') and (datos['tipo'] == 'U' or datos['tipo'] == 'V')):
                self.perform_create(serializer)
                headers=self.get_success_headers(serializer.data)
                return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodo de leer
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
            instancia=perfil.instancia
            menu=Menu.objects.get(router__contains='Usuario')
            menu_instancia=MenuInstancia.objects.get(menu__id=menu.id)
            try:
                permiso=Permiso.objects.get(instancia=instancia,perfil=perfil,menuinstancia=menu_instancia)
            except:
                permiso=Permiso(leer=False)
            if perfil.tipo=='S':
                return User.objects.all()
            elif perfil.tipo=='A':
                return User.objects.filter(perfil__instancia=instancia)
            elif perfil.tipo=='U' or perfil.tipo=='V':
                return User.objects.filter(perfil__instancia=instancia).exclude(perfil__tipo__in=['A','S']) if permiso.leer else User.objects.filter(id=self.request.user.id)
        else:
            return User.objects.none()
    # Metodo de actualizar
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','actualizar'):
            partial=True
            instance=self.get_object()
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            if perfil.tipo=='A' or perfil.tipo=='U':
                perfil_cambiar=Perfil.objects.get(usuario_id=serializer.id)
                if perfil_cambiar.tipo != 'A' and perfil_cambiar != 'S':
                    self.perform_update(serializer)
                    return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodo de eliminar
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','borrar'):
            objeto=self.get_object()
            # Super
            if perfil.tipo=='S':
                Perfil.objects.get(usuario=self.request.data.id).delete()
                objeto.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            # Admin/Usuario
            elif perfil.tipo=='A' or perfil.tipo=='U':
                # Verificar que el usuario a borrar no sea Staff,y este en la misma instancia desde donde se hace la peticion
                if objeto.perfil.tipo!='S' and objeto.perfil.tipo!='A' and str(objeto.perfil.instancia.id)==str(perfil.instancia.id) and perfil.usuario.id!=self.request.user.id:
                    Perfil.objects.get(usuario=self.request.data.id).delete()
                    objeto.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response('No tienes permitido borrar este usuario',status=status.HTTP_401_UNAUTHORIZED)
            # Vendedor
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
# Vista del modelo Modulo
class ModuloVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ModuloSerializer
    # Metodo de crear no disponible
    def create(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo de leer
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
            # Super
            if perfil.tipo=='S':
                return Modulo.objects.all().order_by('nombre')
            # Admin
            if perfil.tipo=='A':
                modulos=[]
                for m in perfil.instancia.modulo:
                    modulos.append(m)
                return modulos
            # Usuario/Vendedor
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Modulo.objects.none()
    # Metodo de actualizar no disponible
    def update(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo de eliminar no disponible
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
# Vista para el modelo Menu
class MenuVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=MenuSerializer
    # Metodo de crear no disponible
    def create(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo de leer
    def get_queryset(self):
        # Verificar si existen los menus
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            return Menu.objects.all()
        else:
            return Menu.objects.none()
    def update(self,request,*args,**kwargs):
       perfil=obt_per(self.request.user)
       if perfil.tipo=='S':
           partial=True
           instance=self.get_object()
           serializer=self.get_serializer(instance,data=request.data,partial=partial)
           serializer.is_valid(raise_exception=True)
           self.perform_update(serializer)
           return Response(serializer.data,status=status.HTTP_200_OK)
       else:
           return Response(status=status.HTTP_403_FORBIDDEN)
    # Metodo de eliminar no disponible
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
# Instancia
class InstanciaVS(viewsets.ModelViewSet):
    permission_classes=[IsAdminUser]
    authentication_classes=[TokenAuthentication]
    serializer_class=InstanciaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S' and self.request.user.is_superuser==True:
            serializer=self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        elif perfil.tipo=='S':
            return Response("Tu usuario o perfil no tienen permisos de superusuario",status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            return Instancia.objects.all().order_by('nombre')
        else:
            return Instancia.objects.none()
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            if perfil.tipo=='S':
                partial=True
            instance=self.get_object()
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
# Menus por instancia
class MenuInstanciaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=MenuInstanciaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        datos=request.data
        datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
        if perfil.tipo=='S':
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            return MenuInstancia.objects.all().order_by('id')
        elif perfil.tipo=='A':
            return MenuInstancia.objects.filter(instancia=perfil.instancia).order_by('id')
        else:
            return MenuInstancia.objects.none()
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            partial=True
            instance=self.get_object()
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        instance=self.get_object()
        if perfil.tipo=='S':
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
# Perfiles de usuarios
class PerfilVS(viewsets.ModelViewSet):
    permission_classes=[AllowAny]
    authentication_classes=[TokenAuthentication]
    serializer_class=PerfilSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','escribir'):
            datos=request.data
            datos._mutable=True
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            permisos=datos['permisos']
            datos._mutable=False
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            if (perfil.tipo=='S' or perfil.tipo=='A'):
                self.perform_create(serializer)
                permisos=guardar_permisos(permisos,serializer['id'].value,perfil)
                headers=self.get_success_headers(serializer.data)
                return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
            if perfil.tipo=='S':
                return Perfil.objects.all().order_by('usuario')
            elif perfil.tipo=='A':
                return Perfil.objects.filter(instancia=perfil.instancia).order_by('usuario')
            else:
                return Perfil.objects.filter(perfil=perfil.id)
        else:
            return Perfil.objects.none()
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','actualizar'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            if perfil.tipo=='S' or perfil.tipo=='A':
                partial=True
                instance=self.get_object()
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                try:
                    objeto=Perfil.objects.get(usuario=self.request.user)
                    objeto.avatar=request.data['avatar']
                    self.perform_update(objeto)
                    return Response(objeto,status=status.HTTP_200_OK)
                except:
                    return Response('Problema con el avatar a guardar',status=status.HTTP_202_ACCEPTED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','borrar'):
            instance=self.get_object()
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)) and instance.perfil.tipo=='A':
                    instance.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response('No puedes eliminar este perfil',status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
# Permisos de los usuarios
class PermisoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=PermisoSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','escribir'):
            datos=request.data
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
            if perfil.tipo=='S':
                return Permiso.objects.all()
            else:
                return Permiso.objects.filter(instancia=perfil.instancia)
        else:
            return Permiso.objects.none()
    def update(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','actualizar'):
            permiso=self.get_object()
            partial=True
            if permiso.perfil.instancia==perfil.instancia:
                if (permiso.perfil.tipo=='U' and perfil.tipo=='A') or (permiso.perfil.tipo=='V' and perfil.tipo=='U') or (permiso.perfil.tipo=='U' and perfil.tipo=='U' and not permiso.perfil.activo):
                    serializer=self.get_serializer(permiso,data=request.data,partial=partial)
                    serializer.is_valid(raise_exception=True)
                    self.perform_update(serializer)
                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response('El permiso pertenece a un usuario del mismo o mayor rango',status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response('No puedes cambiar los permisos de este usuario',status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','borrar'):
            permiso=self.get_object()
            if permiso.perfil.instancia==perfil.instancia:
                if ((permiso.perfil.tipo=='U' and perfil.tipo=='A') or (permiso.perfil.tipo=='V' and perfil.tipo=='U'))or(permiso.perfil.tipo=='U' and perfil.tipo=='U' and not permiso.perfil.activo):
                    permiso.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response('El permiso pertenece a un usuario del mismo o mayor rango',status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response('No puedes eliminar los permisos de este usuario',status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
# Empresas registradas de la instancia
class EmpresaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=EmpresaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','leer'):
            if perfil.tipo=='S':
                return Empresa.objects.all().order_by('nombre')
            else:
                return Empresa.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return Empresa.objects.none()
# Contactos de las empresas
class ContactoEmpresaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ContactoEmpresaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','leer'):
            if perfil.tipo=='S':
                return ContactoEmpresa.objects.all().order_by('nombre')
            else:
                return ContactoEmpresa.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return ContactoEmpresa.objects.none()
# Configuracion de papelerias
class ConfiguracionPapeleriaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ConfiguracionPapeleriaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','leer'):
            if perfil.tipo=='S':
                return ConfiguracionPapeleria.objects.all().order_by('valor','empresa')
            else:
                return ConfiguracionPapeleria.objects.filter(instancia=perfil.instancia).order_by('valor','empresa')
        else:
            return ConfiguracionPapeleria.objects.none()
# Tasas de conversiones de la instancia
class TasaConversionVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=TasaConversionSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'TasaConversion','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'TasaConversion','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'TasaConversion','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            return TasaConversion.objects.all().order_by('-id')
        else:
            return TasaConversion.objects.filter(instancia=perfil.instancia).order_by('-id')
# Impuestos registrados
class ImpuestosVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ImpuestosSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Impuesto','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Impuesto','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Impuesto','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Impuesto','leer'):
            if perfil.tipo=='S':
                return Impuestos.objects.all().order_by('nombre')
            else:
                return Impuestos.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return Impuestos.objects.none()
# Marcas registradas en la instancia
class MarcaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=MarcaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','leer'):
            if perfil.tipo=='S':
                return Marca.objects.all().order_by('nombre')
            else:
                return Marca.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return Marca.objects.none()
# Productos registrados en la instancia
class ProductoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ProductoSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['servicio','menejo_inventario','activo']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','leer'):
            if perfil.tipo=='S':
                return Producto.objects.all().order_by('id')
            else:
                return Producto.objects.filter(instancia=perfil.instancia).order_by('id')
        else:
            return Producto.objects.none()
# ImagenesP registradas en la instancia
class ProductoImagenVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ProductoImagenSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','leer'):
            if perfil.tipo=='S':
                return ProductoImagen.objects.all()
            else:
                return ProductoImagen.objects.filter(instancia=perfil.instancia)
        else:
            return ProductoImagen.objects.none()
# Almacen registrado en la instancia
class AlmacenVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=AlmacenSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Almacenes','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Almacenes','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Almacenes','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Almacenes','leer'):
            if perfil.tipo=='S':
                return Almacen.objects.all()
            else:
                return Almacen.objects.filter(instancia=perfil.instancia)
        else:
            return Almacen.objects.none()
# Movimientos del inventario registrados en el sistema
class MovimientoInventarioVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=MovimientoInventarioSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['producto','almacen']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            try:
                inventario=Inventario.objects.get(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'],lote=datos['lote'])
            except:
                inventario=None
            try:
                if inventario:
                    if datos['tipo']=='Salida':
                        datos['tipo']='S'
                        inventario.disponible-=float(datos['cantidad'])
                    elif datos['tipo']=='Entrada':
                        datos['tipo']='E'
                        inventario.disponible+=float(datos['cantidad'])
                    else:
                        Response('Tipo de movimiento no aceptado',status=status.HTTP_406_NOT_ACCEPTABLE)
                elif not inventario and datos['tipo']!='Salida':
                    datos['tipo']='E'
                    inventario=Inventario.objects.create(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'],disponible=datos['cantidad'],lote=datos['lote'],fecha_vencimiento=datos['fecha_vencimiento'])
                else:
                    return Response('Inventario no encontrado',status=status.HTTP_404_NOT_FOUND)
                inventario.save()
                datos['inventario']=inventario.id
                serializer=self.get_serializer(data=datos)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers=self.get_success_headers(serializer.data)
                return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
            except Exception as e:
                return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','leer'):
            if perfil.tipo=='S':
                return MovimientoInventario.objects.all()
            else:
                return MovimientoInventario.objects.filter(instancia=perfil.instancia)
        else:
            return MovimientoInventario.objects.none()
# Detalles del inventario registrados
class DetalleInventarioVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=InventarioSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['producto','almacen','disponible','bloqueado']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Inventario','leer'):
            if perfil.tipo=='S':
                return Inventario.objects.all().exclude(disponible=0)
            else:
                return Inventario.objects.filter(instancia=perfil.instancia).exclude(disponible=0)
        else:
            return Inventario.objects.none()
# Vendedores registrados en la instancia
class VendedorVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=VendedorSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['activo']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Vendedor','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Vendedor','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Vendedor','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Vendedor','leer'):
            if perfil.tipo=='S':
                return Vendedor.objects.all()
            else:
                return Vendedor.objects.filter(instancia=perfil.instancia)
        else:
            return Vendedor.objects.none()
# Clientes registrados en la instancia
class ClienteVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ClienteSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['activo']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia.id!=perfil.instancia.id:
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','leer'):
            if perfil.tipo=='S':
                return Cliente.objects.all().order_by('nombre')
            else:
                return Cliente.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return Cliente.objects.none()
# Contactos de los clientes de la instancias
class ContactoClienteVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ContactoClienteSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Cliente','leer'):
            if perfil.tipo=='S':
                return ContactoCliente.objects.all()
            else:
                return ContactoCliente.objects.filter(instancia=perfil.instancia)
        else:
            return ContactoCliente.objects.none()
# Pedidos registrados en la instancia
class PedidoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=PedidoSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','leer'):
            if perfil.tipo=='S':
                return Pedido.objects.all().order_by('-id')
            else:
                return Pedido.objects.filter(instancia=perfil.instancia).order_by('-id')
        else:
            return Pedido.objects.none()
# Detalles de los pedidos
class DetallePedidoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=DetallePedidoSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['pedido']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','borrar'):
            instance=self.get_object()
            inventario=Inventario.objects.get(id=instance.inventario.id)
            inventario.bloqueado=inventario.bloqueado-instance.cantidada
            inventario.disponible=inventario.disponible+instance.cantidada
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                inventario.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','leer'):
            if perfil.tipo=='S':
                return DetallePedido.objects.all()
            else:
                return DetallePedido.objects.filter(instancia=perfil.instancia)
        else:
            return DetallePedido.objects.none()
# Proformas registrados en la instancia
class ProformaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ProformaSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['cliente']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                DetalleProforma.objects.filter(proforma=instance.id).delete()
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','leer'):
            if perfil.tipo=='S':
                return Proforma.objects.all().order_by('-id')
            else:
                return Proforma.objects.filter(instancia=perfil.instancia).order_by('-id')
        else:
            return Proforma.objects.none()
# Detalles de las proformas de la instancia
class DetalleProformaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=DetalleProformaSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['proforma']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','borrar'):
            instance=self.get_object()
            inventario=Inventario.objects.get(id=instance.inventario.id)
            inventario.disponible=inventario.disponible+instance.cantidada
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                inventario.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','leer'):
            if perfil.tipo=='S':
                return DetalleProforma.objects.all()
            else:
                return DetalleProforma.objects.filter(instancia=perfil.instancia)
        else:
            return DetalleProforma.objects.none()
# Notas de pago
class NotaPagoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=NotaPagoMSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','leer'):
            if perfil.tipo=='S':
                return NotasPago.objects.all()
            else:
                return NotasPago.objects.filter(instancia=perfil.instancia)
        else:
            return NotasPago.objects.none()
# Detalles de las notas de pago de la instancia
class DetalleNotaPagoVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=DetalleNotaPagoMSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['notapago']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','leer'):
            if perfil.tipo=='S':
                return DetalleNotasPago.objects.all()
            else:
                return DetalleNotasPago.objects.filter(instancia=perfil.instancia)
        else:
            return DetalleNotasPago.objects.none()
# Facturas registradas en la instancia
class FacturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=FacturaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','leer'):
            if perfil.tipo=='S':
                return Factura.objects.all()
            else:
                return Factura.objects.filter(instancia=perfil.instancia)
        else:
            return Factura.objects.none()
# Detalles de las facturas de la instancia
class DetalleFacturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=DetalleFacturaSerializer
    filter_backends=[DjangoFilterBackend]
    filterset_fields=['factura']
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','leer'):
            if perfil.tipo=='S':
                return DetalleFactura.objects.all()
            else:
                return DetalleFactura.objects.filter(instancia=perfil.instancia)
        else:
            return DetalleFactura.objects.none()
# Impuestos en las facturas de la instancia
class ImpuestosFacturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ImpuestosFacturaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','leer'):
            if perfil.tipo=='S':
                return ImpuestosFactura.objects.all().order_by('nombre')
            else:
                return ImpuestosFactura.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return ImpuestosFactura.objects.none()
# Numerologia de las facturas de la instancia
class NumerologiaFacturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=NumerologiaFacturaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','leer'):
            if perfil.tipo=='S':
                return NumerologiaFactura.objects.all().order_by('tipo','valor')
            else:
                return NumerologiaFactura.objects.filter(instancia=perfil.instancia).order_by('tipo','valor')
        else:
            return NumerologiaFactura.objects.none()
# Notas de las facturas de la instancia
class NotaFacturaVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=NotaFacturaSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','leer'):
            if perfil.tipo=='S':
                return NotaFactura.objects.all()
            else:
                return NotaFactura.objects.filter(instancia=perfil.instancia)
        else:
            return NotaFactura.objects.none()
# Proveedores registrados en la instancia
class ProveedorVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=ProveedorSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proveedor','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proveedor','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proveedor','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proveedor','leer'):
            if perfil.tipo=='S':
                return Proveedor.objects.all().order_by('nombre')
            else:
                return Proveedor.objects.filter(instancia=perfil.instancia).order_by('nombre')
        else:
            return Proveedor.objects.none()
# Compras registradas en la instancia
class CompraVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=CompraSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','leer'):
            if perfil.tipo=='S':
                return Compra.objects.all().order_by('empresa','Proveedor','total')
            else:
                return Compra.objects.filter(instancia=perfil.instancia).order_by('empresa','Proveedor','total')
        else:
            return Compra.objects.none()
# Detalle de las compras
class DetalleCompraVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=DetalleCompraSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','leer'):
            if perfil.tipo=='S':
                return DetalleCompra.objects.all().order_by('compra','producto','cantidad','precio')
            else:
                return DetalleCompra.objects.filter(instancia=perfil.instancia).order_by('compra','producto','cantidad','precio')
        else:
            return DetalleCompra.objects.none()
# Notas de las compras de la intancia
class NotaCompraVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    serializer_class=NotaCompraSerializer
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','actualizar'):
            partial=True
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                serializer=self.get_serializer(instance,data=request.data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Compra','leer'):
            if perfil.tipo=='S':
                return NotaCompra.objects.all().order_by('compra')
            else:
                return NotaCompra.objects.filter(instancia=perfil.instancia).order_by('compra')
        else:
            return NotaCompra.objects.none()
""" PDFs """
# Generar pagina tipo PDF para pedidos
class PedidoPDF(PDFView):
    template_name='pedido.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        try:
            perfil=Perfil.objects.get(usuario=self.request.user)
        except Exception as e:
            self.template_name='forbidden.html'
            return {}
        # Definicion de contenido extra para el template
        context=super().get_context_data(*args,**kwargs)
        pedido=Pedido.objects.get(id=kwargs['id_pedido'])
        value={'data':[]}
        agrupador=DetallePedido.objects.filter(pedido=pedido).values('producto').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
        # Ciclo para generar Json y data para el template
        for dato in agrupador:
            productox=Producto.objects.get(id=dato['producto'])
            valuex={'datax':[]}
            total_cantidad=0
            mostrar=True
            detallado=DetallePedido.objects.filter(pedido=pedido,producto=productox).order_by('producto__id')
            if productox.lote==True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += detalle.cantidada
            elif productox.lote==True and len(detallado)==1:
                valuex['datax']=''
                mostrar=False
                for detalle in detallado:
                    valuex['datax']=detalle.lote
                    total_cantidad += detalle.cantidada
            else:
                mostrar=False
                for detalle in detallado:
                    total_cantidad += detalle.cantidada
                valuex['datax']=None
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad})
        # Setear los valores al template
        context['productos']=value['data']
        context['pedido']=pedido
        return context
# Generar pagina tipo PDF para proformas
class ProformaPDF(PDFView):
    template_name='proforma.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        # Definicion de contenido extra para el template
        context=super().get_context_data(*args,**kwargs)
        proforma=Proforma.objects.get(id=kwargs['id_proforma'])
        total_costo=float(proforma.total)
        value={'data':[]}
        total_calculado=0
        agrupador=DetalleProforma.objects.filter(proforma=proforma).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
        # Ciclo para generar Json y data para el template
        for dato in agrupador:
            productox=Producto.objects.get(id=dato['producto'])
            valuex={'datax':[]}
            total_cantidad=0
            precio_unidad=0
            costo_total=0
            mostrar=True
            detallado=DetalleProforma.objects.filter(proforma=proforma,producto=productox).order_by('producto__id')
            if productox.lote==True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += detalle.cantidada
                    precio_unidad=detalle.precio
            elif productox.lote==True and len(detallado)==1:
                valuex['datax']=''
                mostrar=False
                for detalle in detallado:
                    valuex['datax']=detalle.lote
                    total_cantidad += detalle.cantidada
                    precio_unidad=detalle.precio
            else:
                mostrar=False
                for detalle in detallado:
                    total_cantidad += detalle.cantidada
                    precio_unidad=detalle.precio
                valuex['datax']=None
            costo_total=float(precio_unidad) * float(total_cantidad)
            total_calculado += round(costo_total,2)
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':precio_unidad,'total_producto':round(costo_total,2)})
        # Setear los valores al template
        context['productos']=value['data']
        if (float(total_calculado)==float(total_costo)):
            context['total']=total_calculado
        else:
            context['total']='Error'
        context['proforma']=proforma
        return context
# Generar pagina tipo PDF para facturas
class FacturaPDF(PDFView):
    template_name='factura.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        # Definicion de contenido extra para el template
        conversion=None
        try:
            conversion=TasaConversion.objects.filter(fecha_tasa__date=datetime.datetime.today().date()).latest('fecha_tasa__date')
        except:
            conversion=TasaConversion.objects.latest('fecha_tasa')
        context=super().get_context_data(*args,**kwargs)
        factura=Factura.objects.get(id=kwargs['id_factura'])
        subtotal=float(factura.subtotal)
        total_costo=round(float(factura.total) * conversion.valor,2)
        value={'data':[]}
        total_calculado=0
        # Ciclo para generar Json y data para el template
        for dato in DetalleFactura.objects.filter(factura=factura).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada')):
            productox=Producto.objects.get(id=dato['producto'])
            valuex={'datax':[]}
            total_cantidad=0
            precio_unidad=0.0
            costo_total=0.0
            mostrar=True
            detallado=DetalleFactura.objects.filter(factura=factura,producto=productox).order_by('producto__id')
            if productox.lote==True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += int(detalle.cantidada)
                    precio_unidad=float(detalle.precio) * conversion.valor
            elif productox.lote==True and len(detallado)==1:
                valuex['datax']=''
                mostrar=False
                for detalle in detallado:
                    valuex['datax']=detalle.lote
                    total_cantidad += int(detalle.cantidada)
                    precio_unidad=float(detalle.precio) * conversion.valor
            else:
                mostrar=False
                for detalle in detallado:
                    total_cantidad += int(detalle.cantidada)
                    precio_unidad=float(detalle.precio) * conversion.valor
                valuex['datax']=None
            costo_total=precio_unidad * float(total_cantidad)
            total_calculado += costo_total
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':precio_unidad,'total_producto':round(costo_total,2)})
        subtotal_conversion=subtotal * conversion.valor
        # Setear los valores al template
        context['productos']=value['data']
        if (float(total_calculado)==float(subtotal_conversion)):
            context['subtotal']=subtotal_conversion
            context['total']=total_costo
        else:
            context['subtotal']='Error'
            context['total']='Error'
        context['factura']=factura
        return context
# Generar pagina tipo PDF para notas de pago
class NotaPagoPDF(PDFView):
    template_name='notapago.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        # Definicion de contenido extra para el template
        conversion=None
        try:
            conversion=TasaConversion.objects.filter(fecha_tasa__date=datetime.datetime.today().date()).latest('fecha_tasa__date')
        except:
            conversion=TasaConversion.objects.latest('-fecha_tasa')
        context=super().get_context_data(*args,**kwargs)
        notapago=NotasPago.objects.get(id=kwargs['id_notapago'])
        total_costo=round(float(notapago.total) * conversion.valor,2)
        value={'data':[]}
        total_calculado=0
        # Setear los valores al template
        detalles=DetalleNotasPago.objects.filter(notapago_id=notapago.id).order_by('id')
        reduccion_total=0
        for detalle in detalles:
            reduccion_total=reduccion_total+detalle.monto
        context['detalles']=detalles
        context['reduccion_total']=reduccion_total
        context['notapago']=notapago
        return context
