from django.core.management.base import BaseCommand, CommandError
import requests
import shutil


class Command(BaseCommand):
    help = 'Verify Course Data'

    def add_arguments(self, parser):
        parser.add_argument('course_key', type=str, nargs='?')

    def handle(self, *args, **options):
        self.course_key = options.get('course_key')
        self.input_file =  self.verify_git_document()
        self.result = self.post_api_document()
        print (self.input_file)
        print (self.result)
    
    def verify_git_document(self):
        url  = "https://github.com/manikarthikk/openedx_upgrade/blob/master/course.test.tar.gz"
        local_filename = url.split('/')[-1]
        response = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024): 
                if chunk:
                    f.write(chunk)
        return local_filename

    def post_api_document(self):
        url  = "http://127.0.0.1:8000/api/course_upload"
        files = {'file': (self.input_file, 'input_file')}
        response = requests.post(url, data={"course_key" : "xyz"}, files=files)
        return response.text
