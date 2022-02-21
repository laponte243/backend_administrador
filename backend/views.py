# Rest framework imports
from email import header
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Django imports
from django.apps import apps
from django.db.models import Count, Q, Sum
from django.contrib.auth import login
from django.core import serializers as sr
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse, request
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
# Raiz imports
from .serializers import *
from .models import *
from .menu import *
# Recover password
from knox.views import LoginView as KnoxLoginView
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.template.loader import render_to_string
# Import pandas
import pandas as pd
import csv

# Utiles
"""Rceiver for reset password"""
@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):

    RESET_PASSWORD_ROUTE = getattr(settings, "RESET_PASSWORD_ROUTE", None)
    # email_plaintext_message = "{}?token={}".format(reverse('password_reset:reset-password-request'), reset_password_token.key)
    # import html message.html file
    context = ({"url": RESET_PASSWORD_ROUTE + '#/passwordset?token=' + reset_password_token.key})
    resetPasswordTemplate = 'user_reset_password.html'
    reset_password_message = render_to_string(resetPasswordTemplate, context)
    # send email
    subject, from_email, to = "Password Reset for {title}".format(title="DataVisualizer"), 'noreply@somehost.local', reset_password_token.user.email
    text_content = ''
    html_content = reset_password_message
    msg = EmailMessage(subject, html_content, from_email, [to])
    msg.content_subtype = "html" # Main content is now text/html
    msg.send()

"""Overwrite knox's login view"""

class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        #return super(LoginView, self).post(request, format=None)
        temp_list=super(LoginView, self).post(request, format=None)
        temp_list.data["user_id"]=user.id
        temp_list.data["first_name"]=user.first_name
        temp_list.data["last_name"]=user.last_name
        temp_list.data["last_login"]=user.last_login
        return Response({"data":temp_list.data})

class GroupVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupMSerializer

class PermissionVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    queryset = Permission.objects.all().order_by('name')
    serializer_class = PermissionMSerializer

