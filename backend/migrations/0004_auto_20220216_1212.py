# Generated by Django 3.2.7 on 2022-02-16 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0003_auto_20220216_1039'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='mail',
            field=models.TextField(default=1, help_text='correo electronico del contacto', max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cliente',
            name='telefono',
            field=models.TextField(default=1, help_text='telefono del contacto', max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalcliente',
            name='mail',
            field=models.TextField(default=1, help_text='correo electronico del contacto', max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalcliente',
            name='telefono',
            field=models.TextField(default=1, help_text='telefono del contacto', max_length=150),
            preserve_default=False,
        ),
    ]
