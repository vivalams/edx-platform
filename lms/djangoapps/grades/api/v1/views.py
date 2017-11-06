import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import Http404
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from courseware.access import has_access
from lms.djangoapps.ccx.utils import prep_course_for_grading
from lms.djangoapps.courseware import courses
from lms.djangoapps.courseware.exceptions import CourseAccessRedirect
from lms.djangoapps.grades.api.serializers import GradingPolicySerializer
from lms.djangoapps.grades.new.course_grade import CourseGradeFactory
from openedx.core.lib.api.paginators import NamespacedPageNumberPagination
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from enrollment import data as enrollment_data
from student.roles import CourseStaffRole


log = logging.getLogger(__name__)
USER_MODEL = get_user_model()


@view_auth_classes()
class GradeViewMixin(DeveloperErrorViewMixin):
    """
    Mixin class for Grades related views.
    """
    def _get_course(self, course_key_string, user, access_action):
        """
        Returns the course for the given course_key_string after
        verifying the requested access to the course by the given user.
        """
        try:
            course_key = CourseKey.from_string(course_key_string)
        except InvalidKeyError:
            return self.make_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                developer_message='The provided course key cannot be parsed.',
                error_code='invalid_course_key'
            )

        try:
            return courses.get_course_with_access(
                user,
                access_action,
                course_key,
                check_if_enrolled=True,
            )
        except Http404:
            log.info('Course with ID "%s" not found', course_key_string)
        except CourseAccessRedirect:
            log.info('User %s does not have access to course with ID "%s"', user.username, course_key_string)
        return self.make_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            developer_message='The user, the course or both do not exist.',
            error_code='user_or_course_does_not_exist',
        )

    def _get_courses(self, user, access_action):
        # try:
        enrollments = enrollment_data.get_course_enrollments(user.username)
        course_key_strings = [enrollment.get('course_details').get('course_id') for enrollment in enrollments]
        return [self._get_course(course_key_string, user, access_action) for course_key_string in course_key_strings]
        # except:
        #     return []

    def _get_effective_user(self, request, courses):
        """
        Returns the user object corresponding to the request's 'username' parameter,
        or the current request.user if no 'username' was provided.

        Verifies that the request.user has access to the requested users's grades.
        Returns a 403 error response if access is denied, or a 404 error response if the user does not exist.
        """

        # Use the request user's if none provided.
        if 'username' in request.GET:
            username = request.GET.get('username')
        else:
            username = request.user.username

        if request.user.username == username:
            # Any user may request her own grades
            return request.user

        # Only a user with staff access may request grades for a user other than herself.
        for course in courses:
            if not has_access(request.user, CourseStaffRole.ROLE, course):
                log.info(
                    'User %s tried to access the grade for user %s.',
                    request.user.username,
                    username
                )
                return self.make_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    developer_message='The user requested does not match the logged in user.',
                    error_code='user_mismatch'
                )

        if username == 'all':
            try:
                course = courses[0]
                return [enrollment.user for enrollment in enrollment_data.get_user_enrollments(course.id, serialize=False)]
            except:
                return self.make_error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    developer_message='The course does not have any enrollments.',
                    error_code='no_course_enrollments'
                )

        try:
            return USER_MODEL.objects.get(username=username)

        except USER_MODEL.DoesNotExist:
            return self.make_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                developer_message='The user matching the requested username does not exist.',
                error_code='user_does_not_exist'
            )

    def _read_or_create_grade(self, user, course, calculate=False):
        """
        Read or create a new CourseGrade for the specified user and course.
        """
        if calculate is not None:
            course_grade = CourseGradeFactory().create(user, course)
        else:
            course_grade = CourseGradeFactory().get_persisted(user, course)

        return {
            'username': user.username,
            'course_key': str(course.id),
            'passed': course_grade.passed,
            'percent': course_grade.percent,
            'letter_grade': course_grade.letter_grade,
        }

    def _parse_filter_date_string(self, date_string):
        """
        Parse an ISO 8061 date string from url parameter
        """
        if not date_string:
            return
        if len(date_string) == 10:
            # e.g. 2017-01-31
            date_string += "T00:00:00"
        try:
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        except Exception as exc:
            log.info("DATE STRING: ", date_string)
            log.info(exc.message)
            log.exception('Error parsing provided date string', date_string, exc.message)
            return self.make_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                developer_message='Could not parse one of the provided date filters',
                error_code='date_filter_format'
            )

    def perform_authentication(self, request):
        """
        Ensures that the user is authenticated (e.g. not an AnonymousUser), unless DEBUG mode is enabled.
        """
        super(GradeViewMixin, self).perform_authentication(request)
        if request.user.is_anonymous():
            raise AuthenticationFailed


