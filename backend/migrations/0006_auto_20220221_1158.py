# Generated by Django 3.2.7 on 2022-02-21 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_auto_20220218_1203'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalpedido',
            name='total',
            field=models.FloatField(default=0, help_text='total de la proforma'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='total',
            field=models.FloatField(default=0, help_text='total de la proforma'),
        ),
    ]
