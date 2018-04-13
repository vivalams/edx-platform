""" API v0 views. """
import logging

from django.contrib.auth import get_user_model
from django.http import Http404
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from edx_rest_framework_extensions.authentication import JwtAuthentication

from courseware.access import has_access
from enrollment import data as enrollment_data
from lms.djangoapps.courseware import courses
from lms.djangoapps.courseware.exceptions import CourseAccessRedirect
from lms.djangoapps.grades.api.serializers import GradingPolicySerializer
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from student.roles import CourseStaffRole
from util.string_utils import str_to_bool
from openedx.core.lib.api.authentication import OAuth2AuthenticationAllowInactiveUser
from openedx.core.lib.api.permissions import OAuth2RestrictedApplicatonPermission

log = logging.getLogger(__name__)
USER_MODEL = get_user_model()


@view_auth_classes()
class GradeViewMixin(DeveloperErrorViewMixin):
    """
    Mixin class for Grades related views.
    """

    authentication_classes = (
        OAuth2AuthenticationAllowInactiveUser,
        SessionAuthentication,
        JwtAuthentication,
    )
    permission_classes = (IsAuthenticated, OAuth2RestrictedApplicatonPermission,)

    # needed for passing OAuth2RestrictedApplicatonPermission checks
    # for RestrictedApplications (only). A RestrictedApplication can
    # only call this method if it is allowed to receive a 'grades:read'
    # scope
    required_scopes = ['grades:read']

    def _get_course(self, course_key_string, user, access_action = 'load'):
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

    def _get_effective_user(self, request, course):
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

        try:
            return USER_MODEL.objects.get(username=username)

        except USER_MODEL.DoesNotExist:
            return self.make_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                developer_message='The user matching the requested username does not exist.',
                error_code='user_does_not_exist'
            )

    def _make_grade_response(self, user, course, course_grade, use_email=False):
        """
        Serialize a single grade to dict to use in Repsonses
        """
        if use_email:
            user = user.email
        else:
            user = user.username

        return {
            'user': user,
            'course_key': str(course.id),
            'passed': course_grade.passed,
            'percent': course_grade.percent,
            'letter_grade': course_grade.letter_grade,
        }

    def _get_auth_type(self, request):
        """
        Returns value based on request auth type
        """
        if request.auth.application.authorization_grant_type == u'authorization-code' or request.auth.application.authorization_grant_type == u'password':
            return True
        else:
            return None

    def perform_authentication(self, request):
        """
        Ensures that the user is authenticated (e.g. not an AnonymousUser), unless DEBUG mode is enabled.
        """
        super(GradeViewMixin, self).perform_authentication(request)
        if request.user.is_anonymous():
            raise AuthenticationFailed


class CourseGradesView(GradeViewMixin, ListAPIView):
    """
    **Use Case**
        * Get course grades if all user who are enrolled in a course.
        The currently logged-in user may request all enrolled user's grades information.
    **Example Request**
        GET /api/grades/v1/courses/{course_id}/   - Get grades for all users in course
    **GET Parameters**
        A GET request may include the following parameters.
        * course_id: (required) A string representation of a Course ID.
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
            "course_key": "course-v1:edX+DemoX+Demo_Course",
            "passed": false,
            "percent": 0.03,
            "letter_grade": null,
        },
        {
            "username": "fred",
            "course_key": "course-v1:edX+DemoX+Demo_Course",
            "passed": true,
            "percent": 0.83,
            "letter_grade": "B",
        },
        {
            "username": "kate",
            "course_key": "course-v1:edX+DemoX+Demo_Course",
            "passed": false,
            "percent": 0.19,
            "letter_grade": null,
        }]
    """

    # needed for passing OAuth2RestrictedApplicatonPermission checks
    # for RestrictedApplications (only). A RestrictedApplication can
    # only call this method if it is allowed to receive a 'grades:read'
    # scope
    required_scopes = ['grades:read']
    restricted_oauth_required = True

    def get(self, request, course_id=None):
        """
        Gets a course progress status.
        Args:
            request (Request): Django request object.
            course_id (string): URI element specifying the course location.
        Return:
            A JSON serialized representation of the requesting user's current grade status.
        """
        use_email = str_to_bool(request.GET.get('use_email'))
        username = request.GET.get('username')

        if not course_id:
            course_id = request.GET.get('course_id')

        if self._get_auth_type(request):
            username = request.user.username
        else:
            if username:
                request.user.username = username

        course = self._get_course(course_id, request.user)
        if isinstance(course, Response):
            # Returns a 404 if course_id is invalid, or request.user is not enrolled in the course
            return course

        if username:
            grade_user = self._get_effective_user(request, course)
            if isinstance(grade_user, Response):
                # Returns a 403 if the request.user can't access grades for the requested user,
                # or a 404 if the requested user does not exist.
                return grade_user

            course_grade = CourseGradeFactory().read(grade_user, course)

            return Response([
                self._make_grade_response(grade_user, course, course_grade, use_email)
            ])
        else:
            enrollments_in_course = enrollment_data.get_user_enrollments(
                course.id, serialize=False
            )

            if not enrollments_in_course:
                return self.make_error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    developer_message='The course has no enrollments',
                    error_code='course_no_enrollments',
                )

            paged_enrollments = self.paginator.paginate_queryset(
                enrollments_in_course, self.request, view=self
            )
            users = (enrollment.user for enrollment in paged_enrollments)
            grades = CourseGradeFactory().iter(users, course)

            response = []
            for user, course_grade, __ in grades:
                course_grade_res = self._make_grade_response(user, course, course_grade, use_email)
                response.append(course_grade_res)

            return Response(response)
