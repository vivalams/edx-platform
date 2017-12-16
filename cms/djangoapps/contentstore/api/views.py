from django.http import HttpResponse
# Rest API
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import zipfile
import StringIO
from django.core import serializers
#from services.serializers import CourseUploadAPISerializer
from cms.djangoapps.contentstore.views.import_export import api_import_handler
from cms.djangoapps.contentstore.api.serializers import CourseUploadAPISerializer
@api_view(['GET', 'POST'])
def CourseUploadAPI(request, format=None):
    if request.method == 'GET':
        serializer = CourseUploadAPISerializer()
        return Response(serializer.data, status=200)
    elif request.method == 'POST':
        serializer = CourseUploadAPISerializer(data=request.data)
        if serializer.is_valid():
            #print (request.data['course_key'])
            api_import_handler(request.data['course_key']) 
            msg = {}
            return Response(msg, status=200)
        else:
            return Response(serializer.errors, status=200)

    elif request.method == 'PUT':
        serializer = CourseUploadAPISerializer(data=request.data)
        if serializer.is_valid():
            #print (request.data)
            # todo
            msg = {}
            return Response(msg, status=200)
        else:
            return Response(serializer.errors, status=200)
