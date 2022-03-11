from .models import Registro_temperatura, PuertaEstatus
import django_tables2 as tables


class Temp_table(tables.Table):
    export_formats = ['csv', 'xls']
    created_at = tables.Column(verbose_name='Fecha Registro')

    class Meta:
        model = Registro_temperatura
        template_name = "django_tables2/bootstrap4.html"

class Door_table(tables.Table):
    export_formats = ['csv', 'xls']
    created_at = tables.Column(verbose_name='Fecha Registro')

    class Meta:
        model = PuertaEstatus
        template_name = "django_tables2/bootstrap4.html"
