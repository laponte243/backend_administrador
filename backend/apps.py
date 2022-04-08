from django.apps import AppConfig

class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from . import models
        if not models.Instancia.objects.all():
            from . import views
            views.crear_super_usuario()