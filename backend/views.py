# Importes de Rest framework
import re
from rest_framework import permissions
from rest_framework import viewsets,status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import SessionAuthentication,BasicAuthentication,TokenAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Importes de Django
from django.apps import apps
from django.db.models import Count,Q,Sum
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
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
            if perfil.tipo == 'S':
                self.perform_create(serializer)
                headers=self.get_success_headers(serializer.data)
                return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
            elif (perfil.tipo == 'A' or perfil.tipo == 'U') and (datos['tipo'] == 'U' or datos['tipo'] == 'V'):
                self.perform_create(serializer)
                headers=self.get_success_headers(serializer.data)
                return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
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
    permission_classes=[IsAdminUser,IsAuthenticated]
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
                guardar_permisos(permisos,serializer['id'].value,perfil)
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
                    self.perform_update(serializer)
                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','borrar'):
            instance=self.get_object()
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
                    instance.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
                    self.perform_update(serializer)
                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Empresa','borrar'):
            instance=self.get_object()
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
                    instance.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
                    instance.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'TasaConversion','leer'):
            if perfil.tipo=='S':
                return TasaConversion.objects.all().order_by('-id')
            else:
                return TasaConversion.objects.filter(instancia=perfil.instancia)
        else:
            return TasaConversion.objects.none()
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
                print(e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Producto','actualizar'):
            partial=True
            instance=self.get_object()
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
        print(verificar_permiso(perfil,'Cliente','escribir'))
        if verificar_permiso(perfil,'Cliente','escribir'):
            datos=request.data
            try:
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                inventario.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                DetalleProforma.objects.filter(proforma=instance.id).delete()
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                inventario.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
                    self.perform_update(serializer)
                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_403_FORBIDDEN)
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','borrar'):
            instance=self.get_object()
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
                datos['instancia']=request.data['instancia']
            except:
                request.data['instancia']=None
            datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
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
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if perfil.tipo=='S':
                self.perform_update(serializer)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                if (str(request.data['instancia'])==str(perfil.instancia.id)):
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
            if perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if (str(instance.instancia.id)==str(perfil.instancia.id)):
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
""" Funciones y funciones tipo vistas """
# Reseteo de contraseña
@receiver(reset_password_token_created)
def password_reset_token_created(sender,instance,reset_password_token,*args,**kwargs):
    RESET_PASSWORD_ROUTE=getattr(settings,"RESET_PASSWORD_ROUTE",None)
    # email_plaintext_message="{}?token={}".format(reverse('password_reset:reset-password-request'),reset_password_token.key)
    context=({"url": RESET_PASSWORD_ROUTE+'#/passwordset?token='+reset_password_token.key})
    resetPasswordTemplate='user_reset_password.html'
    reset_password_message=render_to_string(resetPasswordTemplate,context)
    # Send email
    subject,from_email,to="Password Reset for {title}".format(title="DataVisualizer"),'noreply@somehost.local',reset_password_token.user.email
    text_content=''
    html_content=reset_password_message
    msg=EmailMessage(subject,html_content,from_email,[to])
    msg.content_subtype="html"  # Main content is now text/html
    msg.send()
