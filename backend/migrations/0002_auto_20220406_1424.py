# Generated by Django 3.2.7 on 2022-04-06 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detallefactura',
            name='total_producto',
            field=models.FloatField(default=0, help_text='Total final del detalle'),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='total_producto',
            field=models.FloatField(default=0, help_text='Total final del detalle'),
        ),
    ]
