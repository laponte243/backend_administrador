from django.apps import AppConfig

class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from . import models
        from . import menu
        try:
            if not models.Instancia.objects.all():
                from . import views
                ret=views.crear_super_usuario('Holo')
                print(ret)
        except Exception as e:
            print(e)