from django.conf.urls import url
from cms.djangoapps.contentstore.api import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^api/course_upload$', views.CourseUploadAPI, name='CourseUploadAPI'),
]
urlpatterns = format_suffix_patterns(urlpatterns)

