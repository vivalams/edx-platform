""" API v1 views. """
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
from lms.djangoapps.courseware import courses
from lms.djangoapps.courseware.exceptions import CourseAccessRedirect
from lms.djangoapps.grades.api.serializers import GradingPolicySerializer
from lms.djangoapps.grades.course_grade import CourseGrade
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.lib.api.paginators import NamespacedPageNumberPagination
from openedx.core.lib.api.permissions import IsStaffOrOwner, OAuth2RestrictedApplicatonPermission
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

    pagination_class = NamespacedPageNumberPagination

    def _get_course(self, request, course_key_string, user, access_action):
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

        org_filter = self._get_org_filter(request)
        if org_filter:
            if course_key.org not in org_filter:
                return self.make_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    developer_message='The OAuth2 RestrictedApplication is not associated with org.',
                    error_code='course_org_not_associated_with_calling_application'
                )

        try:
            course_org_filter = configuration_helpers.get_value('course_org_filter')
            if course_org_filter and course_key.org not in course_org_filter:
                raise Http404
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

    def _get_all_users(self, request, course):
        """
        Validates course enrollments and returns the users course enrollment data
        Returns a 404 error response if the user course enrollments does not exist.
        """
        try:
            org_filter = self._get_org_filter(request)
            return enrollment_data.get_user_enrollments(
                course.id, org_filter=org_filter, serialize=False
            )
        except:
            return self.make_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                developer_message='The course does not have any enrollments.',
                error_code='no_course_enrollments'
            )

    def _make_grade_response(self, user, course, course_grade, use_email=None):
        """
        Serialize a single grade to dict to use in Repsonses
        """
        if use_email is not None:
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

    def _get_org_filter(self, request):
        """
        See if the request has an explicit ORG filter on the request
        which limits which OAuth2 clients can see what courses
        based on the association with a RestrictedApplication

        For more information on RestrictedApplications and the
        permissions model, see openedx/core/lib/api/permissions.py
        """
        if hasattr(request, 'auth') and hasattr(request.auth, 'org_associations'):
            return request.auth.org_associations

    def perform_authentication(self, request):
        """
        Ensures that the user is authenticated (e.g. not an AnonymousUser), unless DEBUG mode is enabled.
        """
        super(GradeViewMixin, self).perform_authentication(request)
        if request.user.is_anonymous():
            raise AuthenticationFailed


class UserGradeView(GradeViewMixin, GenericAPIView):
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

    # needed for passing OAuth2RestrictedApplicatonPermission checks
    # for RestrictedApplications (only). A RestrictedApplication can
    # only call this method if it is allowed to receive a 'grades:read'
    # scope
    required_scopes = ['grades:read']

    def get(self, request, course_id):
        """
        Gets a course progress status.

        Args:
            request (Request): Django request object.
            course_id (string): URI element specifying the course location.

        Return:
            A JSON serialized representation of the requesting user's current grade status.
        """

        # See if the request has an explicit ORG filter on the request
        # which limits which OAuth2 clients can see what courses
        # based on the association with a RestrictedApplication
        #
        # For more information on RestrictedApplications and the
        # permissions model, see openedx/core/lib/api/permissions.py
        if hasattr(request, 'auth') and hasattr(request.auth, 'org_associations'):
            course_key = CourseKey.from_string(course_id)
            if course_key.org not in request.auth.org_associations:
                return self.make_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    developer_message='The OAuth2 RestrictedApplication is not associated with org.',
                    error_code='course_org_not_associated_with_calling_application'
                )

        course = self._get_course(request, course_id, request.user, 'load')
        if isinstance(course, Response):
            # Returns a 404 if course_id is invalid, or request.user is not enrolled in the course
            return course

        grade_user = self._get_effective_user(request, course)
        if isinstance(grade_user, Response):
            # Returns a 403 if the request.user can't access grades for the requested user,
            # or a 404 if the requested user does not exist.
            return grade_user

        use_email = request.GET.get('use_email', None)

        course_grade = CourseGradeFactory().read(grade_user, course)
        response = self._make_grade_response(grade_user, course, course_grade, use_email)

        return Response([response])


class CourseGradeAllUsersView(GradeViewMixin, GenericAPIView):
    """
    **Use Case**

        * Get course grades if all user who are enrolled in a course.

        The currently logged-in user may request all enrolled user's grades information.

    **Example Request**

        GET /api/grades/v1/course_grade/{course_id}/all_users   - Get grades for all users in course

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
    # only call this method if it is allowed to receive a 'grades:statistics'
    # scope
    required_scopes = ['grades:statistics']
    restricted_oauth_required = True

    def get(self, request, course_id):
        """
            Gets a course progress status.

            Args:
                request (Request): Django request object.
                course_id (string): URI element specifying the course location.

            Return:
                A JSON serialized representation of the requesting user's current grade status.
        """
        use_email = request.GET.get('use_email', None)

        course = self._get_course(request, course_id, request.user, 'load')

        if isinstance(course, Response):
            # Returns a 404 if course_id is invalid, or request.user is not enrolled in the course
            return course

        enrollments_in_course = self._get_all_users(request, course)
        if isinstance(enrollments_in_course, Response):
            # Returns a 403 if the request.user can't access grades for the requested user,
            # or a 404 if the requested user does not exist or the course had no enrollments.
            return enrollments_in_course

        paged_enrollments = self.paginator.paginate_queryset(enrollments_in_course, self.request, view=self)
        users = (enrollment.user for enrollment in paged_enrollments)
        grades = CourseGradeFactory().iter(users, course)

        response = []
        for user, course_grade, __ in grades:
            course_grade_res = self._make_grade_response(user, course, course_grade, use_email)
            response.append(course_grade_res)

        return Response(response)


@view_auth_classes()
class CourseGradingPolicy(GradeViewMixin, ListAPIView):
    """
    **Use Case**

        Get the course grading policy.

    **Example requests**:

        GET /api/grades/v0/policy/{course_id}/

    **Response Values**

        * assignment_type: The type of the assignment, as configured by course
          staff. For example, course staff might make the assignment types Homework,
          Quiz, and Exam.

        * count: The number of assignments of the type.

        * dropped: Number of assignments of the type that are dropped.

        * weight: The weight, or effect, of the assignment type on the learner's
          final grade.
    """

    allow_empty = False

    def get(self, request, course_id, **kwargs):
        course = self._get_course(request, course_id, request.user, 'staff')
        if isinstance(course, Response):
            return course
        return Response(GradingPolicySerializer(course.raw_grader, many=True).data)
