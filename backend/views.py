# Importes de Rest framework
from os import stat_result
import re
from idna import IDNABidiError
from rest_framework import permissions,viewsets,status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.models import Token
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
from django.shortcuts import render,get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
# Raiz
from .serializers import *
from .models import *
from .menu import *
# from .vistas import *
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
    queryset=Group.objects.none()
    serializer_class=GroupMSerializer
# Vista creada para el modelo de Permission
class PermissionVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    queryset=Permission.objects.none()
    serializer_class=PermissionMSerializer
# Vista modificada para el modelo mixim de User
class UserVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=User
    queryset=modelo.objects.all()
    serializer_class=UsuarioMSerializer
    # Motodo crear no permitido
    def create(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'escribir'):
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
                raise
        except:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodo actualizar
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
    # Metodo borrar
    def destroy(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Usuarios_y_permisos','borrar'):
            objeto=self.get_object()
            # Super
            if perfil.tipo=='S':
                objeto.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            # Admin/Usuario
            elif perfil.tipo=='A' or perfil.tipo=='U':
                # Verificar que el usuario a borrar no sea Staff,y este en la misma instancia desde donde se hace la peticion
                if objeto.perfil.tipo!='S' and objeto.perfil.tipo!='A' and str(objeto.perfil.instancia.id)==str(perfil.instancia.id) and perfil.usuario.id!=self.request.user.id:
                    objeto.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response('No tienes permitido borrar este usuario',status=status.HTTP_401_UNAUTHORIZED)
            # Vendedor
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Vista del modelo Modulo
class ModuloVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Modulo
    # queryset=modelo.objects.all()
    serializer_class=ModuloSerializer
    # Metodo crear no disponible
    def create(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo actualizar no disponible
    def update(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo borrar no disponible
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo leer
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
# Vista para el modelo Menu
class MenuVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Menu
    # queryset=modelo.objects.all()
    serializer_class=MenuSerializer
    # Metodo crear no disponible
    def create(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo actualizar
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
    # Metodo borrar no disponible
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo leer
    def get_queryset(self):
        # Verificar si existen los menus
        perfil=obt_per(self.request.user)
        if perfil.tipo=='S':
            return Menu.objects.all()
        else:
            return Menu.objects.none()
# Instancia
class InstanciaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAdminUser]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Instancia
    # queryset=modelo.objects.all()
    serializer_class=InstanciaSerializer
    # Metodo crear no disponible
    def create(self,request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo actualizar
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Dashboard','actualizar'):
            if perfil.tipo=='S':
                partial=True
            instance=self.get_object()
            serializer=self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    # Metodo borrar
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # Metodo actualizar
    def get_queryset(self):
        perfil=obt_per(self.request.user)
        return Instancia.objects.all().order_by('nombre') if perfil.tipo=='S' else Instancia.objects.none()
# Menus por instancia
class MenuInstanciaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=MenuInstancia
    # queryset=modelo.objects.all()
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
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Perfil
    queryset=modelo.objects.all()
    serializer_class=PerfilSerializer
    # Metodo crear
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
    # Metodo actualizar
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
    # Metodo borrar
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
                    return Response('No puedes borrar este perfil',status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)# Permisos de los usuarios
class PermisoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Usuarios_y_permisos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Permiso
    queryset=modelo.objects.all()
    serializer_class=PermisoSerializer
    # Metodo crear
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
    # Metodo actualizar
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
    # Metodo borrar
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
                return Response('No puedes borrar los permisos de este usuario',status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Empresas registradas de la instancia
class EmpresaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Empresa'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Empresa
    queryset=modelo.objects.all()
    serializer_class=EmpresaSerializer
    # Metodo crear
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
    # Metodo actualizar
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
    # Metodo borrar
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Contactos de las empresas
class ContactoEmpresaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Empresa'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=ContactoEmpresa
    queryset=modelo.objects.all()
    serializer_class=ContactoEmpresaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Configuracion de papelerias
class ConfiguracionPapeleriaVS(viewsets.ModelViewSet):
    permiso='Empresa'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=ConfiguracionPapeleria
    queryset=modelo.objects.all()
    serializer_class=ConfiguracionPapeleriaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Tasas de conversiones de la instancia
class TasaConversionVS(viewsets.ModelViewSet):
    # Permisos
    permiso='TasaConversion'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=TasaConversion
    queryset=modelo.objects.all()
    serializer_class=TasaConversionSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Impuestos registrados
class ImpuestosVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Impuesto'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Impuestos
    queryset=modelo.objects.all()
    serializer_class=ImpuestosSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Marcas registradas en la instancia
class MarcaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Productos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Marca
    queryset=modelo.objects.all()
    serializer_class=MarcaSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Productos','escribir'):
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
        if verificar_permiso(perfil,'Productos','actualizar'):
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
        if verificar_permiso(perfil,'Productos','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data)
# Productos registrados en la instancia
class ProductoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Productos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Producto
    queryset=modelo.objects.all()
    serializer_class=ProductoSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Productos','escribir'):
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
        if verificar_permiso(perfil,'Productos','actualizar'):
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
        if verificar_permiso(perfil,'Productos','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# ImagenesP registradas en la instancia
class ProductoImagenVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Productos'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=ProductoImagen
    queryset=modelo.objects.all()
    serializer_class=ProductoImagenSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Productos','escribir'):
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
        if verificar_permiso(perfil,'Productos','actualizar'):
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
        if verificar_permiso(perfil,'Productos','borrar'):
            instance=self.get_object()
            if instance.instancia==perfil.instancia or perfil.tipo=='S':
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodo leer no disponible
    def get_queryset(self):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
# Almacen registrado en la instancia
class AlmacenVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Almacenes'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Almacen
    queryset=modelo.objects.all()
    serializer_class=AlmacenSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Movimientos del inventario registrados en el sistema
class MovimientoInventarioVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Inventario'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=MovimientoInventario
    queryset=modelo.objects.all()
    serializer_class=MovimientoInventarioSerializer
    # Metodo crear
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
        if verificar_permiso(perfil,'Productos','actualizar'):
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalles del inventario registrados
class DetalleInventarioVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Inventario'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Inventario
    queryset=modelo.objects.all()
    serializer_class=InventarioSerializer
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Vendedores registrados en la instancia
class VendedorVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Vendedor'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Vendedor
    queryset=modelo.objects.all()
    serializer_class=VendedorSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Clientes registrados en la instancia
class ClienteVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Cliente'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Cliente
    queryset=modelo.objects.all()
    serializer_class=ClienteSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Contactos de los clientes de la instancias
class ContactoClienteVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Cliente'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=ContactoCliente
    queryset=modelo.objects.all()
    serializer_class=ContactoClienteSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Pedidos registrados en la instancia
class PedidoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Pedido'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Pedido
    queryset=modelo.objects.all()
    serializer_class=PedidoSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Pedido','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            configuracion=verificar_numerologia(datos,self.modelo)
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion.save()
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalles de los pedidos
class DetallePedidoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Pedido'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetallePedido
    queryset=modelo.objects.all()
    serializer_class=DetallePedidoSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Proformas registrados en la instancia
class ProformaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Proforma'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Proforma
    queryset=modelo.objects.all()
    serializer_class=ProformaSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            configuracion=verificar_numerologia(datos,self.modelo)
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Proforma','actualizar'):
            partial=True
            instance=self.get_object()
            try:
                if request.data['fecha_despacho'] == True and instance.fecha_despacho == None:
                    request.data['fecha_despacho'] = timezone.now()
            except Exception as e:
                print(e)
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalles de las proformas de la instancia
class DetalleProformaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Proforma'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetalleProforma
    queryset=modelo.objects.all()
    serializer_class=DetalleProformaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Notas de pago
class NotaPagoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Notasdepago'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=NotasPago
    queryset=modelo.objects.all()
    serializer_class=NotaPagoMSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Notasdepago','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            configuracion=verificar_numerologia(datos,self.modelo)
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion.save()
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalles de las notas de pago de la instancia
class DetalleNotaPagoVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Notasdepago'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetalleNotasPago
    queryset=modelo.objects.all()
    serializer_class=DetalleNotaPagoMSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Facturas registradas en la instancia
class FacturaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Factura'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Factura
    queryset=modelo.objects.all()
    serializer_class=FacturaSerializer
    # Metodo crear
    def create(self,request):
        perfil=obt_per(self.request.user)
        if verificar_permiso(perfil,'Factura','escribir'):
            datos=request.data
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            configuracion=verificar_numerologia(datos,self.modelo)
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion.save()
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalles de las facturas de la instancia
class DetalleFacturaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Factura'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetalleFactura
    queryset=modelo.objects.all()
    serializer_class=DetalleFacturaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Impuestos en las facturas de la instancia
class ImpuestosFacturaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Factura'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=ImpuestosFactura
    queryset=modelo.objects.all()
    serializer_class=ImpuestosFacturaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Numerologia de las facturas de la instancia
class NumerologiaFacturaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Factura'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=NumerologiaFactura
    queryset=modelo.objects.all()
    serializer_class=NumerologiaFacturaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Notas de las facturas de la instancia
class NotaFacturaVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Factura'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=NotaFactura
    queryset=modelo.objects.all()
    serializer_class=NotaFacturaSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Proveedores registrados en la instancia
class ProveedorVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Proveedor'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Proveedor
    queryset=modelo.objects.all()
    serializer_class=ProveedorSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Compras registradas en la instancia
class CompraVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Compra'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=Compra
    queryset=modelo.objects.all()
    serializer_class=CompraSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Detalle de las compras
class DetalleCompraVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Compra'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetalleCompra
    queryset=modelo.objects.all()
    serializer_class=DetalleCompraSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
# Notas de las compras de la intancia
class NotaCompraVS(viewsets.ModelViewSet):
    # Permisos
    permiso='Compra'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=NotaCompra
    queryset=modelo.objects.all()
    serializer_class=NotaCompraSerializer
    # Metodo crear
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
    # Metodos de leer
    def list(self,request):
        try:
            perfil=obt_per(self.request.user)
            if verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if verificar_permiso(obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
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
    modelo=Inventario
    if verificar_permiso(perfil,'Inventario','leer'):
        if perfil:
            inventarios=Inventario.objects.filter(instancia=perfil.instancia)
            for o in inventarios:
                if o.disponible==0 and o.bloqueado==0:
                    inventarios=inventarios.exclude(id=o.id)
            inventarios=inventarios.values('almacen','almacen__nombre','producto','producto__nombre').annotate(sum_disponible=Sum('disponible'),sum_bloqueado=Sum('bloqueado'))
            inventarios_p=paginar(inventarios,request.query_params.copy(),modelo)
            return Response(inventarios_p,status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para crear un nuevo usuario
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def crear_nuevo_usuario(request):
    datos=request.data
    user=None
    perfil_nuevo=None
    try:
        perfil_creador=Perfil.objects.get(usuario=request.user)
        # En caso de encontrar un usuario con el mismo email
        user=User.objects.filter(email=datos['email'])
        if user:
            return Response("Ya hay un usuario con el mismo correo",status=status.HTTP_400_BAD_REQUEST)
        # En caso de crear un nuevo Admin
        elif perfil_creador.tipo=='S' and datos['tipo']=='A':
            return crear_admin(datos,perfil_creador)
        # En caso de que se quiera crear un usuario normal
        elif perfil_creador.tipo=='A' or perfil_creador.tipo=='S' or verificar_permiso(perfil_creador,'Usuarios_y_permisos','escribir'):
            # Obtencion rapida de la instancia
            datos['instancia']=obtener_instancia(perfil_creador,datos['instancia'])
            # Crear usuario con 'create_user'
            user=User.objects.create_user(username=datos['username'],email=datos['email'],password=datos['clave'])
            # Crear perfil del usuario
            perfil_nuevo=Perfil.objects.create(usuario=user,instancia_id=datos['instancia'],tipo=datos['tipo'])
            # Crear permisos
            permisos=guardar_permisos(datos['permisos'],perfil_nuevo.id,perfil_creador)
            # En caso de un error al crear los permisos saltar error
            if permisos:
                raise Exception('%s'%(permisos['error']))
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        # Borrar datos en caso de error
        try:
            user.delete()
        except:
            pass
        try:
            perfil_nuevo.delete()
        except:
            pass
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener el menu de la pagina segun el perfil, los permisos y la intancia del usuario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
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
                configuracion=verificar_numerologia({'empresa':pedido.empresa.id,'instancia':pedido.instancia.id},Proforma)
                # Se crea una nueva proforma,en base a los datos del pedido
                nueva_proforma=Proforma(pedido=pedido,instancia=instancia)
                nueva_proforma.numerologia=configuracion.valor
                nueva_proforma.cliente=pedido.cliente
                nueva_proforma.vendedor=pedido.vendedor
                nueva_proforma.empresa=pedido.empresa
                nueva_proforma.nombre_cliente=pedido.cliente.nombre
                nueva_proforma.identificador_fiscal=pedido.cliente.identificador
                nueva_proforma.direccion_cliente=pedido.cliente.ubicacion
                nueva_proforma.telefono_cliente=pedido.cliente.telefono
                nueva_proforma.precio_seleccionadoo=pedido.precio_seleccionadoo
                nueva_proforma.save()
                configuracion.valor+=1
                configuracion.save()
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
                print('holo')
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
            configuracion=verificar_numerologia({'empresa':proforma.empresa.id,'instancia':proforma.instancia.id},Factura)
            nueva_factura=Factura(proforma=proforma,instancia=instancia)
            nueva_factura.numerologia=configuracion.valor
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
            configuracion.valor+=1
            configuracion.save()
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
def vista_xls(request):
    params=request.query_params
    token=params.get('token').split(' ')[1]
    if Token.objects.get(key=token):
        perfil=Perfil.objects.get(usuario=1)
        if verificar_permiso(perfil,'Productos','leer'):
            response=HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition']='attachment;filename="productos.xls"'
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
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
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
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo para obtener los permisos disponibles para la instancia
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def permisos_disponibles(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
        try:
            perfil=Perfil.objects.get(usuario=request.user)
            menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
            disponibles=[]
            for m in menus:
                if not menus.filter(parent=m) and m:
                    obj={}
                    obj['id']=m.id
                    obj['orden']=m.orden
                    try:
                        obj['menu_id']=m.menu.id
                    except:
                        pass
                    try:
                        obj['parent_id']=m.parent.id
                    except:
                        pass
                    try:
                        obj['nombreMenu']=m.menu.router
                    except:
                        pass
                    try:
                        obj['nombreParent']=m.parent.menu.router
                    except:
                        pass
                    disponibles.append(obj)
            return Response(data=disponibles,status=status.HTTP_200_OK)
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener los usuarios y su informacion
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def perfiles_usuarios(request):
    try:
        perfil=Perfil.objects.get(usuario=request.user)
        instancia=perfil.instancia
        modelo=User
        objetos=modelo.objects.all() if perfil.tipo=='S' else modelo.objects.filter(perfil__instancia=instancia)
        usuarios=paginar(objetos,request.query_params.copy(),modelo)
        disponibles=[]
        for u in usuarios['objetos']:
            try:
                perfil=Perfil.objects.get(usuario=u)
            except:
                perfil=None
            usuario={'id':u.id,'email':u.email,'username':u.username,'permisos':[]}
            # Seteando el tipo de usuario
            usuario['tipo']=perfil.tipo if perfil else 'Sin perfil'
            if perfil:
                tipo=None
                tipo='Super' if perfil.tipo=='S' and not tipo else tipo
                tipo='Admin' if perfil.tipo=='A' and not tipo else tipo
                tipo='Usuario' if perfil.tipo=='U' and not tipo else tipo
                tipo='Vendedor' if perfil.tipo=='V' and not tipo else tipo
                usuario['nombreTipo']=tipo
            else:
                usuario['nombreTipo']='Sin perfil'
            # Escribiendo informacion del usuario
            usuario['perfil']=perfil.id if perfil else 'Sin perfil'
            usuario['instancia']=perfil.instancia.id if perfil else 'Sin perfil'
            usuario['nombreInstancia']=perfil.instancia.nombre if perfil else 'Sin perfil'
            usuario['activo']=perfil.activo if perfil else False
            if perfil:
                for p in Permiso.objects.filter(instancia=instancia,perfil=perfil):
                    permiso={
                        'instancia_id':p.instancia.id,
                        'orden':p.menuinstancia.orden,
                        'menu_id':p.menuinstancia.menu.id,
                        'nombreMenu':p.menuinstancia.menu.router,
                        'perfil_id':p.perfil.id,
                        'leer':p.leer,
                        'escribir':p.escribir,
                        'borrar':p.borrar,
                        'actualizar':p.actualizar,
                    }
                    permiso['parent_id']=p.menuinstancia.parent.menu.id if p.menuinstancia.parent else None
                    permiso['nombreParent']=p.menuinstancia.parent.menu.router if p.menuinstancia.parent else None
                    usuario['permisos'].append(permiso)
            disponibles.append(usuario)
        # Respuesta
        return Response({'objetos':disponibles,'info':usuarios['info']},status=status.HTTP_200_OK)
    except:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener los datos del usuario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def usuario_info(request):
    return Response(PerfilSerializer(Perfil.objects.get(usuario=request.user)).data,status=status.HTTP_200_OK)
@api_view(["POST", "GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def comision(request):
    data=request.data
    perfil=Perfil.objects.get(usuario=data.user)
    if verificar_permiso(perfil,'Comisiones','leer'):
        try:
            if not data:
                return Response("Error, Faltan los datos",status=status.HTTP_406_NOT_ACCEPTABLE)
            comision={'total_comision':0,'notas':[]}
            notas=NotasPago.objects.filter(instancia=perfil.instancia)
            notas_e=notas.filter(cliente=data['cliente']) # ,fecha__month=data['mes'],fecha__year=data['año']
            if len(notas_e)!=0:
                for n in notas_e:
                    nota={}
                    nota['id']=n.id
                    nota['cliente']=n.cliente.nombre
                    nota['cliente_id']=n.cliente.id
                    nota['comprobante']=n.comprobante
                    nota['descripcion']=n.descripcion
                    nota['fecha']=n.fecha
                    nota['total']=n.total
                    nota['detalles']=[]
                    for d in DetalleNotasPago.objects.filter(notapago__id=n.id):
                        detalle={}
                        detalle['id']=d.id
                        detalle['notapago_id']=d.notapago.id
                        detalle['proforma_id']=d.proforma.id
                        detalle['saldo_anterior']=d.saldo_anterior
                        detalle['monto']=d.monto
                        nota['detalles'].append(detalle)
                    comision['total_comision']+=n.total
                    comision['notas'].append(nota)
                comision['cliente_id']=data['cliente']
                comision['mes']=data['mes']
                comision['año']=data['año']
                return Response(comision,status=status.HTTP_200_OK)
            else:
                return Response("Error, No se encontraron notas de pago",status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response('Error, %s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion para obtener las instancias en las acciones
def obtener_instancia(perfil,instancia=None):
    return instancia if perfil.tipo=='S' and instancia else perfil.instancia.id
# Verificar que el usuario tenga permisos
def verificar_permiso(perfil,vista,accion):
    try:
        permiso=Permiso.objects.filter(instancia=perfil.instancia,menuinstancia__menu__router__exact=vista,perfil=perfil).first()
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
        instancia=Instancia.objects.create(nombre="Primera")
        for mod in Modulo.objects.all():
            instancia.modulos.add(mod)
        superuser=User.objects.create_user(username='super',password='super',is_staff=True, is_superuser=True)
        perfilS=Perfil(instancia=instancia,usuario=superuser,activo=True,avatar=None,tipo="S")
        perfilS.save()
        admin=User.objects.create_user(username='admin',password='admin')
        perfilA=Perfil(instancia=instancia,usuario=admin,activo=True,avatar=None,tipo="A")
        perfilA.save()
        usuario=User.objects.create_user(username='usuario',password='usuario')
        perfilU=Perfil(instancia=instancia,usuario=usuario,activo=True,avatar=None,tipo="U")
        perfilU.save()
        for m in Menu.objects.all().order_by('id'):
            menuinstancia=MenuInstancia(instancia=instancia,menu=m,orden=m.orden)
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
# Funcion para obtener la data de los permisos
def guardar_permisos(data,perfil_n=None,perfil_c=None,perfil=None):
    try:
        if perfil_c:
            instancia=perfil.instancia if perfil else perfil_c.instancia
            if perfil_n:
                # Obtener datos para la creacion de permisos
                perfil_n=Perfil.objects.get(id=perfil_n)
                menus_i=MenuInstancia.objects.filter(instancia=instancia)
                permisos=Permiso.objects.filter(instancia=perfil_c.instancia,perfil=perfil_c)
                for per in data:
                    # Si se debe crear un menu, crearlo
                    padre=crear_menu(instancia,per['parent']) if perfil else None
                    menu=crear_menu(instancia,per['menu'],padre) if perfil else None
                    # Obtener menu
                    menu_i=menus_i.get(menu__router__exact=per['menu']) if not perfil else menu
                    # Verificar permiso del creador
                    permiso_c=permisos.filter(menuinstancia=menu_i).first()
                    if permiso_c:
                        if per['parent']:
                            # Obtener menu padre
                            menu_ip=menus_i.get(instancia=instancia,menu__router__exact=per['parent']) if not perfil else padre
                            crear_permiso(instancia,per,menu_ip,perfil_n,permiso_c)
                        crear_permiso(instancia,per,menu_i,perfil_n,permiso_c)
        return None
    except Exception as e:
        # Borrar datos creados
        try:
            Permiso.objects.filter(instancia=instancia,perfil=perfil).delete()
        except:
            pass
        return {'error':e}
# Funcion para crear/guardar los permisos
def crear_permiso(instancia,data,menu,perfil,creador):
    try:
        permiso=Permiso.objects.get(instancia=instancia,menuinstancia=menu,perfil=perfil)
    except:
        permiso=Permiso(instancia=instancia,menuinstancia=menu,perfil=perfil)
    permiso.leer=data['leer'] if creador.leer else False
    permiso.escribir=data['escribir'] if creador.escribir else False
    permiso.borrar=data['borrar'] if creador.borrar else False
    permiso.actualizar=data['actualizar'] if creador.actualizar else False
    permiso.save()
# Funcion para crear los admins por la nueva instancia
def crear_admin(data,super_p):
    try:
        user=User.objects.create(username=data['username'],email=data['email'],password=generar_clave())
        instancia=Instancia.objects.create(nombre=data['instancia'],activo=True,multiempresa=data['multiempresa'],vencimiento=data['vencimiento'])
        perfil=Perfil.objects.create(usuario=user,instancia=instancia,tipo='A')
        permisos=guardar_permisos(data['permisos'],perfil.id,super_p,perfil)
        if permisos:
            raise Exception('%s'%(permisos['error']))
        return Response(status=status.HTTP_201_CREATED)
    except Exception as e:
        try:
            user.delete()
        except:
            pass
        try:
            instancia.delete()
        except:
            pass
        try:
            perfil.delete()
        except:
            pass
        return Response('%s'%(e),status=status.HTTP_417_EXPECTATION_FAILED)
# Funcion para crear menu de la instancia
def crear_menu(instancia,menu,parent=None):
    menu=Menu.objects.get(router__exact=menu)
    menu_i=MenuInstancia.objects.create(instancia=instancia,menu=menu,parent=parent)
    return menu_i
# Funcion para obtener los menus superiores
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
        if not encontrado and menu.parent:
            lista.append(menu.parent.id)
        lista.append(menu.id)
    del lista[0]
    return lista
# Funcion para paginar y filtrar objetos
def paginar(objetos,parametros,modelo=None):
    retorno={}
    devueltos=[]
    errores=[]
    # Parametros
    try:
        pagina=int(parametros.get('p_pagina'))
        parametros.pop('p_pagina')
    except:
        pagina=1
    try:
        ordenar=parametros.get('p_ordenar')
        parametros.pop('p_ordenar')
    except:
        ordenar=''
    try:
        cantidad=int(parametros.get('p_cantidad'))
        parametros.pop('p_cantidad')
        if cantidad>100:
            raise
    except:
        errores.append({'code':404,'valor':'%s'%('La cantidad dada no es aceptable')})
        cantidad=10
    # Intentar obtener objetos por filtro
    filtros=[]
    if parametros:
        for p in parametros.keys():
            try:
                campos=p.split('__')
                valores=parametros.get(p)
                if campos[-1]=='in' or campos[-1]=='range':
                    valores=valores.split(',')
                objetos=objetos.filter(**{p: valores}) if parametros.get(p) else objetos
                filtros.append({'campo':p,'valor':valores})
            except Exception as e:
                errores.append({'code':500,'valor':'%s'%(e)})
                objetos=objetos
    # Intentar ordenar los objetos
    try:
        objetos=objetos.order_by(ordenar) if len(ordenar) > 0 else objetos
    except Exception as e:
        errores.append({'code':404,'valor':'%s'%(e)})
        objetos=objetos
    # Variables
    devueltos=[]
    vuelta=1
    page=1
    id=0
    # Ciclo while para hacer la paginacion
    try:
        while True:
            if page==pagina:
                try:
                    devueltos.append(objetos[id])
                except:
                    pass
            if vuelta==cantidad:
                page+=1
                vuelta=0
                if page>pagina:
                    break
            vuelta+=1
            id+=1
    except Exception as e:
        errores.append({'code':500,'valor':'%s'%(e)})
        devueltos=objetos[:10]
    info=paginas_totales(modelo,cantidad,filtros)
    info['pagina_actual']=pagina
    info['ordenado_por']=ordenar
    info['cantidad_seleccionada']=cantidad
    info['errores']=[]
    for e in errores:
        info['errores'].append(e)
    retorno['info']=info
    retorno['objetos']=devueltos
    return retorno
# Funcion para calcular paginas
def paginas_totales(modelo,cantidad,filtros):
    try:
        if modelo:
            paginas=1
            vueltas=0
            objetos=modelo.objects.all()
            if filtros:
                for f in filtros:
                    objetos=objetos.filter(**{f['campo']:f['valor']})
                total=objetos.count()
                objetos=None
            else:
                total=modelo.objects.all().count()
            for i in range(total):
                if vueltas==cantidad:
                    paginas+=1
                    vueltas=0
                vueltas+=1
            return {'objetos_totales':total,'paginas_totales':paginas,'error':[]}
        else:
            raise
    except Exception as e:
        return {'error':[{'code':406,'valor':'%s'%(e)}]}
@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def c(r):
    perfil=Perfil.objects.get(usuario=r.user)
    # m=Marca.objects.all().first()
    # for p in Producto.objects.all():
    #     p.marca=m
    #     p.save()
    # if Producto.objects.all().count() < 1000:
    #     for i in range(1500):
    #         n='Prueba %s'%(i)
    #         Producto.objects.create(nombre=n,instancia=perfil.instancia,precio_1=1,precio_2=2,sku='Prueba')
    return Response('Hey')
# Obtener correlativo
def verificar_numerologia(datos,modelo):
    if modelo == Pedido:
        tipo='E'
    elif modelo == Proforma:
        tipo='P'
    elif modelo == Factura:
        tipo='F'
    elif modelo == NotasPago:
        tipo='N'
    # elif modelo == NotaDevolucion:
    #     tipo='A'
    # elif modelo == NotaControl:
    #     tipo='B'
    # elif modelo == NotaCredito:
    #     tipo='C'
    # elif modelo == NotaDebito:
    #     tipo='D'
    empresa=Empresa.objects.get(id=datos['empresa'])
    instancia=Instancia.objects.get(id=datos['instancia'])
    configuracion, creado = ConfiguracionPapeleria.objects.get_or_create(instancia=instancia,empresa=empresa,tipo=tipo,defaults={'valor':1})
    return configuracion

@api_view(["GET"])
@csrf_exempt
def subir_xls(request):
    df = pd.read_excel("clientes.xls", sheet_name="hoja1")
    df = df.reset_index()
    print("inicio carga de data")
    for index, row in df.iterrows():
        instancia = Instancia.objects.get(id=1)
        empresa = Empresa.objects.get(id=row['EMPRESA'])
        vendedor, created = Vendedor.objects.get_or_create(codigo=row['VENDEDOR'], defaults={'instancia':instancia,'nombre': row['NOMBRE_VENDEDOR']})
        vendedor.save()
        nuevo_cliente, created = Cliente.objects.get_or_create(
            nombre=row['NOMBRE'],
            defaults={
                'instancia':instancia,
                'codigo':row['CODIGO'],
                'empresa': empresa,
                'vendedor':vendedor,
                'identificador':row['RIF'],
                'ubicacion':row['DIRECCION'],
                'telefono':row['TELEFONO'],
                'mail':row['EMAIL'],
                'credito':row['CREDITO'],
                'activo':row['ACTIVO']
            }
        )
        if(created):
            nuevo_cliente.save()
            print(nuevo_cliente)
    print("fin carga de data")
    data = {
        "crear": "data"
        }
    return JsonResponse(data)

@api_view(["GET"])
@csrf_exempt
def subir_xls2(request):
    print("Inicio de proceso")
    df = pd.read_excel("productos.xls", sheet_name="Hoja1")
    df = df.reset_index()  # make sure indexes pair with number of rows
    print("inico carga de data")
    for index, row in df.iterrows():
        instancia = Instancia.objects.get(id=2)
        marca, created = Marca.objects.get_or_create(nombre=row['MARCA'], defaults={'instancia':instancia,'nombre': row['MARCA']})
        marca.save()
        exonerado = True
        venta_sin_inventario= True
        lote= False
        if(row['IVA'] == 'SI'):
            exonerado = False
        if(row['VENTA_SIN_INVENTARIO'] == 'NO'):
            venta_sin_inventario = False
        if(row['LOTE'] == 'SI'):
            lote: True
        nuevo_producto, created = Producto.objects.get_or_create(
                            marca=marca,
                            nombre=row['DESCRIPCIÓN'],
                            defaults={
                            'instancia':instancia,
                            'nombre':row['DESCRIPCIÓN'],
                            'sku':row['CODIGO'],
                            'costo':row['Costo'],
                            'precio_1':row['Precio1'],
                            'precio_2':row['Precio2'],
                            'exonerado':exonerado,
                            'servicio': False,
                            'menejo_inventario': True,
                            'venta_sin_inventario':True,
                            'lote': lote,
                            'activo': True
                            }
                            )
        if(created):
            nuevo_producto.save()
            print(nuevo_producto)
    print("fin carga de data")
    data = {
        "crear": "data"
        }
    return JsonResponse(data)
from django.utils.timesince import timesince
@api_view(["POST", "GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def calcular_comisiones(request):
    perfil=Perfil.objects.get(usuario=request.user)
    data=request.data
    try:
        if verificar_permiso(perfil,'Comisiones','leer'):
            ini=data['fecha_inicio'].split('/')
            fin=data['fecha_fin'].split('/')
            fecha_inicio=ini[0]+'-'+ini[1]+'-'+ini[2]
            fecha_fin=fin[0]+'-'+fin[1]+'-'+fin[2]
            vendedor=Vendedor.objects.get(id=1)
            rango=[fecha_inicio,fecha_fin]
            tardio=timezone.now()-timezone.timedelta(weeks=4)
            notas=NotasPago.objects.filter(vendedor=vendedor,fecha__date__range=rango).exclude(fecha__date__lt=tardio)
            comision= {'total':0, 'objetos':[], 'info':{}}
            for n in notas:
                nota={'clienteNombre':n.cliente.nombre,'vendedorNombre':n.vendedor.nombre,'total':n.total,'detalles':[]}
                detalle=DetalleNotasPago.objects.filter(notapago=n)
                for d in detalle:
                    detalle = {'proforma':d.proforma.id,'saldo_anterior':d.saldo_anterior,'monto':d.monto}
                    proforma=Proforma.objects.get(id=d.proforma.id)
                    try:
                        if int(proforma.precio_seleccionadoo) in [1,2,4]:
                            comision['total'] += ((5*d.monto)/100)
                        else:
                            raise
                    except:
                        comision['total'] += ((3*d.monto)/100)
                    nota['detalles'].append(detalle)
                comision['objetos'].append(nota)
            return Response(comision,status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        print(e)
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)