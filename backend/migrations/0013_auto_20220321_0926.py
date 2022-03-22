# Generated by Django 3.2.7 on 2022-03-21 13:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0012_auto_20220318_1120'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproducto',
            name='costo_2',
        ),
        migrations.RemoveField(
            model_name='historicalproducto',
            name='costo_3',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='costo_2',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='costo_3',
        ),
        migrations.AddField(
            model_name='historicalproducto',
            name='precio_1',
            field=models.FloatField(default=0, help_text='Precio del producto 1'),
        ),
        migrations.AddField(
            model_name='historicalproducto',
            name='precio_2',
            field=models.FloatField(default=0, help_text='Precio del producto 2'),
        ),
        migrations.AddField(
            model_name='historicalproducto',
            name='precio_3',
            field=models.FloatField(default=0, help_text='Precio del producto 3', null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_1',
            field=models.FloatField(default=0, help_text='Precio del producto 1'),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_2',
            field=models.FloatField(default=0, help_text='Precio del producto 2'),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_3',
            field=models.FloatField(default=0, help_text='Precio del producto 3', null=True),
        ),
    ]