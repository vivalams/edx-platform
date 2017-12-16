from rest_framework import serializers

class CourseUploadAPISerializer(serializers.Serializer):
    #input_file = serializers.FileField()
    course_key = serializers.CharField(max_length=200)