# Funcion tipo vista para obtener objetos del inventario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def inventario(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Inventario','leer'):
        if perfil:
            inventarios=Inventario.objects.filter(instancia=perfil.instancia)
            for o in inventarios:
                if o.disponible==0 and o.bloqueado==0:
                    inventarios=inventarios.exclude(id=o.id)
            inventarios=inventarios.values('almacen','almacen__nombre','producto','producto__nombre').annotate(sum_disponible=Sum('disponible'),sum_bloqueado=Sum('bloqueado'))
            return Response(inventarios,status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para crear un nuevo usuario
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def crear_nuevo_usuario(request):
    datos=request.data
    try:
        perfil_creador=Perfil.objects.get(usuario=request.user)
        usuario=User.objects.filter(email=datos['email'])
        if (usuario):
            return Response("Ya hay un usuario con el mismo correo",status=status.HTTP_400_BAD_REQUEST)
        elif datos['tipo']=='A' and perfil_creador.tipo=='S':
            return crear_admin(datos)
        elif perfil_creador.tipo=='A' or perfil_creador.tipo=='S' or verificar_permiso(perfil_creador,'Usuarios_y_permisos','escribir'):
            datos['instancia']=obtener_instancia(perfil_creador,request.datos['instancia'])
            user=User(username=datos['username'],email=datos['email'],password=generar_clave())
            user.save()
            perfil_nuevo=Perfil(usuario=user,instancia=datos['instancia'],tipo=datos['tipo'])
            if perfil_creador.tipo=='S':
                perfil_nuevo.save()
                permisos=datos['permisos']
                guardar_permisos(permisos,perfil_nuevo.id,perfil_creador)
                if perfil_nuevo.id:
                    return Response(status=status.HTTP_201_CREATED)
                else:
                    return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif perfil_creador.tipo=='A':
                if datos['tipo']=="U" or datos['tipo']=="V":
                    # Instancia igual a la instancia del perfil del usuario que hace la peticion (instancia=perfil_c.instancia)     
                    perfil_nuevo.save()
                    permisos=datos['permisos']
                    guardar_permisos(permisos,perfil_nuevo.id,perfil_creador)
                    if perfil_nuevo.id:
                        return Response(status=status.HTTP_201_CREATED)
                    else:
                        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener el menu de la pagina segun el perfil, los permisos y la intancia del usuario
@api_view(["GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def obtener_menu(request):
    menus={ 'router': 'root','children': []}
    usuario=request.user
    def VerificarHijos(objetoPadre):
        if (MenuInstancia.objects.filter(parent=objetoPadre.id).count() > 0 or Menu.objects.filter(parent=objetoPadre.id).count() > 0):
            return True
        else:
            return False
    if usuario.perfil.tipo=="S":
        primeros=Menu.objects.filter(parent=None).order_by('orden')
        for p in primeros:
            if VerificarHijos(p):
                primero={ 'router': '','children': []}
                primero['router']=p.router.replace('-','')
                for s in Menu.objects.filter(parent=p.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo={ 'router': '','children': []}
                        segundo['router']=s.router
                        for t in Menu.objects.filter(parent=s.id).order_by('orden'):
                            tercero=t.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo=s.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero=p.router
                menus['children'].append(primero)
        return Response([menus])
    elif usuario.perfil.tipo=="A" or usuario.perfil.tipo=="U" or usuario.perfil.tipo=="V":
        instancia=usuario.perfil.instancia
        perfil=Perfil.objects.get(usuario=usuario)
        lista=obtener_padres(perfil)
        disponibles=MenuInstancia.objects.filter(instancia=instancia,id__in=lista)
        primeros=disponibles.filter(parent=None).order_by('orden')
        for primer in primeros:
            if VerificarHijos(primer):
                primero={ 'router': '','children': []}
                nombrePrimero=primer.menu.router
                primero['router']=nombrePrimero.replace('-','')
                for s in disponibles.filter(parent=primer.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo={ 'router': '','children': []}
                        nombreSegundo=s.menu.router
                        segundo['router']=nombreSegundo
                        for t in disponibles.filter(parent=s.id).order_by('orden'):
                            tercero=t.menu.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo=s.menu.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero=primer.menu.router
                menus['children'].append(primero)
        return Response([menus])
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
# Funcion para obtener las columnas 
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def obtener_columnas(request):
    data=json.loads(request.body)
    columnas=[]
    try:
        for f in eval(data['value'])._meta.get_fields():
            JsonCol={
                'select': False,
                'title': f.name.capitalize(),
                'dataIndex': f.name,
                'align': 'left'
            }
            columnas.append(JsonCol)
        return Response(columnas)
    except ObjectDoesNotExist as e:
        return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def borrar_nota(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Notasdepago','borrar'):
        payload=json.loads(request.body)
        try:
            nota=NotasPago.objects.get(id=payload['idnota'])
            for obj in DetalleNotasPago.objects.filter(notapago=nota):
                proforma=Proforma.objects.get(id=obj.proforma.id)
                proforma.saldo_proforma=float(proforma.saldo_proforma)+float(obj.monto)
                proforma.save()
                obj.delete()
            nota.delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar las notas de pago
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_nota(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Notasdepago','actualizar'):
        payload=json.loads(request.body)
        try:
            for obj in payload['data']:
                try:
                    if obj['monto'] > 0:
                        DetalleNotasPago.objects.filter(proforma=obj['proforma']).delete()
                        proforma=Proforma.objects.get(id=obj['proforma'])
                        perfil=Perfil.objects.get(usuario=request.user)
                        instancia=Instancia.objects.get(perfil=perfil.id)
                        nota_pago=NotasPago.objects.get(id=payload['idnota'])
                        detalle_nota=DetalleNotasPago(instancia=instancia,proforma=proforma,notapago=nota_pago,monto=obj['monto'],saldo_anterior=obj['saldo_anterior'])
                        detalle_nota.save()
                        proforma.saldo_proforma=proforma.saldo_proforma - detalle_nota.monto
                        proforma.save()
                except Exception as e:  
                    pass
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar los pedidos de la instancia
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_pedido(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Pedido','actualizar'):
        payload=json.loads(request.body)
        try:
            pedido_id=Pedido.objects.get(id=payload['idpedido'])
            detashepedido=DetallePedido.objects.filter(pedido=pedido_id)
            id_dpedidos=[]
            total_proforma=0.0
            for dpedidos in detashepedido:
                id_dpedidos.append(dpedidos.id)
            for i in payload['data']:
                inventario=Inventario.objects.get(id=i['inventario'])
                if i['id']!=None:
                    indexpedido=None
                    for index,item in enumerate(detashepedido):
                        if item.id==i['id']:
                            indexpedido=index
                    cantidadanterior=detashepedido[indexpedido].cantidada
                    nuevodisponible=i['cantidada'] - cantidadanterior
                    inventario.disponible -= nuevodisponible
                    inventario.bloqueado += nuevodisponible
                perfil=Perfil.objects.get(usuario=request.user)
                precio_seleccionado=i['precio_seleccionado']
                producto=Producto.objects.get(id=i["producto"])
                instancia=Instancia.objects.get(perfil=perfil.id)
                cantidad=int(i["cantidada"])
                totalp=cantidad * precio_seleccionado
                precio_unidad=float(precio_seleccionado) # Calcular el precio de cada producto
                totalp=cantidad * float(precio_unidad) # Calcular el precio final segun la cantidad
                total_proforma+=float(totalp)
                pedido=pedido_id
                nuevo_componente=DetallePedido(lote=i["lote"],total_producto=totalp,precio_seleccionado=precio_seleccionado,instancia_id=instancia.id,pedido=pedido,cantidada=cantidad,producto=producto,inventario=inventario)
                nuevo_componente.save()
                if i['id']==None:
                    inventario.disponible=int(inventario.disponible) - cantidad
                    inventario.bloqueado=int(inventario.bloqueado)+cantidad
                inventario.save()
            pedido_id.total=total_proforma
            pedido_id.save()
            DetallePedido.objects.filter(id__in=id_dpedidos).delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para hacer la validacion de los pedidos
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validar_pedido(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Pedido','actualizar'):
        payload=json.loads(request.body)
        try:
            pedido=Pedido.objects.get(id=payload['idpedido'])
            decision=payload['decision']
            detashepedido=DetallePedido.objects.filter(pedido=pedido)
            perfil=Perfil.objects.get(usuario=request.user)
            instancia=Instancia.objects.get(perfil=perfil.id)
            if payload['decision']=='Rechazado':
                pedido.estatus='C'
                pedido.save()
                for deta in detashepedido:
                    inventario=Inventario.objects.get(id=deta.inventario.id)
                    inventario.bloqueado=inventario.bloqueado - deta.cantidada
                    inventario.disponible=inventario.disponible+deta.cantidada
                    inventario.save()
                return Response(status=status.HTTP_200_OK)
            else:
                pedido.estatus='A'
                pedido.save()
                ## Se crea una nueva proforma,en base a los datos del pedido
                nueva_proforma=Proforma(pedido=pedido,instancia=instancia)
                nueva_proforma.cliente=pedido.cliente
                nueva_proforma.vendedor=pedido.vendedor
                nueva_proforma.empresa=pedido.empresa
                nueva_proforma.nombre_cliente=pedido.cliente.nombre
                nueva_proforma.identificador_fiscal=pedido.cliente.identificador
                nueva_proforma.direccion_cliente=pedido.cliente.ubicacion
                nueva_proforma.telefono_cliente=pedido.cliente.telefono
                nueva_proforma.precio_seleccionadoo=pedido.precio_seleccionadoo
                nueva_proforma.save()
                # Se crea el detalle de la proforma con la información asociada en el detalle pedido
                for deta in detashepedido:
                    nuevo_detalle=DetalleProforma(
                        proforma=nueva_proforma,
                        precio_seleccionado=deta.precio_seleccionado,
                        inventario=deta.inventario,
                        cantidada=deta.cantidada,
                        lote=deta.lote,
                        producto=deta.producto,
                        precio=deta.precio_seleccionado,
                        total_producto=deta.total_producto,
                        instancia=instancia
                    )
                    nuevo_detalle.save()
                    nueva_proforma.total += deta.total_producto
                    nueva_proforma.saldo_proforma=nueva_proforma.total
                    nueva_proforma.save()
                    inventario=Inventario.objects.get(id=deta.inventario.id)
                    inventario.bloqueado=inventario.bloqueado - deta.cantidada
                    inventario.save()
                return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para generar facturas
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def generar_factura(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Factura','escribir'):
        payload=json.loads(request.body)
        try:
            proforma=Proforma.objects.get(id=payload['idproforma'])
            detasheproforma=DetalleProforma.objects.filter(proforma=proforma)
            perfil=Perfil.objects.get(usuario=request.user)
            instancia=Instancia.objects.get(perfil=perfil.id)
            nueva_factura=Factura(proforma=proforma,instancia=instancia)
            nueva_factura.nombre_empresa=proforma.empresa.nombre
            nueva_factura.direccion_empresa= proforma.empresa.direccion_fiscal
            nueva_factura.id_cliente=proforma.cliente.id
            nueva_factura.nombre_cliente=proforma.cliente.nombre
            nueva_factura.identificador_fiscal=proforma.cliente.identificador
            nueva_factura.direccion_cliente=proforma.cliente.ubicacion
            nueva_factura.telefono_cliente=proforma.cliente.telefono
            nueva_factura.correo_cliente=proforma.cliente.mail
            nueva_factura.id_vendedor=proforma.cliente.id
            nueva_factura.nombre_vendedor=proforma.vendedor.nombre
            nueva_factura.telefono_vendedor=proforma.vendedor.telefono
            nueva_factura.impuesto=16
            nueva_factura.save()
            for deta in detasheproforma:
                    nuevo_detalle=DetalleFactura(
                        factura=nueva_factura,
                        inventario=deta.inventario,
                        inventario_fijo=deta.inventario,
                        cantidada=deta.cantidada,
                        lote=deta.lote,
                        fecha_vencimiento=deta.inventario.fecha_vencimiento,
                        producto=deta.producto,
                        producto_fijo=deta.producto.nombre,
                        precio=deta.precio_seleccionado,
                        total_producto=deta.total_producto,
                        instancia=instancia)
                    nuevo_detalle.save()
                    nueva_factura.subtotal += float( deta.total_producto)
                    nueva_factura.total += float( deta.total_producto)+(float( deta.total_producto) * (float(nueva_factura.impuesto) / 100))
                    nueva_factura.save()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar proformas 
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_proforma(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Proforma','actualizar'):
        payload=json.loads(request.body)
        try:
            proforma_id=Proforma.objects.get(id=payload['idproforma'])
            detasheproforma=DetalleProforma.objects.filter(proforma=proforma_id)
            id_proformas=[]
            total_proforma=0.0
            for dproformas in detasheproforma:
                id_proformas.append(dproformas.id)
            for i in payload['data']:
                inventario=Inventario.objects.get(id=i['inventario'])
                if i['id']!=None:
                    indexpedido=None
                    for index,item in enumerate(detasheproforma):
                        if item.id==i['id']:
                            indexpedido=index
                    cantidadanterior=detasheproforma[indexpedido].cantidada
                    nuevodisponible=i['cantidada'] - cantidadanterior
                    inventario.disponible -= nuevodisponible
                perfil=Perfil.objects.get(usuario=request.user)
                precio_seleccionado=i['precio_seleccionado']
                producto=Producto.objects.get(id=i["producto"])
                instancia=Instancia.objects.get(perfil=perfil.id)
                cantidad=int(i["cantidada"])
                totalp=cantidad * precio_seleccionado
                precio_unidad=float(precio_seleccionado) # Calcular el precio del producto en la venta
                totalp=cantidad * precio_unidad # Calcular el precio final del detalle segun la cantidad
                total_proforma += float(totalp)
                proforma=proforma_id
                nuevo_componente=DetalleProforma(proforma=proforma,lote=i["lote"],total_producto=totalp,precio_seleccionado=precio_seleccionado,precio=precio_unidad,instancia_id=instancia.id,cantidada=cantidad,producto=producto,inventario=inventario)
                nuevo_componente.save()
                if i['id']==None:
                    inventario.disponible=int(inventario.disponible) - cantidad
                inventario.save()
            proforma_id.total=total_proforma
            proforma_id.save()
            DetalleProforma.objects.filter(id__in=id_proformas).delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion para generar Excel de precios de productos
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def vista_xls(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Producto','leer'):
        response=HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition']='attachment; filename="productos.xls"'
        excel_wb=xlwt.Workbook(encoding='utf-8')
        excel_ws=excel_wb.add_sheet('Styling Data') # ws es Work Sheet
        i=0
        for m in Marca.objects.all().values():
            estilo=xlwt.easyxf('font: bold 1')
            excel_ws.write(i,0,'Marca:',estilo)
            excel_ws.write(i,1,m['nombre'])
            i=i+1
            excel_ws.write(i,0,'Codigo')
            excel_ws.write(i,1,'Producto')
            excel_ws.write(i,2,'Precio A')
            excel_ws.write(i,3,'Precio B')
            excel_ws.write(i,4,'Precio c')
            i=i+1
            for p in Producto.objects.filter(marca=m['id']).values():
                excel_ws.write(i,0,p['sku'])
                excel_ws.write(i,1,p['nombre'])
                excel_ws.write(i,2,p['precio_1'])
                excel_ws.write(i,3,p['precio_2'])
                excel_ws.write(i,4,p['precio_3'])
                i=i+1
        excel_wb.save(response)
        return response
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para guardar los pdfs de pedidos en el sistema operativo
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def guardar_pdf(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Proforma','actualizar'):
        try:
            data=request.data
            if not data:
                data['id']=1
            host=str(request.get_host())
            principal_url='http://%s'%(host)
            url=principal_url+'/apis/v1/pdf-proforma/%s'%(data['id'])
            response=requests.get(url)
            with open('proformas/proforma-%s.pdf'%data['id'],'wb') as f:
                f.write(response.content)
            return Response(True,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(False,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para obtener las ventas totales del mes actual y el anterior
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ventas_totales(request):
    try:
        ahora=timezone.now()
        antes=timezone.datetime(month=ahora.month,year=ahora.year,day=1)
        total_actual=Proforma.objects.filter(fecha_proforma__range=(antes,ahora)).aggregate(cantidad=Sum('total'))
        mucho_antes=antes-timezone.timedelta(weeks=4)
        mucho_antes=mucho_antes.replace(day=1)
        total_anterior=Proforma.objects.filter(fecha_proforma__range=(mucho_antes,antes)).aggregate(cantidad=Sum('total'))
        total={'actual':{'fecha':antes,'total':total_actual,},'anterior':{'fecha':mucho_antes,'total':total_anterior,},}
        return Response(total,status=status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo para obtener los permisos disponibles para la instancia
@api_view(["GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def permisos_disponibles(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
        try:
            perfil=Perfil.objects.get(usuario=request.user)
            menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
            lista=[]
            for m in menus:
                if not menus.filter(parent=m):
                    lista.append(m.id)
            seria=MenuInstanciaSerializer(MenuInstancia.objects.filter(id__in=lista), many=True)
            return Response(data=seria.data,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        Response(status=status.HTTP_401_UNAUTHORIZED)
# Crear permisos
@api_view(["GET"])
@csrf_exempt
@permission_classes([IsAdminUser])
def ubop(request):
    try:
        perfil=Perfil.objects.get(usuario=request.user)
        menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
        lista=[]
        for m in menus:
            if not menus.filter(parent=m):
                lista.append(m.id)
        permisos=MenuInstancia.objects.filter(id__in=lista)
        for p in permisos:
            Permiso.objects.create(instancia=perfil.instancia,menuinstancia=p,perfil=perfil,leer=True,escribir=True,borrar=True,actualizar=True)
        return Response('Hecho')
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion para obtener las instancias en las acciones
def obtener_instancia(perfil,instancia=None):
    return instancia if perfil.tipo=='S' and instancia else perfil.instancia.id
# Verificar que el usuario tenga permisos
def verificar_permiso(perfil,vista,accion):
    try:
        permiso=Permiso.objects.filter(instancia=perfil.instancia,menuinstancia__menu__router__contains=vista,perfil=perfil).first()
    except:
        return False
    if permiso:
        if accion=='leer':
            return permiso.leer
        elif accion=='escribir':
            return permiso.escribir
        elif accion=='actualizar':
            return permiso.actualizar
        elif accion=='borrar':
            return permiso.borrar
    return False
# Funcion para la primera carga del sistema
def crear_super_usuario(request):
    if Menu.objects.all().count()==0:
        for modelo in modelosMENU['modelos']:
            modulo=Modulo(nombre=modelo['router'])
            modulo.save()
            menu=Menu(router=modelo['router'],orden=modelo['orden'])
            menu.modulos=modulo
            menu.save()
            if modelo['parent']!=None:
                menu.parent=Menu.objects.get(router=modelo['parent'])
                menu.save()
    if Instancia.objects.all().count()==0:
        instancia=Instancia.objects.create(nombre="Primera",activo=True,multiempresa=True,vencimiento=None)
        for mod in Modulo.objects.all():
            instancia.modulos.add(mod)
        superuser=User.objects.create_user(username='super',password='super',is_staff=True, is_superuser=True)
        perfilS=Perfil(instancia=instancia,usuario_id=superuser,activo=True,avatar=None,tipo="S")
        perfilS.save()
        admin=User.objects.create_user(username='admin',password='admin')
        perfilA=Perfil(instancia=instancia,usuario=admin,activo=True,avatar=None,tipo="A")
        perfilA.save()
        usuario=User.objects.create_user(username='usuario',password='usuario')
        perfilU=Perfil(instancia=instancia,usuario=usuario,activo=True,avatar=None,tipo="U")
        perfilU.save()
        for m in Menu.objects.all().order_by('id'):
            menuinstancia=MenuInstancia(instancia_id=instancia,menu=m,orden=m.orden)
            menuinstancia.save()
            if m.parent!=None:
                menuinstancia.parent=MenuInstancia.objects.get(menu__id=m.parent.id)
                menuinstancia.save()
        return "Super creado"
    else:
        return "Ya existe un superusuario"
# Funcion para generar contraseñas
def generar_clave():
    lower=string.ascii_lowercase
    upper=string.ascii_uppercase
    numeros='1234567890'
    symbols='!$%&?*#@+='
    all=lower+upper+numeros+symbols
    temp=random.sample(all,16)
    return "".join(temp)
# Funcion para obtener el perfil del usuario
def obt_per(user):
    return Perfil.objects.get(usuario=user)
# Funcion para guardar permisos
def guardar_permisos(data,perfil_n=None,perfil_c=None):
    if perfil_c:
        instancia=perfil_c.instancia
        if not perfil_n:
            perfil_n=perfil_c
        perfil_n=Perfil.objects.get(id=perfil_n)
        for per in data:
            menu_i=MenuInstancia.objects.get(instancia=instancia,menu__router__contains=per['menu'])
            permiso_c=Permiso.objects.filter(menuinstancia=menu_i,perfil=perfil_c).first()
            if permiso_c and perfil_n!=perfil_c:
                try:
                    permiso_n=Permiso.objects.get(instancia=instancia,menuinstancia=menu_i,perfil=perfil_n)
                except:
                    permiso_n=Permiso(instancia=instancia,menuinstancia=menu_i,perfil=perfil_n)
                permiso_n.leer=per['leer'] if permiso_c.leer else False
                permiso_n.escribir=per['escribir'] if permiso_c.escribir else False
                permiso_n.borrar=per['borrar'] if permiso_c.borrar else False
                permiso_n.actualizar=per['actualizar'] if permiso_c.actualizar else False
                permiso_n.save()
# Funcion para crear los admins por la nueva instancia
def crear_admin(data):
    try:
        user=User(username=data['username'],email=data['email'],password=generar_clave())
        user.save()
        instancia=Instancia(nombre=data['instancia'],activo=True,multiempresa=data['multiempresa'],vencimiento=data['vencimiento'])
        instancia.save()
        perfil=Perfil(usuario=user,instancia=instancia,tipo='A')
        perfil.save()
        permisos=data['permisos']
        guardar_permisos(permisos,perfil.id,perfil)
        # lista=[]
        # for p in permisos:
        #     lista.append(p.menu)
        # menus=Menu.objects.filter(router__in=lista)
        # while True:
        #     i=0
        #     if menus[i].parent:
        #         menus.append(menus[i].parent)
        #     break
        # for m in Menu.objects.all().order_by('id'):
        #     menuinstancia=MenuInstancia(instancia_id=instancia,menu=m,orden=m.orden)
        #     menuinstancia.save()
        #     if m.parent!=None:
        #         menuinstancia.parent=MenuInstancia.objects.get(menu__id=m.parent.id)
        #         menuinstancia.save()
        if perfil.id:
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': _(e.args[0])},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
def obtener_padres(perfil):
    menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
    lista=[0]
    for p in Permiso.objects.filter(perfil=perfil):
        menu=menus.get(id=p.menuinstancia_id)
        encontrado=False
        if menu.parent:
            for l in lista:
                if l==menu.parent.id:
                    encontrado=True
                    break
        if not encontrado:
            lista.append(menu.parent.id)
        lista.append(menu.id)
    del lista[0]
    return lista
