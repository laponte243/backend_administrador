# Importes de Rest framework
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
from django.http import JsonResponse,HttpResponse,request,QueryDict
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
from numpy import indices, safe_eval
from xlwt import *
import pandas as pd
import csv
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
    authentication_classes=[BasicAuthentication]
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
    authentication_classes=[BasicAuthentication]
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

# Permisos de los usuarios
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
                excluir=[]
                for o in objetos:
                    if not o.bloqueado and not o.disponible:
                        excluir.append(o.id)
                objetos=objetos.exclude(id__in=excluir)
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
                codigo = None
                paginado=paginar(objetos,self.request.query_params.copy(),self.modelo)
                if not paginado['objetos']:
                    parametros=self.request.query_params.copy()
                    # Eliminar parametros de paginado
                    try: parametros.pop('p_pagina')
                    except: pass
                    try: parametros.pop('p_ordenar')
                    except: pass
                    try: parametros.pop('p_cantidad')
                    except: pass
                    # Extraer valor para buscar por codigo
                    extras=[]
                    for p in parametros.keys():
                        codigo = parametros[p] if not codigo or p == 'nombre__icontains' else codigo
                        extras.append(p)
                    if codigo:
                        params = self.request.query_params.copy()
                        params['codigo__icontains'] = codigo
                        for e in extras:
                            params.pop(e)
                        paginado=paginar(objetos,params,self.modelo)
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
            for d in DetallePedido.objects.filter(pedido=instance):
                if d.inventario:
                    inventario=Inventario.objects.get(id=d.inventario.id,producto=d.producto,lote__exact=d.lote)
                    modificar_inventario('devolver',inventario,d.cantidada)
                d.delete()
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
        # if verificar_permiso(perfil,'Pedido','escribir'):
        #     datos=request.data
        #     try:
        #         datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
        #     except:
        #         datos['instancia']=perfil.instancia.id
        #     serializer=self.get_serializer(data=datos)
        #     serializer.is_valid(raise_exception=True)
        #     self.perform_create(serializer)
        #     headers=self.get_success_headers(serializer.data)
        #     return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
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
        # perfil=obt_per(self.request.user)
        # if verificar_permiso(perfil,'Pedido','borrar'):
        #     instance=self.get_object()
        #     if instance.instancia==perfil.instancia or perfil.tipo=='S':
        #         if instance.inventario:
        #             inventario=Inventario.objects.get(id=instance.inventario.id)
        #             inventario.bloqueado=inventario.bloqueado-instance.cantidada
        #             inventario.disponible=inventario.disponible+instance.cantidada
        #             inventario.save()
        #         instance.delete()
        #         return Response(status=status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(status=status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
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
            datos['vendedor'] = Cliente.objects.get(id=datos['cliente']).vendedor.id
            datos['empresa'] = Cliente.objects.get(id=datos['cliente']).empresa.id
            try:
                datos['instancia']=obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            configuracion=verificar_numerologia(datos,self.modelo)
            # Arreglar fecha
            fecha=datos['fecha_comprobante'].split('/')
            datos['fecha_comprobante']=timezone.datetime(year=int(fecha[0]),month=int(fecha[1]),day=int(fecha[2]))
            # Serializar
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            # Correlativo
            configuracion.valor+=1
            configuracion.save()
            # Return
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
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(instancia=instancia)
                # objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                parametros=self.request.query_params.copy()
                excluidos=['p_pagina','p_ordenar','p_cantidad'] # Añadir aqui los parametros a excluir
                extras=[]
                objs_co=None
                objs_no=None
                for pa in parametros.keys():
                    if pa not in excluidos:
                        objs_co=objetos.filter(cliente__codigo__contains=parametros.get(pa))
                        objs_no=objetos.filter(**{pa:parametros.get(pa)})
                        extras.append(pa)
                objs=NotasPago()
                if objs_co and objs_co.count() > 0:
                    for o in objs_co:
                        objetos
                if objs_no and objs_no.count() > 0:
                    objs.append(objs_co)
                if len(extras) == 0:
                    objs = objetos
                for ex in extras:
                    parametros.pop(ex)
                paginado=paginar(objs,parametros,self.modelo)
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
            configuracion_control=verificar_numerologia(datos,'NotaControl')
            datos['numerologia']=configuracion.valor
            datos['control']=configuracion_control.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion_control.valor+=1
            configuracion.save()
            configuracion_control.save()
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
        context=super().get_context_data(*args,**kwargs)
        context['error'] = None
        try:
            if Token.objects.get(key=kwargs['token']):
                # Definicion de contenido extra para el template
                pedido=Pedido.objects.get(id=kwargs['id_pedido'])
                value={'data':[]}
                agrupador=DetallePedido.objects.filter(pedido=pedido).values('producto').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
                # Ciclo para generar Json y data para el template
                for dato in agrupador:
                    # Obtener producto
                    productox=Producto.objects.get(id=dato['producto'])
                    # Iniciar variable de los detalles
                    valuex={'datax':[]}
                    # Iniciar variables del pedido
                    total_cantidad=0
                    mostrar=True
                    detallado=DetallePedido.objects.filter(pedido=pedido,producto=productox).order_by('producto__id')
                    # Condiciones para mostrar o no los lotes y detalles
                    if productox.lote==True and len(detallado) > 1: # Conficion para cuando se debe mostrar el lote, y hay varios detalles, del producto
                        for detalle in detallado:
                            valuex['datax'].append({'lote':detalle.lote  if detalle.lote else 'Sin lote','cantidad':detalle.cantidada,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
                            total_cantidad += detalle.cantidada
                    else: # Conficion para cuando se debe mostrar el lote, y hay un solo detalle, del producto
                        mostrar=False
                        for detalle in detallado:
                            valuex['datax'] = {'lote':detalle.lote,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
                            total_cantidad += detalle.cantidada
                    # else: # Conficion para cuando no se debe mostrar el lote del producto
                    #     mostrar=False
                    #     for detalle in detallado:
                    #         total_cantidad += detalle.cantidada
                    #     valuex['datax']=None
                    # Agregar detalles al arreglo de detalles
                    value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad})
                # Setear los valores al template
                context['productos']=value['data']
                context['pedido']=pedido
                # Setear los valores de la empresa
                empresa=pedido.cliente.empresa
                context['empresa']=empresa
                context['logo'] = self.request.build_absolute_uri(empresa.logo.url)
                return context
            else:
                raise Exception('Token del usuario invalido')
        except Exception as e:
            context['error'] = e
            return context

# Generar pagina tipo PDF para proformas
class ProformaPDF(PDFView):
    template_name='proforma.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        context=super().get_context_data(*args,**kwargs)
        context['error'] = None
        try:
            if Token.objects.get(key=kwargs['token']):
                # Definicion de contenido extra para el template
                context=super().get_context_data(*args,**kwargs)
                proforma=Proforma.objects.get(id=kwargs['id_proforma'])
                value={'data':[]}
                total_exento=0
                total_imponible=0
                total_calculado=0
                agrupador=DetalleProforma.objects.filter(proforma=proforma).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
                # Ciclo para generar Json y data para el template
                for dato in agrupador:
                    # Obtener producto
                    productox=Producto.objects.get(id=dato['producto'])
                    # Verficar exonerado
                    if productox.exonerado == False:
                        total_imponible += round(dato['total'],2)
                    else:
                        total_exento += round(dato['total'],2)
                    # Iniciar variable de los detalles
                    valuex={'datax':[]}
                    # Iniciar variables de la proforma
                    total_cantidad=0
                    precio_unidad=0
                    costo_total=0
                    mostrar=True
                    detallado=DetalleProforma.objects.filter(proforma=proforma,producto=productox).order_by('producto__id')
                    # Condiciones para mostrar o no los lotes y detalles
                    if productox.lote==True and len(detallado) > 1: # Condicion para cuando se debe mostrar el lote, y hay varios detalles, del producto
                        for detalle in detallado:
                            valuex['datax'].append({'lote':detalle.lote if detalle.lote else 'Sin lote','cantidad':detalle.cantidada,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
                            total_cantidad += detalle.cantidada
                            precio_unidad=round(detalle.precio,2)
                    else: # Condicion para cuando se debe mostrar el lote, y hay un solo detalle, del producto
                        mostrar=False
                        for detalle in detallado:
                            valuex['datax'] = {'lote':detalle.lote,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
                            total_cantidad += detalle.cantidada
                            precio_unidad=round(detalle.precio,2)
                    # else: # Condicion para cuando no se debe mostrar el lote del producto
                    #     mostrar=False
                    #     for detalle in detallado:
                    #         total_cantidad += detalle.cantidada
                    #         precio_unidad=round(detalle.precio,2)
                    #     valuex['datax']=None
                    # Obtener los costos totales
                    costo_total=float(precio_unidad) * float(total_cantidad)
                    total_calculado += round(costo_total,2)
                    # Agregar detalles al arreglo de detalles
                    value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':precio_unidad,'total_producto':round(costo_total,2)})
                # Sumatoria de los exentos valores
                total_real=(total_imponible + total_exento)
                # 16% (IVA)
                iva=round(total_imponible*(16/100),2)
                if total_imponible:
                    total_real=total_real+iva
                # Setear los valores al template
                context['productos']=value['data']
                context['proforma']=proforma
                context['subtotal']=round(total_calculado,2)
                context['imponible']=round(total_imponible,2)
                context['monto_exento']=round(total_exento,2)
                context['impuesto']=iva
                context['total']=round(total_real,2)
                # Setear los valores de la empresa
                empresa=proforma.cliente.empresa
                context['empresa']={'nombre':empresa.nombre.upper(),'logo':'media/'+empresa.logo.name.split('/')[2],'correo':empresa.correo,'telefono':empresa.telefono,'direccion':empresa.direccion}
                return context
            else:
                raise Exception('Token del usuario invalido')
        except Exception as e:
            print(e)
            context['error'] = e
            return context

# Generar pagina tipo PDF para facturas
class FacturaPDF(PDFView):
    template_name='factura.html'
    allow_force_html=True
    def get_context_data(self,*args,**kwargs):
        context=super().get_context_data(*args,**kwargs)
        context['error'] = None
        try:
            if Token.objects.get(key=kwargs['token']):
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
                total_exento=0
                total_imponible=0
                total_calculado=0
                # Ciclo para generar Json y data para el template
                for dato in DetalleFactura.objects.filter(factura=factura).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada')):
                    productox=Producto.objects.get(id=dato['producto'])
                    if productox.exonerado == False:
                        total_imponible += dato['total']
                    else:
                        total_exento += dato['total']
                    valuex={'datax':[]}
                    total_cantidad=0
                    precio_unidad=0.0
                    costo_total=0.0
                    mostrar=True
                    detallado=DetalleFactura.objects.filter(factura=factura,producto=productox).order_by('producto__id')
                    if productox.lote==True and len(detallado) > 1:
                        for detalle in detallado:
                            valuex['datax'].append({'lote':detalle.lote if detalle.lote else 'Sin lote','cantidad':detalle.cantidada,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
                            total_cantidad += int(detalle.cantidada)
                            precio_unidad=float(detalle.precio) * conversion.valor
                    elif productox.lote==True and len(detallado)==1:
                        valuex['datax']=''
                        mostrar=False
                        for detalle in detallado:
                            valuex['datax'] = {'lote':detalle.lote,'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
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
                    value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':round(precio_unidad,2),'total_producto':round(costo_total,2)})
                subtotal_conversion=subtotal * conversion.valor
                # Sumatoria de los no exentos (Imponible)
                total_imponible = total_imponible * conversion.valor
                # Sumatoria de los exentos (Exonerados)
                total_exento = total_exento * conversion.valor
                total_real=(total_imponible + total_exento)
                # 16% (IVA)
                iva=round(total_imponible*(16/100),2)
                if total_imponible:
                    total_real=total_real+iva
                # Setear los valores al template
                context['productos']=value['data']
                context['subtotal']=round(subtotal_conversion,2)
                context['imponible']=round(total_imponible,2)
                context['monto_exento']=round(total_exento,2)
                context['impuesto']=iva
                context['total']=round(total_real,2)
                context['factura']=factura
                # Setear los valores de la empresa
                empresa=factura.proforma.cliente.empresa
                context['empresa']={'nombre':empresa.nombre.upper(),'logo':'media/'+empresa.logo.name.split('/')[2],'correo':empresa.correo,'telefono':empresa.telefono,'direccion':empresa.direccion}
                return context
            else:
                raise Exception('Token del usuario invalido')
        except Exception as e:
            context['error'] = e
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
            # Obtener inventarios de la instancia
            inventarios=Inventario.objects.filter(instancia=perfil.instancia)
            # Ciclo para sacar los inventarios vacios
            for o in inventarios:
                if o.disponible==0 and o.bloqueado==0:
                    inventarios=inventarios.exclude(id=o.id)
            # Sumar los inventarios del mismo producto en el mismo almacen
            inventarios=inventarios.values('almacen','almacen__nombre','producto','producto__nombre').annotate(sum_disponible=Sum('disponible'),sum_bloqueado=Sum('bloqueado'))
            # Iniciar Diccionario de django para los filtros
            diccionario = QueryDict('', mutable=True)
            # Obtener JSON/Dict 
            json=verificar_filtros_inventario(['almacen__nombre','producto__nombre'],request.query_params.copy())
            if json: diccionario.update(json)
            inventarios_p=paginar(inventarios,diccionario,modelo)
            return Response(inventarios_p,status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

# Funcion para verificar los filtros al hacer la busqueda de los inventarios
def verificar_filtros_inventario(valores,parametros):
    diccionario=dict()
    # Guardar p_pagina al diccionario
    try: diccionario['p_pagina']=parametros.get('p_pagina')
    except: pass
    # Guardar p_ordenar al diccionario
    try:
        ordenar=parametros.get('p_ordenar')
        if ((ordenar == 'almacen' or ordenar == 'producto') or (ordenar == '-almacen' or ordenar == '-producto')) or ((ordenar == 'almacen__nombre' or ordenar == 'producto__nombre') or (ordenar == '-almacen__nombre' or ordenar == '-producto__nombre')):
            diccionario['p_ordenar']=ordenar
    except Exception as e: pass
    # Guardar p_cantidad al diccionario
    try: diccionario['p_cantidad']=parametros.get('p_cantidad')
    except: pass
    for p in parametros:
        campos=p.split('__')
        for v in valores:
            campo=v.split('__')
            if campos[0] == campo[0]:
                diccionario[p]=parametros.get(p)
    return diccionario

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

# Funcion tipo vista para borrar las notas
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def borrar_nota(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Notasdepago','borrar'):
        payload=json.loads(request.body)
        try:
            nota=NotasPago.objects.get(id=payload['idNota'])
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
                        proforma=Proforma.objects.get(id=obj['proforma'])
                        detalle_original = DetalleNotasPago.objects.filter(notapago=payload['idNota'],proforma=proforma).first()
                        if detalle_original:
                            proforma.saldo_proforma=proforma.saldo_proforma + detalle_original.monto
                            proforma.save()
                            detalle_original.delete()
                        perfil=Perfil.objects.get(usuario=request.user)
                        instancia=Instancia.objects.get(perfil=perfil.id)
                        nota_pago=NotasPago.objects.get(id=payload['idNota'])
                        detalle_nota=DetalleNotasPago(instancia=instancia,proforma=proforma,notapago=nota_pago,monto=obj['monto'],saldo_anterior=obj['saldo_anterior'])
                        detalle_nota.save()
                        proforma.saldo_proforma=proforma.saldo_proforma - detalle_nota.monto
                        proforma.save()
                except Exception as e:
                    print(e)
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
    instancia=Instancia.objects.get(perfil=perfil.id)
    info={'errores':[]}
    if verificar_permiso(perfil,'Pedido','actualizar'):
        # Cargar la data recibida
        nuevos_detalles=request.data['detalles']
        try:
            # Obtener pedido
            pedido=Pedido.objects.get(id=request.data['id_pedido'])
            # Salvar los detalles antiguos del pedido
            viejos_detalles=DetallePedido.objects.filter(pedido=pedido)
            # Iniciar total del pedido
            total=0
            # Borrar los detalles antiguos del pedido
            for d in viejos_detalles:
                try:
                    # Modificar el inventario si existe
                    if d.inventario:
                        inventario=Inventario.objects.get(id=d.inventario.id,producto=d.producto,lote__exact=d.lote)
                        retornado=modificar_inventario('devolver',inventario,d.cantidada) if inventario else 'Inventario no encontrado'
                        if retornado:
                            raise Exception(retornado)
                except Exception as e:
                    # Guardar Error
                    info['errores'].append({'code':'404','error':str(e)})
                # Eliminar detalle
                d.delete()
            # Guardar los nuevos detalles del pedido
            for d in nuevos_detalles:
                try:
                    # Obtener inventario del nuevo pedido
                    inventario=None if not d['inventario'] else Inventario.objects.get(id=d['inventario'])
                    # Obtener producto
                    producto=Producto.objects.get(id=d["producto"])
                    # Obtener el precio seleccionado del producto y su cantidad en el pedido
                    precio_seleccionado=float(d['precio_seleccionado'])
                    cantidad=int(d['cantidada'])
                    # Calcular el precio de cada producto segun la cantidad
                    total_producto=cantidad * precio_seleccionado
                    # Sumar al precio final 
                    total+=total_producto
                    # Crear detalle
                    nuevo_detalle=DetallePedido(lote=d["lote"],total_producto=total_producto,precio_seleccionado=precio_seleccionado,instancia_id=instancia.id,pedido=pedido,cantidada=cantidad,producto=producto,inventario=inventario)
                    nuevo_detalle.save()
                    # Encaso de tener un inventario, modificarlo
                    if inventario:
                        retornado=modificar_inventario('bloquear',inventario,cantidad)
                        if retornado:
                            raise Exception(retornado)
                except Exception as e:
                    info['errores'].append({'code':'404','error':str(e)})
            # Modificar total y guardar pedido
            pedido.total=total
            pedido.save()
            return Response(info,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

# Funcion para modificar las cantidades del inventario
def modificar_inventario(tipo,inventario,cantidad):
    if inventario:
        # Buscar u obtener Query de inventario
        inventario=Inventario.objects.get(id=inventario) if isinstance(inventario, int) else inventario
        # Si el tipo de movimiento es devolver, suma al disponible y resta al bloqueado
        if tipo == 'devolver':
            inventario.disponible += cantidad
            inventario.bloqueado -= cantidad
        # Si el tipo de movimiento es bloquear, suma al bloqueado y resta al disponible
        elif tipo == 'bloquear':
            inventario.disponible -= cantidad
            inventario.bloqueado += cantidad
        # Guardar inventario
        inventario.save()
        return False # False signifca que no hubo error
    else:
        return 'Falta asignar un inventario'

# Funcion tipo vista para hacer la validacion de los pedidos
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validar_pedido(request):
    payload=request.data
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Pedido','actualizar'):
        try:
            pedido=Pedido.objects.get(id=payload['idpedido'])
            detashepedido=DetallePedido.objects.filter(pedido=pedido)
            perfil=Perfil.objects.get(usuario=request.user)
            instancia=Instancia.objects.get(perfil=perfil.id)
            if payload['decision']=='Rechazado':
                pedido.estatus='C'
                pedido.save()
                for deta in detashepedido:
                    try:
                        inventario=Inventario.objects.get(id=deta.inventario.id)
                        inventario.bloqueado=inventario.bloqueado-deta.cantidada
                        inventario.disponible=inventario.disponible+deta.cantidada
                        inventario.save()
                    except:
                        pass
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
                    inventario = None
                    try:
                        inventario=Inventario.objects.get(id=deta.inventario.id)
                        inventario.bloqueado=inventario.bloqueado - deta.cantidada
                        inventario.save()
                    except:
                        pass
                    nuevo_detalle=DetalleProforma(
                        proforma=nueva_proforma,
                        precio_seleccionado=deta.precio_seleccionado,
                        inventario=inventario,
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
                return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

# Funcion tipo vista para generar facturas
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def generar_factura(request):
    payload=request.data
    perfil=Perfil.objects.get(usuario=request.user)
    instancia=Instancia.objects.get(perfil=perfil.id)
    if verificar_permiso(perfil,'Factura','escribir'):
        try:
            # Obtener proforma
            proforma = Proforma.objects.get(id=payload['idproforma'])
            # En caso de generar una factura como peticion directa, verificar existencia de una factura asociada a la proforma
            factura = Factura.objects.filter(proforma=proforma).first()
            if factura:
                # Anular factura encontrada
                factura.proforma = None
                factura.save()
            # Obtener detalles de la proforma
            detasheproforma=DetalleProforma.objects.filter(proforma=proforma)
            # Obtener correlativo/configuracion/numerologia/papeleria del la factura y la nota de control
            configuracion=verificar_numerologia({'empresa':proforma.empresa.id,'instancia':proforma.instancia.id},Factura)
            configuracion_control=verificar_numerologia({'empresa':proforma.empresa.id,'instancia':proforma.instancia.id},'NotaControl')
            # Iniciar factura
            nueva_factura=Factura(proforma=proforma,origen=proforma.id,instancia=instancia)
            # Definir correlativos
            nueva_factura.numerologia=configuracion.valor
            nueva_factura.control=configuracion_control.valor
            # Definir valores de la empresa
            nueva_factura.nombre_empresa=proforma.empresa.nombre
            nueva_factura.direccion_empresa=proforma.empresa.direccion
            # Definir valores del cliente
            nueva_factura.nombre_cliente=proforma.cliente.nombre
            nueva_factura.codigo_cliente=proforma.cliente.codigo
            nueva_factura.identificador_fiscal=proforma.cliente.identificador
            nueva_factura.direccion_cliente=proforma.cliente.ubicacion
            nueva_factura.telefono_cliente=proforma.cliente.telefono
            nueva_factura.correo_cliente=proforma.cliente.mail
            # Definir valores del vendedor
            nueva_factura.nombre_vendedor=proforma.vendedor.nombre
            nueva_factura.codigo_vendedor=proforma.vendedor.codigo
            nueva_factura.telefono_vendedor=proforma.vendedor.telefono
            # Extras
            nueva_factura.impuesto=16
            # Guardar factura
            nueva_factura.save()
            # Modificar correlativos
            configuracion.valor+=1
            configuracion_control.valor+=1
            configuracion.save()
            configuracion_control.save()
            # Iniciar valores de los detales para la factura
            subtotal=0
            imponible=0
            exento=0
            impuesto=16
            total_real=0
            # Ciclo para crear los detalles
            for deta in detasheproforma:
                inventario = None
                try:
                    # Obtener inventario
                    inventario=deta.inventario if deta.inventario else None
                    inventario_id=inventario.id if inventario else None
                    vencimiento=inventario.fecha_vencimiento if inventario else None
                except:
                    pass
                # Iniciar nuevo detalle de la factura
                nuevo_detalle=DetalleFactura(
                    factura=nueva_factura,
                    inventario=inventario,
                    inventario_fijo=inventario_id,
                    cantidada=deta.cantidada,
                    lote=deta.lote,
                    fecha_vencimiento=vencimiento,
                    producto=deta.producto,
                    producto_fijo=deta.producto.nombre,
                    precio=deta.precio_seleccionado,
                    total_producto=round(deta.total_producto,2),
                    instancia=instancia)
                # Guardar detalle
                nuevo_detalle.save()
                # Obtener imponible del detalle si no es exonerado
                if nuevo_detalle.producto.exonerado == False:
                    imponible += nuevo_detalle.total_producto
                # Obtener exento del detalle si es exonerado
                else:
                    exento += nuevo_detalle.total_producto
            # Calcular valor total
            subtotal=round(imponible,2) + round(exento,2)
            total_real=round(subtotal,2)
            # Calcular imponible
            if imponible:
                # Sumar al total
                total_real=round(total_real,2)+(round(imponible,2)*(impuesto/100))
            # Modificar total y subtotal de la factura
            nueva_factura.subtotal = round(subtotal,2)
            nueva_factura.total = round(total_real,2)
            # Guardar modificacion
            nueva_factura.save()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': (e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def anular_factura(request):
    perfil = Perfil.objects.get(usuario=request.user)
    data = request.data
    if verificar_permiso(perfil,'Factura','escribir'):
        try:
            factura = Factura.objects.get(id=data['id'])
            factura.origen = factura.proforma.id if not factura.origen else factura.origen
            factura.proforma = None
            factura.save()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({'error': (e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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

# Funcion tipo vista para generar Excel de precios de productos
@api_view(["GET"])
@csrf_exempt
def vista_xls(request):
    params=request.query_params.copy()
    token=params.get('token').split(' ')[1]
    if Token.objects.get(key=token):
        perfil=Perfil.objects.get(usuario=1)
        if verificar_permiso(perfil,'Productos','leer'):
            # Crear archivo temporal
            response=HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition']='attachment;filename="productos.xls"'
            # Iniciar Excel
            excel_wb=Workbook(encoding='utf-8')
            excel_ws=excel_wb.add_sheet('Hoja1') # ws es Work Sheet
            # Añadiendo estilo
            excel_ws.col(0).width = 11600 # Tamaño columna nombre marca
            excel_ws.col(1).width = 8000 # Tamaño columna codigo producto
            excel_ws.col(2).width = 13000 # Tamaño columna nombre producto
            estilo=easyxf('font: bold 1')
            i=0 # Saltador de fila
            # Escribir nombres de las columnas
            excel_ws.write(i,0,'MARCA',estilo)
            excel_ws.write(i,1,'CODIGO',estilo)
            excel_ws.write(i,2,'DESCRIPCIÓN',estilo)
            excel_ws.write(i,3,'COSTO',estilo)
            excel_ws.write(i,4,'PRECIO 1',estilo)
            excel_ws.write(i,5,'PRECIO 2',estilo)
            excel_ws.write(i,6,'PRECIO 3',estilo)
            excel_ws.write(i,7,'PRECIO 4',estilo)
            i=i+1 # Saltar fila
            # Ciclo por cada marca
            for m in Marca.objects.all().order_by('prioridad').values():
                # Ciclo por cada producto
                for p in Producto.objects.filter(marca=m['id']).values():
                    # Escribir productos
                    excel_ws.write(i,0,m['nombre']) # Nombre marca
                    excel_ws.write(i,1,p['sku']) # Codigo producto
                    excel_ws.write(i,2,p['nombre']) # Nombre producto
                    excel_ws.write(i,3,p['costo']) # Costo producto
                     # Precios del producto
                    excel_ws.write(i,4,p['precio_1'])
                    excel_ws.write(i,5,p['precio_2'])
                    excel_ws.write(i,6,p['precio_3'])
                    excel_ws.write(i,7,p['precio_4'])
                    i=i+1 # Saltar fila
            # Guardar excel en el archivo temporal
            excel_wb.save(response)
            # Restornar archivo
            return response
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)

# Funcion tipo vista para generar Excel de las comisiones
@api_view(["POST","GET"])
@csrf_exempt
def comision(request):
    params=request.query_params.copy()
    token=params.get('token').split(' ')[1]
    user = Token.objects.get(key=token).user
    if user:
        data={'fecha_inicio':params.get('fecha_inicio'),'fecha_fin':params.get('fecha_fin'),'vendedor':params.get('vendedor')}
        perfil=Perfil.objects.get(usuario=user)
        try:
            if verificar_permiso(perfil,'Comisiones','leer'):
                """ Data inicial """
                # Obtner Vendedor para el filtro
                vendedor=Vendedor.objects.get(id=data['vendedor'])
                # Obtner el rango de fechas para el filtro
                ini=data['fecha_inicio'].split('/')
                fecha_inicio=ini[0]+'-'+ini[1]+'-'+ini[2] # Formateando Date inicial para timezone
                fin=data['fecha_fin'].split('/')
                fecha_fin=fin[0]+'-'+fin[1]+'-'+fin[2] # Formateando Date final para timezone
                rango=[fecha_inicio,fecha_fin] # Rango
                tardio=timezone.now()-timezone.timedelta(weeks=4) # Tiempo maximo de 30 dias
                # Filtrar Notas de pago
                notas=NotasPago.objects.filter(vendedor=vendedor,fecha_comprobante__date__range=rango)
                # Excel
                i=0
                response=HttpResponse(content_type='application/ms-excel')
                response['Content-Disposition']='attachment;filename="comision_%s_%s&%s.xls"'%(vendedor.codigo,fecha_inicio,fecha_fin)
                excel_wb=Workbook(encoding='utf-8')
                excel_ws=excel_wb.add_sheet('Comisiones') # ws es Work Sheet
                # Añadiendo estilo
                excel_ws.col(0).width = 2500 # Tamaño columna numero de nota
                excel_ws.col(1).width = 3500 # Tamaño columna numero de comporbante
                excel_ws.col(2).width = 5000 # Tamaño columna fecha de comporbante
                excel_ws.col(3).width = 2500 # Tamaño columna numero de proforma
                excel_ws.col(4).width = 5000 # Tamaño columna fecha despacho
                excel_ws.col(5).width = 5000 # Tamaño columna precio seleccionado
                excel_ws.col(6).width = 3500 # Tamaño columna total proforma
                excel_ws.col(7).width = 3500 # Tamaño columna monto pagado
                estilo=easyxf('font: bold 1')
                # Primera fila del excel
                excel_ws.write(i,0,'Nº Nota',estilo)
                excel_ws.write(i,1,'Nº Comprobante',estilo)
                excel_ws.write(i,2,'Fecha comprobante',estilo)
                excel_ws.write(i,3,'Nº Proforma',estilo)
                excel_ws.write(i,4,'Fecha despacho',estilo)
                excel_ws.write(i,5,'Precio seleccionado',estilo)
                excel_ws.write(i,6,'Total proforma',estilo)
                excel_ws.write(i,7,'Monto pagado',estilo)
                excel_ws.write(i,8,'Comision',estilo)
                i=i+1
                total_comision=0
                # Creador de filas
                for n in notas:
                    correlativo_nota=ConfiguracionPapeleria.objects.get(empresa=n.cliente.empresa,tipo="N")
                    excel_ws.write(i,0,'%s%s'%(correlativo_nota.prefijo+'-' if correlativo_nota.prefijo else '',n.numerologia))
                    excel_ws.write(i,1,'%s'%(n.comprobante))
                    excel_ws.write(i,2,'%s'%(n.fecha.date()))
                    detalle=DetalleNotasPago.objects.filter(notapago=n)
                    for d in detalle:
                        comision=0
                        # Añadir detalle de la nota
                        correlativo_prof=ConfiguracionPapeleria.objects.get(empresa=d.proforma.empresa,tipo="E")
                        excel_ws.write(i,3,'%s%s'%(correlativo_prof.prefijo+'-' if correlativo_prof.prefijo else '',n.numerologia))
                        excel_ws.write(i,4,'%s'%(d.proforma.fecha_despacho.date() if d.proforma.fecha_despacho else 'S/D' ))
                        excel_ws.write(i,5,'%s'%(d.proforma.precio_seleccionadoo))
                        excel_ws.write(i,6,'%s'%(round(d.proforma.total,2)))
                        excel_ws.write(i,7,'%s'%(d.monto))
                        # Calcular comision
                        proforma=Proforma.objects.get(id=d.proforma.id)
                        if d.proforma.fecha_despacho:
                            if (d.proforma.fecha_despacho.date() - n.fecha_comprobante.date()).days < 30:
                                if proforma.precio_seleccionadoo in ['precio_1','precio_2','precio_4']:
                                    comision = round(((5*d.monto)/100),2)
                                else:
                                    comision = round(((3*d.monto)/100),2)
                            total_comision+=comision
                            excel_ws.write(i,9,'%s'%('Despachado'))
                        else:
                            excel_ws.write(i,9,'%s'%('Sin despachar'))
                        excel_ws.write(i,8,'%s'%(comision))
                        # excel_ws.write(i,6,'%s'%())
                        i=i+1
                excel_ws.write(i,7,'%s'%('Total:'),estilo)
                excel_ws.write(i,8,'%s'%(round(total_comision,2)))
                excel_wb.save(response)
                return response
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e)
            return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)

# Funcion tipo vista para generar Excel del credito de los clientes
@api_view(["GET"])
@csrf_exempt
def calcular_credito(request):
    params=request.query_params.copy()
    # Verificar token del usuario
    token=params.get('token').split(' ')[1]
    user = Token.objects.get(key=token).user
    if user:
        # Obtener cliente
        cliente=Cliente.objects.get(id=params.get('id'))
        # Obtener correlativo proforma
        correlativo_pro=ConfiguracionPapeleria.objects.get(empresa=cliente.empresa,tipo="E")
        # Obtener proformas
        p=[]
        proformas =Proforma.objects.filter(cliente=cliente)
        for pro in proformas:
            factura = Factura.objects.filter(proforma=pro)
            p.append({'doc':'proforma','fecha':pro.fecha_proforma,'pre_doc':correlativo_pro.prefijo if correlativo_pro.prefijo else '','num_doc':pro.numerologia,'monto':str(round(pro.saldo_proforma,2)).replace('.',','),'fecha_b': pro.fecha_despacho.date() if pro.fecha_despacho else '','factura':factura.values_list('id') if factura else None})
        # Obtener correlativo nota de pago
        correlativo_npa=ConfiguracionPapeleria.objects.get(empresa=cliente.empresa,tipo="N")
        # Obtener nota de pago
        n=[]
        for npa in NotasPago.objects.filter(cliente=cliente):
            factura = None
            n.append({'doc':'not_pago','fecha':npa.fecha,'pre_doc':correlativo_npa.prefijo if correlativo_npa.prefijo else '','num_doc':npa.numerologia,'monto':str(round(npa.total,2)).replace('.',','),'fecha_b':npa.fecha_comprobante.date(),'factura':'*' if factura else None})
        # Generar Dataframes
        data_excel = pd.DataFrame(p)
        data_excel_2 = pd.DataFrame(n)
        # Fusionas Dataframes y ordenar por fecha
        data_excel = data_excel.append(data_excel_2, ignore_index=True)
        data_excel = data_excel.sort_values(by='fecha',ascending=True)
        # Iniciar Excel
        response=HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition']='attachment;filename="deuda_%s.xls"'%(cliente.nombre)
        excel_wb=Workbook(encoding='utf-8')
        excel_ws=excel_wb.add_sheet('Credito') # ws es Work Sheet
        # Iniciar valores del Excel
        i=0 # Salto de linea
        total=0 # Deuda total del cliente
        # Añadiendo estilo
        estilo=easyxf('font: bold 1') # Estilo especial a campos y casillas importantes
        excel_ws.col(3).width = 6000 # Tamaño columna total proforma
        excel_ws.col(4).width = 6000 # Tamaño columna monto pagado
        # Definir cliente
        excel_ws.write(i,0,'Cliente:',estilo)
        excel_ws.write(i,1,cliente.nombre)
        # Definir vendedor
        excel_ws.write(i,2,'Vendedor:',estilo)
        excel_ws.write(i,3,cliente.vendedor.nombre)
        i+=1 # Salto de linea
        # Excribir campos
        excel_ws.write(i,0,'Fecha',estilo)
        excel_ws.write(i,1,'Doc',estilo)
        excel_ws.write(i,2,'Monto',estilo)
        excel_ws.write(i,3,'Fecha',estilo)
        excel_ws.write(i,4,'Factura',estilo)
        for index, row in data_excel.iterrows():
            if row.monto != '0':
                i+=1 # Salto de linea
                # Escribir valores del documento
                excel_ws.write(i,0,'%s'%(row.fecha.date()))
                excel_ws.write(i,1,'%s%s'%(row.pre_doc if row.pre_doc + '-' else '',row.num_doc))
                number_style = XFStyle()
                number_style.num_format_str = '0.00'
                excel_ws.write(i,2,row.monto,number_style)
                if row.fecha_b:
                    excel_ws.write(i,3,'%s%s'%(row.fecha_b, ' (Despacho)' if row.doc == 'proforma' else ' (Comprobante)'))
                else:
                    excel_ws.write(i,3,'Sin despachar')
                if row.factura:
                    fac = Factura.objects.filter(id__in=row.factura).first()
                    correlativo_fac = ConfiguracionPapeleria.objects.get(empresa=cliente.empresa,tipo="F")
                    excel_ws.write(i,4,'%s%s (%s)'%(correlativo_fac.prefijo+'-' if correlativo_fac.prefijo else '', fac.numerologia if fac else '',fac.fecha_factura.date()))
                else:
                    excel_ws.write(i,4,'Sin factura' if row.doc == 'proforma' else '')
                # Calular total
                if row.doc=='proforma':
                    total+=round(float(row.monto.replace(',','.')),2) # Aumentar deuda
                elif row.doc=='not_pago':
                    total-=round(float(row.monto.replace(',','.')),2) # Disminuir deuda
        i+=1 # Salto de linea
        excel_ws.write(i,1,'%s'%('Saldo pendiente:'),estilo)
        excel_ws.write(i,2,'%s'%(str(total).replace('.',',')))
        # Guardado temporal del excel
        excel_wb.save(response)
        # Retornar y generar
        return response
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
        total_actual=Proforma.objects.filter(fecha_proforma__range=(antes,ahora)).aggregate(cantidad=Round(Sum('total')))
        mucho_antes=antes-timezone.timedelta(weeks=4)
        mucho_antes=mucho_antes.replace(day=1)
        total_anterior=Proforma.objects.filter(fecha_proforma__range=(mucho_antes,antes)).aggregate(cantidad=Round(Sum('total')))
        total={'actual':{'fecha':antes,'total':total_actual,},'anterior':{'fecha':mucho_antes,'total':total_anterior,},}
        return Response(total,status=status.HTTP_200_OK)
    except Exception as e:
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Funcion para redondear decimales en los Sum y Avg
class Round(Func):
    function = 'ROUND'
    template='%(function)s(%(expressions)s, 2)'

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
            permiso,create = Permiso.objects.get_or_create(instancia=perfil.instancia,menuinstancia=p,perfil=perfil,defaults={'leer':True,'escribir':True,'borrar':True,'actualizar':True})
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

# Funcion para añadir clientes y vendedores
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def subir_xls2(request):
    if not request.FILES['file']:
        df = pd.read_excel("productos.xls", sheet_name="Hoja1")
        df = df.reset_index()  # make sure indexes pair with number of rows
    else:
        df = pd.read_excel(request.FILES['file'])
    for index, row in df.iterrows():
        if row['CODIGO']:
            instancia = Instancia.objects.all().first()
            try:
                perfil = Perfil.objects.get(user=request.user)
                instancia = Instancia.objects.get(id=perfil.instancia)
            except:
                pass
            marca, created = Marca.objects.get_or_create(nombre=row['MARCA'], defaults={'instancia':instancia,'nombre': row['MARCA']})
            marca.save()
            exonerado = True
            venta_sin_inventario= True
            lote= False
            try:
                if(row['EXCENTO'] != 'SI'):
                    exonerado = False
            except:
                pass
            try:
                if(row['VENTA_SIN_INVENTARIO'] == 'NO'):
                    venta_sin_inventario = False
            except:
                pass
            try:
                if(row['LOTE'] == 'SI'):
                    lote: True
            except:
                pass
            nuevo_producto, created = Producto.objects.get_or_create(
                marca=marca,
                nombre=row['DESCRIPCIÓN'],
                sku=row['CODIGO'],
                defaults={
                    'instancia':instancia,
                    'costo':row['COSTO'],
                    'precio_1':row['PRECIO 1'],
                    'precio_2':row['PRECIO 2'],
                    'precio_3':row['PRECIO 3'],
                    'precio_4':row['PRECIO 4'],
                    'lote': lote,
                    'exonerado':exonerado,
                    'venta_sin_inventario':venta_sin_inventario,
                    'servicio': False,
                    'menejo_inventario': True,
                    'activo': True
                }
            )
            if(created):
                nuevo_producto.save()
            else:
                nuevo_producto.costo=row['COSTO']
                nuevo_producto.precio_1=row['PRECIO 1']
                nuevo_producto.precio_2=row['PRECIO 2']
                nuevo_producto.precio_3=row['PRECIO 3']
                nuevo_producto.precio_4=row['PRECIO 4']
                nuevo_producto.save()
    return Response('Carga de productos terminada',status=status.HTTP_200_OK)

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
    # Intenta conseguir la pagina actual
    try: pagina=int(parametros.get('p_pagina')); parametros.pop('p_pagina')
    # Si no, devuelve la primera pagina
    except: pagina=1
    # Intenta conseguir el valor por cual ordenar los objetos
    try: ordenar=parametros.get('p_ordenar'); parametros.pop('p_ordenar')
    # Si no, lo ordena por id (del mas nuevo al mas antiguo)
    except: ordenar=''
    # Intenta conseguir la cantidad de objetos en la pagina
    try:
        cantidad=int(parametros.get('p_cantidad')); parametros.pop('p_cantidad')
        if cantidad>100: raise # Si se detectan mas de cien objetos, lanza un raise
    # Si no, devuelve cincuenta como generico
    except: errores.append({'code':404,'valor':'%s'%('La cantidad dada no es aceptable')}); cantidad=50
    # Intentar obtener objetos por filtro
    filtros=[]
    if parametros:
        # Ciclo por cada campo del diccionario
        for p in parametros.keys():
            try:
                # Separar el filtro por campos y opciones (model/field__extra/field...)
                campos=p.split('__')
                # Obtener el valor del campo
                valores=parametros.get(p)
                # Verificar si el filtro busca con un arreglo
                if campos[-1]=='in' or campos[-1]=='range':
                    # Si hace la busqueda con un arreglo,
                    # separar el valor del parametro (string) en varios objetos (array) por cada coma (',')
                    valores=valores.split(',')
                # Hacer un filtro especial (por argumentos definidos) en los objetos a paginar
                objetos=objetos.filter(**{p: valores}) if parametros.get(p) else objetos
                # if not primeros and multi:
                #     segundos = objetos
                #     for m in multi:
                #         segundos = segundos.filter(**{m: valores}) if parametros.get(p) else objetos
                #     objetos = segundos
                # else:
                # objetos = primeros
                # Salvar informacion del filtro 
                filtros.append({'campo':p,'valor':valores})
            except Exception as e:
                # Salvar informacion del error en filtro
                errores.append({'code':500,'valor':'%s'%(e)}) # Ej: "'nobre' no es un campo existente en el modelo 'Clientes'"
                # No hacer filtro
                objetos=objetos
    # Intentar ordenar los objetos
    try:
        objetos=objetos.order_by(ordenar) if len(ordenar) > 0 else objetos
    except Exception as e:
        # Salvar informacion del error al ordenar
        errores.append({'code':404,'valor':'%s'%(e)})
        # No hacer ordenado
        objetos=objetos
    # Variables
    devueltos=[]
    vuelta=1
    page=1
    id=0
    # Ciclo while para hacer la paginacion
    try:
        while True:
            # Si la pagina en el ciclo es la misma que la pagina solicitada agregar objeto a los devueltos
            if page==pagina:
                try:
                    devueltos.append(objetos[id])
                except:
                    pass
            # Si la vuelta del ciclo es igual a la cantidad solicitada
            if vuelta==cantidad:
                page+=1 # Saltar pagina del ciclo
                vuelta=0 # Reiniciar vuelta del ciclo
                # Si la pagina en el ciclo es mayor que la pagina solicitada, terminar ciclo
                if page>pagina:
                    break
            vuelta+=1 # Saltar vuelta del ciclo
            id+=1 # Saltar id del objeto
    except Exception as e:
        # Salvar informacion del error al paginar
        errores.append({'code':500,'valor':'%s'%(e)})
        # Devolver primeros objetos solicitados
        devueltos=objetos[:50]
    # Recopilar informacion del paginado
    info=paginas_totales(modelo,cantidad,filtros)
    info['pagina_actual']=pagina
    info['ordenado_por']=ordenar
    info['cantidad_seleccionada']=cantidad
    info['errores']=[]
    # Recopilar errores
    for e in errores:
        info['errores'].append(e)
    # Guardar informacion
    retorno['info']=info
    # Guardar objetos retornados
    retorno['objetos']=devueltos
    return retorno

# Funcion para calcular paginas
def paginas_totales(modelo,cantidad,filtros):
    try:
        # Verificar si tiene un modelo
        if modelo:
            # Valores base
            paginas=1
            vueltas=0
            # Obtener todos los objetos del modelo
            objetos=modelo.objects.all()
            # Verificar si tiene filtros
            if filtros:
                # Ciclo por cada filtro encontrado
                for f in filtros:
                    # Hacer un filtro especial (por argumentos definidos) en los objetos a analizar
                    objetos=objetos.filter(**{f['campo']:f['valor']})
                # Cuantificar objetos
                total=objetos.count()
                objetos=None
            else:
                # Cuantificar objetos
                total=modelo.objects.all().count()
            # Ciclo por la cantidad total de objetos encontrados
            for i in range(total):
                # Si la vuelta es igual a la cantidad
                if vueltas==cantidad:
                    paginas+=1 # Saltar pagina
                    vueltas=0 # Reiniciar vuelta
                vueltas+=1 # Saltar vuelta
            # Retornar datos
            return {'objetos_totales':total,'paginas_totales':paginas,'error':[]}
        else:
            # En caso de no encontrar modelo, lanzar raise
            raise
    except Exception as e:
        # Retornar error
        return {'error':[{'code':406,'valor':'%s'%(e)}]}

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
    elif modelo == NotaDevolucion:
        tipo='A'
    elif modelo == 'NotaControl':
        tipo='B'
    # elif modelo == NotaCredito:
    #     tipo='C'
    # elif modelo == NotaDebito:
    #     tipo='D'
    empresa=Empresa.objects.get(id=datos['empresa'])
    instancia=Instancia.objects.get(id=datos['instancia'])
    configuracion, creado = ConfiguracionPapeleria.objects.get_or_create(instancia=instancia,empresa=empresa,tipo=tipo,defaults={'valor':1})
    return configuracion
