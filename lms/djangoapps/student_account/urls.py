from django.conf import settings
from django.conf.urls import url

from student_account import views
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

urlpatterns = [
    url(r'^finish_auth$', views.finish_auth, name='finish_auth'),
    url(r'^settings$', views.account_settings, name='account_settings'),
]

if settings.FEATURES.get('ENABLE_COMBINED_LOGIN_REGISTRATION') and configuration_helpers.get_value('ENABLE_RESET_PASSWORD', True):
    urlpatterns += [
        url(r'^password$', views.password_change_request_handler, name='password_change_request'),
    ]
