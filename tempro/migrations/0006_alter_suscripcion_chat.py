# Generated by Django 3.2.7 on 2022-03-28 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tempro', '0005_auto_20220328_0938'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suscripcion',
            name='chat',
            field=models.IntegerField(unique=True),
        ),
    ]