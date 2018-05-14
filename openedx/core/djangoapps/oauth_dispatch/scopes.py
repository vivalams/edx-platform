"""
Django OAuth Toolkit scopes backend for the dot-dynamic-scopes package.
"""

from django.conf import settings
from django.utils import module_loading

from oauth2_provider.scopes import SettingsScopes

from .models import RestrictedApplication_2


class DynamicScopes(SettingsScopes):
    """
    Scopes backend that provides scopes from a Django model.
    """
    def get_all_scopes(self):
        return settings.OAUTH2_PROVIDER['SCOPES']

    def get_available_scopes(self, application = None, request = None, *args, **kwargs):
        return list(self.get_all_scopes().keys())

    #def get_default_scopes(self, application = None, request = None, *args, **kwargs):
    #    return [scope.name for scope in RestrictedApplication_2.objects.filter(is_default = True)]
