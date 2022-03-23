# Generated by Django 3.2.7 on 2022-03-23 13:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Correo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.TextField(max_length=254)),
                ('nombre', models.CharField(help_text='Nombre del receptor', max_length=120, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Error',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razon', models.TextField(max_length=254)),
                ('origen', models.TextField(max_length=254)),
                ('msg_mqtt', models.TextField(max_length=254)),
                ('nodo', models.CharField(blank=True, default='N/A', max_length=254, null=True)),
                ('sensor', models.CharField(blank=True, default='N/A', max_length=254, null=True)),
                ('estado', models.CharField(blank=True, default='N/A', max_length=254, null=True)),
                ('temperatura', models.CharField(blank=True, default='N/A', max_length=254, null=True)),
                ('contador', models.IntegerField(default=1)),
                ('fecha_hora', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Nodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(help_text='Nombre del nodo', max_length=120, null=True)),
                ('direccion_MAC', models.CharField(blank=True, help_text='MAC del nodo', max_length=20)),
                ('temperatura_min', models.FloatField(blank=True, null=True)),
                ('temperatura_max', models.FloatField(blank=True, null=True)),
                ('reenvio_correo', models.IntegerField(blank=True, default=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Sensor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial', models.CharField(help_text='Serial del sensor', max_length=120)),
                ('nombre', models.CharField(help_text='Nombre del sensor', max_length=120, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nodo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='tempro.nodo')),
            ],
        ),
        migrations.CreateModel(
            name='RegistroTemperatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('temperatura', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('nodo', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='tempro.nodo')),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='tempro.sensor')),
            ],
        ),
        migrations.CreateModel(
            name='Puerta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('A', 'Abierta'), ('C', 'Cerrada')], max_length=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('nodo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='tempro.nodo')),
            ],
        ),
        migrations.CreateModel(
            name='CorreoAlerta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_alerta', models.CharField(choices=[('A', 'Alta'), ('B', 'Baja')], max_length=1, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('nodo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='tempro.nodo')),
            ],
        ),
    ]
