# Generated by Django 3.2.7 on 2022-03-25 21:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tempro', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Suscripcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat', models.IntegerField()),
                ('usuario', models.IntegerField(blank=True, null=True)),
                ('alertar', models.BooleanField(default=True)),
            ],
        ),
    ]