class UserVS(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = UsuarioMSerializer

    def create(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        if (self.request.user.perfil.tipo == 'S'):
            return User.objects.all()
        elif (self.request.user.perfil.tipo == 'A'):
            instancia = Perfil.objects.get(usuario=self.request.user).instancia
            return User.objects.filter(perfil__instancia=instancia).exclude(perfil__tipo='A')
        else:
            return None

    """ Update by original django method """

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        objeto = self.get_object()
        if (perfil.tipo == 'S'):
            Perfil.objects.get(usuario=self.request.data.id).delete()
            objeto.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif (perfil.tipo == 'A'):
            if (objeto.perfil.tipo != 'S' and objeto.perfil.tipo != 'A' and str(objeto.perfil.instancia.id) == str(perfil.instancia.id)):
                Perfil.objects.get(usuario=self.request.data.id).delete()
                objeto.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

class ModuloVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = ModuloSerializer
    
    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Modulo.objects.all().order_by('nombre')
        if (perfil.tipo=='A'):
            modulos = []
            for m in perfil.instancia.modulo:
                modulos.append(m)
            return modulos
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

class MenuVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = MenuSerializer

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        if (Menu.objects.all().count() == 0):
            for m in modelosMENU['modelos']:
                menu = Menu(router=m['router'],orden=m['orden'])
                menu.save()
                if (m['parent'] != None):
                    menu.parent = Menu.objects.get(id=m['parent'])
                    menu.save()
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Menu.objects.all()
        else:
            return None

    def update(self, request, *args, **kwargs):
       perfil = Perfil.objects.get(usuario=self.request.user)
       if (perfil.tipo == 'S'):
           partial = True # Here I change partial to True
           instance = self.get_object()
           serializer = self.get_serializer(instance, data=request.data, partial=partial)
           serializer.is_valid(raise_exception=True)
           self.perform_update(serializer)
           return Response(serializer.data, status=status.HTTP_200_OK)
       else:
           return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

# Instancia
class InstanciaVS(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser, IsAuthenticated]
    serializer_class = InstanciaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S' and self.request.user.is_superuser == True):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif(perfil.tipo == 'S'):
            return JsonResponse({"error": "Your profile or user has deactivated being superuser"}, status=status.HTTP_403_FORBIDDEN)
        else:
            return JsonResponse({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Instancia.objects.all().order_by('nombre')
        else:
            return None

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error':'Forbidden, user no have permissions'}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        return Response(False, status=status.HTTP_403_FORBIDDEN)

class MenuInstanciaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = MenuInstanciaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return MenuInstancia.objects.all().order_by('id')
        elif (perfil.tipo == 'A'):
            return MenuInstancia.objects.filter(instancia=perfil.instancia).order_by('id')
        else:
            return JsonResponse({"error": "Forbidden, can't you see",}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN) # Change

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT) # Change
            else:
                return Response(status=status.HTTP_403_FORBIDDEN) # Change
            
class PerfilVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = PerfilSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Perfil.objects.all().order_by('usuario')
        elif (perfil.tipo == 'A'):
            return Perfil.objects.filter(instancia=perfil.instancia).order_by('usuario')
        else:
            return Perfil.objects.filter(id=perfil.id).order_by('usuario')

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=datos, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK) # Change
        else:
            try:
                objeto = Perfil.objects.get(usuario=self.request.user)
                objeto.avatar = request.data['avatar']
                self.perform_update(objeto)
                return Response(objeto, status=status.HTTP_200_OK)
            except:
                return Response({'error':'Problem with user or selected avatar'}, status=status.HTTP_401_UNAUTHORIZED)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT) # Change
            else:
                return Response(status=status.HTTP_403_FORBIDDEN) # Change

class PermisoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = PermisoSerializer

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Permiso.objects.all().order_by('id')
        elif (perfil.tipo == 'A'):
            return Permiso.objects.filter(instancia=perfil.instancia).order_by('perfil')
        else:
            return Permiso.objects.filter(perfil=perfil.id)

    def update(self):
        return JsonResponse({"error": "No authorized"}, status=status.HTTP_403_FORBIDDEN) #Change status

# Empresa
class EmpresaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = EmpresaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Empresa.objects.all().order_by('nombre')
        else:
            return Empresa.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ContactoEmpresaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ContactoEmpresaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return ContactoEmpresa.objects.all().order_by('nombre')
        else:
            return ContactoEmpresa.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ConfiguracionPapeleriaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ConfiguracionPapeleriaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
                
    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return ConfiguracionPapeleria.objects.all().order_by('valor', 'empresa')
        else:
            return ConfiguracionPapeleria.objects.filter(instancia=perfil.instancia).order_by('valor', 'empresa')

# Inventario
class TasaConversionVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = TasaConversionSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return TasaConversion.objects.all().order_by('nombre')
        else:
            return TasaConversion.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ImpuestosVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ImpuestosSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Impuestos.objects.all().order_by('nombre')
        else:
            return Impuestos.objects.filter(instancia=perfil.instancia).order_by('nombre')

class MarcaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = MarcaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Marca.objects.all().order_by('nombre')
        else:
            return Marca.objects.filter(instancia=perfil.instancia).order_by('nombre')

class UnidadVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = Unidad.objects.all().order_by('nombre')
    serializer_class = UnidadSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Unidad.objects.all().order_by('nombre')
        else:
            return Unidad.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ProductoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ProductoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['servicio','menejo_inventario', 'activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        if (perfil.tipo == 'S'):
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            for lp in ListaPrecio.objects.filter(instancia_id=perfil.instancia.id):
                pro = Producto.objects.get(id=serializer.data['id'])
                detalle = DetalleListaPrecio(instancia=perfil.instancia, listaprecio=lp, producto=pro, precio=serializer.data['costo'])
                detalle.save()
            headers = self.get_success_headers(serializer.data)
            return Response('serializer.data', status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            for lp in ListaPrecio.objects.filter(instancia_id=perfil.instancia.id):
                pro = Producto.objects.get(id=serializer.data['id'])
                detalle = DetalleListaPrecio(instancia=perfil.instancia, listaprecio=lp, producto=pro, precio=serializer.data['costo'])
                detalle.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Producto.objects.all().order_by('nombre')
        else:
            return Producto.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ProductoImagenVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = ProductoImagen.objects.all().order_by('producto', 'principal')
    serializer_class = ProductoImagenSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return ProductoImagen.objects.all().order_by('producto', 'principal')
        else:
            return ProductoImagen.objects.filter(instancia=perfil.instancia).order_by('producto', 'principal')

class AlmacenVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = AlmacenSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Almacen.objects.all().order_by('nombre')
        else:
            return Almacen.objects.filter(instancia=perfil.instancia).order_by('nombre')

class MovimientoInventarioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = MovimientoInventarioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'almacen']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            objeto = MovimientoInventario.objects.filter(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'])
            if objeto.count() > 0:
                disp = float(datos['cantidad_recepcion'])
                for o in objeto:
                    disp += o.cantidad_recepcion
                inv = Inventario.objects.filter(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'], lote=datos['lote'])
                if inv.first() != None:
                    inven = inv.first()
                    inven.disponible = disp
                    inven.bloqueado = 0
                    inven.save()
                else:
                    Inventario.objects.create(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'],disponible=disp,bloqueado=0)
            else:
                Inventario.objects.create(instancia_id=datos['instancia'],producto_id=datos['producto'],almacen_id=datos['almacen'],disponible=datos['cantidad_recepcion'],bloqueado=0)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return MovimientoInventario.objects.all().order_by('id')
        else:
            return MovimientoInventario.objects.filter(instancia=perfil.instancia).order_by('lote')

class DetalleInventarioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = InventarioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'almacen']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Inventario.objects.all().order_by('almacen', 'producto')
        else:
            return Inventario.objects.filter(instancia=perfil.instancia).order_by('almacen', 'producto')

@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def Inven(request):
    perfil = Perfil.objects.get(usuario=request.user)
    if perfil:
        objeto_inventario = Inventario.objects.filter(instancia=perfil.instancia).values('almacen', 'producto').annotate(sum_disponible=Sum('disponible'),sum_bloqueado=Sum('bloqueado'))
        return Response(objeto_inventario,status=status.HTTP_200_OK)

# ventas
class VendedorVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = VendedorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Vendedor.objects.all().order_by('nombre')
        else:
            return Vendedor.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ClienteVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ClienteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Cliente.objects.all().order_by('nombre')
        else:
            return Cliente.objects.filter(instancia=perfil.instancia).order_by('nombre')

class ContactoClienteVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = ContactoClienteSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return ContactoCliente.objects.all().order_by('nombre')
        else:
            return ContactoCliente.objects.filter(instancia=perfil.instancia).order_by('nombre')


class PedidoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = PedidoSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Pedido.objects.all()
        else:
            return Pedido.objects.filter(instancia=perfil.instancia)

class DetallePedidoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetallePedidoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pedido']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return DetallePedido.objects.all()
        else:
            return DetallePedido.objects.filter(instancia=perfil.instancia)

class ProformaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = ProformaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Proforma.objects.all()
        else:
            return Proforma.objects.filter(instancia=perfil.instancia)

class DetalleProformaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = DetalleProformaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return DetalleProforma.objects.all()
        else:
            return DetalleProforma.objects.filter(instancia=perfil.instancia)

class FacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = FacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Factura.objects.all().order_by('empresa', 'cliente', 'vendedor')
        else:
            return Factura.objects.filter(instancia=perfil.instancia).order_by('empresa', 'cliente', 'vendedor')

class DetalleFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = DetalleFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return DetalleFactura.objects.all()
        else:
            return DetalleFactura.objects.filter(instancia=perfil.instancia)


class ListaPrecioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = ListaPrecioSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        if (perfil.tipo == 'S'):
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            if (datos['predeterminada'] == 'true'):
                if ListaPrecio.objects.filter(predeterminada=True).exists():
                    return Response({'error': 'Ya existe una lista predeterminada'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            productos = Producto.objects.filter(instancia_id=perfil.instancia.id)
            for o in productos:
                costo_final = o.costo + (o.costo * (serializer.data['porcentaje'] /100))
                listad = DetalleListaPrecio.objects.create(instancia_id=datos['instancia'], producto=o,precio=costo_final, listaprecio_id=serializer.data['id'])
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            if datos['predeterminada'] == 'true':
                if ListaPrecio.objects.filter(predeterminada=True).exists():
                    return Response({'error': 'Ya existe una lista predeterminada'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        if (perfil.tipo == 'S'):
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            if datos['predeterminada'] == 'true':
                if ListaPrecio.objects.filter(predeterminada=True).exists():
                    return Response({'error': 'Ya existe una lista predeterminada'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            datos._mutable = _mutable
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            DetalleListaPrecio.objects.filter(instancia_id=perfil.instancia.id, listaprecio=serializer.data['id']).delete()
            productos = Producto.objects.filter(instancia_id=perfil.instancia.id)
            for o in productos:
                costo_final = o.costo + (o.costo * (serializer.data['porcentaje'] /100))
                listad = DetalleListaPrecio.objects.create(instancia_id=datos['instancia'], producto=o,precio=costo_final, listaprecio_id=serializer.data['id'])
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                _mutable = datos._mutable
                datos._mutable = True
                datos['instancia'] = str(perfil.instancia.id)
                if datos['predeterminada'] == 'true':
                    if ListaPrecio.objects.filter(predeterminada=True).exists():
                        return Response({'error': 'Ya existe una lista predeterminada'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                datos._mutable = _mutable
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        listas = ListaPrecio.objects.filter(instancia=perfil.instancia, predeterminada=True)
        if listas.exists() and listas.count() > 1:
            for l in listas:
                l.predeterminada = False
                l.save()
            lista = ListaPrecio.objects.filter(instancia=perfil.instancia, activo=True).first()
            lista.predeterminada = True
            lista.save()
        if (perfil.tipo=='S'):
            return ListaPrecio.objects.all().order_by('id')
        else:
            return ListaPrecio.objects.filter(instancia=perfil.instancia).order_by('id')

class DetalleListaPrecioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetalleListaPrecioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['listaprecio' ,'producto__activo']
    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        if (perfil.tipo == 'S'):
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            datos._mutable = _mutable
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            _mutable = datos._mutable
            datos._mutable = True
            datos['instancia'] = str(perfil.instancia.id)
            datos._mutable = _mutable
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                _mutable = datos._mutable
                datos._mutable = True
                datos['instancia'] = str(perfil.instancia.id)
                datos._mutable = _mutable
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return DetalleListaPrecio.objects.all().order_by('producto', '-precio')
        else:
            return DetalleListaPrecio.objects.filter(instancia=perfil.instancia).order_by('producto', '-precio')

class ImpuestosFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ImpuestosFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return ImpuestosFactura.objects.all().order_by('nombre')
        else:
            return ImpuestosFactura.objects.filter(instancia=perfil.instancia).order_by('nombre')

class NumerologiaFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = NumerologiaFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return NumerologiaFactura.objects.all().order_by('tipo', 'valor')
        else:
            return NumerologiaFactura.objects.filter(instancia=perfil.instancia).order_by('tipo', 'valor')

class NotaFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = NotaFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return NotaFactura.objects.all().order_by('venta')
        else:
            return NotaFactura.objects.filter(instancia=perfil.instancia).order_by('venta')

# Compras
class ProveedorVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = ProveedorSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Proveedor.objects.all().order_by('nombre')
        else:
            return Proveedor.objects.filter(instancia=perfil.instancia).order_by('nombre')

class CompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = CompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return Compra.objects.all().order_by('empresa', 'Proveedor', 'total')
        else:
            return Compra.objects.filter(instancia=perfil.instancia).order_by('empresa', 'Proveedor', 'total')

class DetalleCompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = DetalleCompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return DetalleCompra.objects.all().order_by('compra', 'producto', 'cantidad', 'precio')
        else:
            return DetalleCompra.objects.filter(instancia=perfil.instancia).order_by('compra', 'producto', 'cantidad', 'precio')

class NotaCompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # # authentication_classes = [TokenAuthentication]
    serializer_class = NotaCompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'): 
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo=='S'):
            return NotaCompra.objects.all().order_by('compra')
        else:
            return NotaCompra.objects.filter(instancia=perfil.instancia).order_by('compra')

# Funciones
def CrearAdmin(data):
    try:
        instan = data['instancia']
        nombreInstancia = instan['nombre'] + " ("+data['username']+")"
        user = User(username=data['username'],email=data['email'],password=data['password'])
        user.save()
        instancia = Instancia(nombre=nombreInstancia,activo=instan['activo'],multiempresa=instan['multiempresa'],vencimiento=instan['vencimiento'])
        instancia.save()
        perfil = Perfil(usuario=user,instancia=instancia,tipo='A')
        perfil.save()
        for p in data['permisos']:
            menuInstancia = MenuInstancia(instancia=instancia,menu=p['menu'])
            menuInstancia.save()
            permiso = Permiso(instancia=instancia,perfil=perfil,menuinstancia=menuInstancia,leer=p['leer'],escribir=p['escribir'],borrar=p['borrar'],actualizar=p['actualizar'])
            permiso.save()
        return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse({'error': _(e.args[0])}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@csrf_exempt
#@authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def CreateSuperUser(request):
    if (Instancia.objects.all().count() == 0):
        instancia = Instancia(nombre="Primera",activo=True,multiempresa=True,vencimiento=None)
        instancia.save()
        perfilS = Perfil(instancia=instancia,usuario_id=1,activo=True,avatar=None,tipo="S")
        perfilS.save()
        # admin = User.objects.create_user(username='admin',email='',password='admin')
        # admin.save()
        # perfilA = Perfil(instancia=instancia,usuario=admin,activo=True,avatar=None,tipo="A")
        # perfilA.save()
        # for m in Menu.objects.all():
        #     menuinstancia = MenuInstancia(intancia=instancia,menu=m,orden=m['orden'])
        #     menuinstancia.save()
        #     if (m['parent'] != None):
        #         menuinstancia.parent = MenuInstancia.objects.filter(menu=Menu.objects.get(id=m['parent'])).first()
        #         menuinstancia.save()
        # for p in MenuInstancia.objects.filter(instancia=instancia):
        #     permiso = None
        #     permiso = Permiso(instancia=instancia,menuinstancia_id=p.id,perfil_id=2,crear=p['crear'],leer=p['leer'],editar=p['editar'],eliminar=p['eliminar'])
        #     permiso.save()
        return Response("Super creado")
    else:
        return Response("Ya existe un superusuario")
    return Response('Menu.objects.all()')


@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def CrearNuevoUsuario(request):
    data = json.load(request.body)
    try:
        usuario = User.objects.filter(email=data['email'])
        if (usuario):
            return JsonResponse({"error": "Email"}, status=status.HTTP_400_BAD_REQUEST)
        elif (data['tipo'] == 'A' & request.user.perfil.tipo == 'S'):
            return CrearAdmin(data)
        else:
            instan = data['instancia']
            user = User(username=data['username'],email=data['email'],password=data['password'])
            user.save()
            if (request.user.perfil.tipo == 'S'):
                # Instancia igual a la instancia dada por el superusuario (instancia=data['instancia'])
                perfil = Perfil(usuario=user,instancia=data['instancia'],tipo=data['tipo'])
                perfil.save()
                for p in data['permisos']:
                    for mi in MenuInstancia.objects.filter(instancia=data['instancia']):
                        if (mi.id == p['menu']):
                            permiso = None
                            permiso = Permiso(instancia=instan['id'],perfil=perfil,menuinstancia=p['menu'],
                                            leer=p['leer'],escribir=p['escribir'],borrar=p['borrar'],actualizar=p['actualizar'])
                            permiso.save()
                return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
            elif (request.user.perfil.tipo == 'A'):
                if (data['tipo'] == "U" or data['tipo'] == "V"):
                    # Instancia igual a la instancia del perfil del usuario que hace la peticion (instancia = request.user.perfil.instancia)     
                    perfil = Perfil(usuario=user,instancia=request.user.perfil.instancia,tipo=data['tipo'])
                    perfil.save()
                    for p in data['permisos']:
                        for mi in MenuInstancia.objects.filter(instancia=data['instancia']):
                            if (mi.id == p['menu']):
                                permiso = None
                                permiso = Permiso(instancia=request.user.perfil.instancia,perfil=perfil,menuinstancia=p['menu'],
                                                leer=p['leer'],escribir=p['escribir'],borrar=p['borrar'],actualizar=p['actualizar'])
                                permiso.save()
                    return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
                else:
                    return JsonResponse({"error": "Forbidden, user type not allowed",}, status=status.HTTP_403_FORBIDDEN)
            else:
                return JsonResponse({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({'error': _(e.args[0])}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ObtenerMenu(request):
    menus = { 'router': 'root', 'children': []}
    def VerificarHijos (objetoPadre):
        if (MenuInstancia.objects.filter(parent=objetoPadre.id).count() > 0 or Menu.objects.filter(parent=objetoPadre.id).count() > 0):
            return True
        else:
            return False
    if (request.user.perfil.tipo == "S"):
        primeros = Menu.objects.filter(parent=None).order_by('orden')
        for p in primeros:
            if VerificarHijos(p):
                primero = { 'router': '', 'children': []}
                primero['router'] = p.router.replace('-','')
                for s in Menu.objects.filter(parent=p.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo = { 'router': '', 'children': []}
                        segundo['router'] = s.router
                        for t in Menu.objects.filter(parent=s.id).order_by('orden'):
                            tercero = t.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo = s.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero = p.router
                menus['children'].append(primero)
        return Response([menus])
    elif (request.user.perfil.tipo == "A" or request.user.perfil.tipo == "U" or request.user.perfil.tipo == "V"):
        for pe in Permiso.objects.filter(perfil=request.user.perfil):
            primer = MenuInstancia.objects.get(id=pe.menuinstancia.id)
            if (primer.parent == None):
                if VerificarHijos(primer):
                    primero = { 'router': '', 'children': []}
                    nombrePrimero = primer.menu.router
                    primero['router'] = nombrePrimero.replace('-','')
                    for s in MenuInstancia.objects.filter(parent=primer.id).order_by('orden'):
                        if VerificarHijos(s):
                            segundo = { 'router': '', 'children': []}
                            nombreSegundo = s.menu.router
                            segundo['router'] = nombreSegundo
                            for t in MenuInstancia.objects.filter(parent=s.id).order_by('orden'):
                                tercero = t.menu.router
                                segundo['children'].append(tercero)
                            primero['children'].append(segundo)
                        else:
                            segundo = s.menu.router
                            primero['children'].append(segundo)
                    menus['children'].append(primero)
                else:
                    primero = primer.menu.router
                    menus['children'].append(primero)
        return Response([menus])
    else:
        return JsonResponse({'error': 'Forbidden, unknown user'}, status=status.HTTP_403_FORBIDDEN)


@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ObtenerColumnas(request):
    data = json.loads(request.body)
    columnas = []
    try:
        for f in eval(data['value'])._meta.get_fields():
            JsonCol = {
                'select': False,
                'title': f.name.capitalize(),
                'dataIndex': f.name,
                'align': 'left'
            }
            columnas.append(JsonCol)
        return Response(columnas)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def crearlista(request):
    data = json.loads(request.body)
    try:
        lista = ListaPrecio(nombre= data['nombre'], activo=data['activo'])
        lista.save()
        return Response('exitoso')
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualiza_pedido(request):
    payload = json.loads(request.body)
    try:
        pedido_id = Pedido.objects.get(id=payload['idpedido'])
        DetallePedido.objects.filter(pedido=pedido_id).delete()
        for i in payload['data']:
            perfil = Perfil.objects.get(usuario=request.user)
            producto = Producto.objects.get(id=i["producto"])
            instancia = Instancia.objects.get(perfil=perfil.id)
            cantidad = int(i["cantidad"])
            pedido = pedido_id
            nuevo_componente = DetallePedido(instancia_id=instancia.id,pedido=pedido,cantidad=cantidad,producto=producto)
            nuevo_componente.save()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
def ObtenerHistorico(request):
    from django.db.models import CharField, Value
    df = pd.DataFrame()
    try:
        #uid = User.objects.get(username=payload['username'])
        uid = request.user
        #modelo = payload['model']
#        modelo = apps.get_model(app_label='backend', model_name=payload['model'])
        #uid = 1
        betados = ["<class 'backend.models.Modulo'>"]
        if uid is not None:
            for model in apps.get_app_config('backend').get_models():
                if('Historical' not in str(model) and str(model) not in betados):
                    df = pd.DataFrame.append(df,list(model.history.all().values('history_date', 'history_type','history_user_id').annotate(modelo=Value(str(model).replace('backend.models.',''), output_field=CharField())).order_by('-id')))
                    df.reset_index(drop=True, inplace=True)
                    dfx = df.sort_values(by='history_date', ascending=False).head(5)
                    data = []
                    for index, row in dfx.iterrows():
                        tipo = ""
                        if(row["history_type"]=="+"):
                            tipo = 'Creado'
                        elif(row["history_type"]=="-"):
                            tipo = 'Eliminado'
                        else:
                            tipo = 'Editado'
                        data.append({'date':row['history_date'],'type':tipo, 'model':str(row['modelo']).replace("<class '",'').replace("'>",'')})
        return JsonResponse({'mensaje': data}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lista.csv"'
    marcas = Marca.objects.all()
    writer = csv.writer(response)  
    for m in marcas:
        writer.writerow(['Marca:' , m.nombre])
        titulos = ['Codigo', 'Producto', 'Costo']
        listas = ListaPrecio.objects.filter(activo=True).order_by('id')
        for lista in listas:
            titulos.append(lista.nombre) 
        writer.writerow(titulos)
        productos = Producto.objects.filter(activo=True,venta=True, marca=m)
        for p in productos:
            texto = [p.sku, p.nombre, p.costo]
            precios = DetalleListaPrecio.objects.filter(producto= p).order_by('listaprecio__id')
            for precio in precios:
                texto.append(precio.precio)
            writer.writerow(texto)
    return response
