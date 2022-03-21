from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db.models import Avg, Func
from django.contrib import messages

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import datetime, timedelta
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
    dataset = Registro_temperatura.objects.values('Nodo__nombre').filter(created_at__range=(earlier,now)).annotate(promedio=Round(Avg('temperatura'),2))
    categories = list()
    promedios = list()
    for entry in dataset:
        categories.append(entry['Nodo__nombre'])
        promedios.append(entry['promedio'])
    datax = []
    nodos = Nodo.objects.all()
    for nodo in nodos:
        datay = []
        registros = Registro_temperatura.objects.filter(Nodo__id=nodo.id).values('created_at__date').annotate(
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
    table = Temp_table(Registro_temperatura.objects.all(), order_by="-created_at")
    RequestConfig(request, paginate={"per_page": 15}).configure(table)
    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response("table.{}".format(export_format))
    return render(request, "registro_temperatura.html", {"table": table})

@login_required()
def log_puerta(request):
    table = Door_table(PuertaEstatus.objects.all(), order_by="-created_at")
    RequestConfig(request, paginate={"per_page": 15}).configure(table)
    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response("table.{}".format(export_format))
    return render(request, "log_puerta.html", {"table": table})

@api_view(["GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def guardar_datos(request):
    return Response('Holo')