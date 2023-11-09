from django.apps import AppConfig

# class NewsbaitappConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'newsbaitapp'

from django.apps import AppConfig
from django.db.models.signals import post_migrate

class NewsBaitAppConfig(AppConfig):
    #default_auto_field = 'django.db.models.BigAutoField'
    name = 'newsbaitapp'

    def ready(self):
        from .signals import create_default_configuration, update_api_key
        post_migrate.connect(create_default_configuration, sender=self)