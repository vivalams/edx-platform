from django.shortcuts import render
from xblockutils.resources import ResourceLoader
from django.http import HttpResponseBadRequest
import requests 
from django.shortcuts import render
from django import forms


request_url = 'http://openedx.microsoft.com/api/courses/v1/courses/'
data = requests.get(request_url)
lit = data.json()['results']
courses_list = []
for each in lit:
    courses_list.append(('https://' + each['media']['image']['small'].split('/')[2] + '/courses/' + each['id']))
image_list = []
for each in lit:
    image_list.append(each['media']['image']['small'])
#user = request.user
user = 'staff'
loader = ResourceLoader(__name__)
def heartbeat(request):
    template = loader.render_django_template('templates/employee.html', {'courseslist':courses_list,'imagelist':image_list,'user':user})
    return HttpResponseBadRequest(template)