class CourseGradeView(GradeViewMixin, GenericAPIView):
    """
    **Use Case**

        * Get the current course grades for a user in a course.

        The currently logged-in user may request her own grades, or a user with staff access to the course may request
        any enrolled user's grades.

    **Example Request**

        GET /api/grades/v0/course_grade/{course_id}/users/?username={username}

    **GET Parameters**

        A GET request may include the following parameters.

        * course_id: (required) A string representation of a Course ID.
        * username: (optional) A string representation of a user's username.
          Defaults to the currently logged-in user's username.

    **GET Response Values**

        If the request for information about the course grade
        is successful, an HTTP 200 "OK" response is returned.

        The HTTP 200 response has the following values.

        * username: A string representation of a user's username passed in the request.

        * course_id: A string representation of a Course ID.

        * passed: Boolean representing whether the course has been
                  passed according the course's grading policy.

        * percent: A float representing the overall grade for the course

        * letter_grade: A letter grade as defined in grading_policy (e.g. 'A' 'B' 'C' for 6.002x) or None


    **Example GET Response**

        [{
            "username": "bob",
            "course_key": "edX/DemoX/Demo_Course",
            "passed": false,
            "percent": 0.03,
            "letter_grade": None,
        }]

    """
    def get(self, request, course_id):
        """
        Gets a course progress status.

        Args:
            request (Request): Django request object.
            course_id (string): URI element specifying the course location.

        Return:
            A JSON serialized representation of the requesting user's current grade status.
        """

        # course_id = request.GET.get('course_id')
        username = request.GET.get('username')
        should_calculate_grade = request.GET.get('calculate')

        course = self._get_course(course_id, request.user, 'load')

        if isinstance(course, Response):
            # Returns a 404 if course_id is invalid, or request.user is not enrolled in the course
            return course

        grade_user = self._get_effective_user(request, [course])
        prep_course_for_grading(course, request)

        if isinstance(grade_user, Response):
            # Returns a 403 if the request.user can't access grades for the requested user,
            # or a 404 if the requested user does not exist or the course had no enrollments.
            return grade_user

        elif isinstance(grade_user, list):
            # List of grades for all users in course
            response = list()
            for user in grade_user:
                course_grade = self._read_or_create_grade(user, course, should_calculate_grade)
                response.append(course_grade)
        else:
            # One grade for one user in course
            course_grade = self._read_or_create_grade(grade_user, course, should_calculate_grade)
            response = [course_grade]

        return Response(response)


class UserGradeView(GradeViewMixin, ListAPIView):
    """
    **Use Case**

        * Get the current course grades for a user in a course.

        The currently logged-in user may request her own grades, or a user with staff access to the course may request
        any enrolled user's grades.

    **Example Request**

        GET /api/grades/v0/course_grade/{course_id}/users/?username={username}

    **GET Parameters**

        A GET request may include the following parameters.

        * course_id: (required) A string representation of a Course ID.
        * username: (optional) A string representation of a user's username.
          Defaults to the currently logged-in user's username.

    **GET Response Values**

        If the request for information about the course grade
        is successful, an HTTP 200 "OK" response is returned.

        The HTTP 200 response has the following values.

        * username: A string representation of a user's username passed in the request.

        * course_id: A string representation of a Course ID.

        * passed: Boolean representing whether the course has been
                  passed according the course's grading policy.

        * percent: A float representing the overall grade for the course

        * letter_grade: A letter grade as defined in grading_policy (e.g. 'A' 'B' 'C' for 6.002x) or None


    **Example GET Response**

        [{
            "username": "bob",
            "course_key": "edX/DemoX/Demo_Course",
            "passed": false,
            "percent": 0.03,
            "letter_grade": None,
        }]
    """

    pagination_class = NamespacedPageNumberPagination

    def get(self, request):
        """
        Bulk implementation of grades api. If username specified just return users grades in all courses
        :param request:
        :return:
        """

        username = request.GET.get('username')
        should_calculate_grade = request.GET.get('calculate')
        start_date_string = request.GET.get('start_date')
        end_date_string = request.GET.get('end_date')

        if username == 'all':
            log.info('Cannot calculate realtime bulk grades...reading from persisted grades')

            bulk_grades_admin = settings.FEATURES.get('BULK_GRADES_ADMIN_USERNAME', 'edx')

            if not request.user.is_superuser or request.user.username != bulk_grades_admin:
                return self.make_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    developer_message='The requesting user does not have the required credentials',
                    error_code='user_does_not_have_access'
                )

            start_date = self._parse_filter_date_string(start_date_string)
            end_date = self._parse_filter_date_string(end_date_string)

            if isinstance(start_date, Response):
                return start_date
            if isinstance(end_date, Response):
                return end_date

            persisted_grades = CourseGradeFactory().bulk_read(start_date=start_date, end_date=end_date)
            page = self.paginator.paginate_queryset(persisted_grades, self.request, view=self)
            grades_to_serialize = persisted_grades if not page else page

            response = []
            for persisted_grade in grades_to_serialize:
                response.append({
                    'username': USER_MODEL.objects.get(id=persisted_grade.user_id).username,
                    'course_key': str(persisted_grade.course_id),
                    'passed': persisted_grade.passed_timestamp is not None,
                    'percent': persisted_grade.percent_grade,
                    'letter_grade': persisted_grade.letter_grade,
                })
            if page is not None:
                return self.get_paginated_response(response)

        else:
            grade_user = self._get_effective_user(request, [])

            courses = self._get_courses(grade_user, 'load')

            response = list()
            for course in courses:
                course_grade = self._read_or_create_grade(grade_user, course, should_calculate_grade)
                response.append(course_grade)


        return Response(response)
