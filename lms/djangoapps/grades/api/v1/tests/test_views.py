"""
Tests for v1 views
"""
from datetime import datetime
import ddt
from django.core.urlresolvers import reverse
from mock import patch
from opaque_keys import InvalidKeyError
from pytz import UTC
from rest_framework import status
from rest_framework.test import APITestCase

from capa.tests.response_xml_factory import MultipleChoiceResponseXMLFactory
from edx_oauth2_provider.tests.factories import AccessTokenFactory, ClientFactory
from lms.djangoapps.courseware.tests.factories import GlobalStaffFactory, StaffFactory
from lms.djangoapps.grades.tests.utils import mock_get_score
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase, TEST_DATA_SPLIT_MODULESTORE


class GradeViewTestMixin(SharedModuleStoreTestCase):
    """
    Mixin class for grades related view tests
    
    The following tests assume that the grading policy is the edX default one:
    {
        "GRADER": [
            {
                "drop_count": 2,
                "min_count": 12,
                "short_label": "HW",
                "type": "Homework",
                "weight": 0.15
            },
            {
                "drop_count": 2,
                "min_count": 12,
                "type": "Lab",
                "weight": 0.15
            },
            {
                "drop_count": 0,
                "min_count": 1,
                "short_label": "Midterm",
                "type": "Midterm Exam",
                "weight": 0.3
            },
            {
                "drop_count": 0,
                "min_count": 1,
                "short_label": "Final",
                "type": "Final Exam",
                "weight": 0.4
            }
        ],
        "GRADE_CUTOFFS": {
            "Pass": 0.5
        }
    }
    """
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    @classmethod
    def setUpClass(cls):
        super(GradeViewTestMixin, cls).setUpClass()

        cls.courses = []

        for i in xrange(3):
            name = 'test_course ' + str(i)
            run = 'Testing_Course_' + str(i)
            course = cls._create_test_course_with_default_grading_policy(name, run)
            cls.courses.append(course)

        cls.course_keys = [course.id for course in cls.courses]

        cls.password = 'test'
        cls.staff = UserFactory(username='staff', password=cls.password, is_staff=True)
        cls.student = UserFactory(username='dummy', password=cls.password)
        cls.other_student = UserFactory(username='foo', password=cls.password)
        cls.other_user = UserFactory(username='bar', password=cls.password)
        date = datetime(2017, 11, 10, tzinfo=UTC)
        for user in (cls.student, cls.other_student, ):
            CourseEnrollmentFactory(
                course_id=cls.courses[0].id,
                user=user,
                created=date,
            )

    def setUp(self):
        super(GradeViewTestMixin, self).setUp()
        self.client.login(username=self.student.username, password=self.password)

    @classmethod
    def _create_test_course_with_default_grading_policy(cls, display_name, run):
        course = CourseFactory.create(display_name=display_name, run=run)

        chapter = ItemFactory.create(
            category='chapter',
            parent_location=course.location,
            display_name="Chapter 1",
        )
        # create a problem for each type and minimum count needed by the grading policy
        # A section is not considered if the student answers less than "min_count" problems
        for grading_type, min_count in (("Homework", 12), ("Lab", 12), ("Midterm Exam", 1), ("Final Exam", 1)):
            for num in xrange(min_count):
                section = ItemFactory.create(
                    category='sequential',
                    parent_location=chapter.location,
                    due=datetime(2017, 12, 18, 11, 30, 00),
                    display_name='Sequential {} {}'.format(grading_type, num),
                    format=grading_type,
                    graded=True,
                )
                vertical = ItemFactory.create(
                    category='vertical',
                    parent_location=section.location,
                    display_name='Vertical {} {}'.format(grading_type, num),
                )
                ItemFactory.create(
                    category='problem',
                    parent_location=vertical.location,
                    display_name='Problem {} {}'.format(grading_type, num),
                )

        return course

    def test_anonymous(self):
        """
        Test that an anonymous user cannot access the API and an error is received.
        """
        self.client.logout()
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_self_get_grade(self):
        """
        Test that a user can successfully request her own grade.
        """
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_nonexistent_user(self):
        """
        Test that a request for a nonexistent username returns an error.
        """
        self.client.logout()
        self.client.login(username=self.staff.username, password=self.password)
        resp = self.client.get(self.get_url('IDoNotExist'))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(resp.data['error_code'], 'user_does_not_exist')  # pylint: disable=no-member

    def test_other_get_grade(self):
        """
        Test that if a user requests the grade for another user, she receives an error.
        """
        self.client.logout()
        self.client.login(username=self.other_student.username, password=self.password)
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(resp.data['error_code'], 'user_mismatch')  # pylint: disable=no-member

    def test_self_get_grade_not_enrolled(self):
        """
        Test that a user receives an error if she requests
        her own grade in a course where she is not enrolled.
        """
        # a user not enrolled in the course cannot request her grade
        self.client.logout()
        self.client.login(username=self.other_user.username, password=self.password)
        resp = self.client.get(self.get_url(self.other_user.username))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'user_or_course_does_not_exist'
        )

    def test_wrong_course_key(self):
        """
        Test that a request for an invalid course key returns an error.
        """
        def mock_from_string(*args, **kwargs):  # pylint: disable=unused-argument
            """Mocked function to always raise an exception"""
            raise InvalidKeyError('foo', 'bar')

        with patch('opaque_keys.edx.keys.CourseKey.from_string', side_effect=mock_from_string):
            resp = self.client.get(self.get_url(self.student.username))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'invalid_course_key'
        )

    def test_course_does_not_exist(self):
        """
        Test that requesting a valid, nonexistent course key returns an error as expected.
        """
        base_url = reverse(
            self.namespaced_url,
            kwargs={
                'course_id': 'course-v1:MITx+8.MechCX+2014_T1',
            }
        )
        url = "{0}?username={1}".format(base_url, self.student.username)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'user_or_course_does_not_exist'
        )


@ddt.ddt
class CourseGradeViewTest(GradeViewTestMixin, APITestCase):
    """
    Tests for grades related to a course
        i.e. /api/grades/v1/course_grade/{course_id}/users/{username}=(student|all)
    """

    @classmethod
    def setUpClass(cls):
        super(CourseGradeViewTest, cls).setUpClass()
        cls.namespaced_url = 'grades_api:v1:course_grades'

    def setUp(self):
        super(CourseGradeViewTest, self).setUp()

    def get_url(self, username):
        """
        Helper function to create the url
        """
        base_url = reverse(
            self.namespaced_url,
            kwargs={
                'course_id': self.course_keys[0],
            }
        )
        return "{0}?username={1}".format(base_url, username)

    def test_anonymous(self):
        """
        Test that an anonymous user cannot access the API and an error is received.
        """
        self.client.logout()
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_self_get_grade(self):
        """
        Test that a user can successfully request her own grade.
        """
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_nonexistent_user(self):
        """
        Test that a request for a nonexistent username returns an error.
        """
        self.client.logout()
        self.client.login(username=self.staff.username, password=self.password)
        resp = self.client.get(self.get_url('IDoNotExist'))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(resp.data['error_code'], 'user_does_not_exist')  # pylint: disable=no-member

    def test_other_get_grade(self):
        """
        Test that if a user requests the grade for another user, she receives an error.
        """
        self.client.logout()
        self.client.login(username=self.other_student.username, password=self.password)
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(resp.data['error_code'], 'user_mismatch')  # pylint: disable=no-member

    def test_self_get_grade_not_enrolled(self):
        """
        Test that a user receives an error if she requests
        her own grade in a course where she is not enrolled.
        """
        # a user not enrolled in the course cannot request her grade
        self.client.logout()
        self.client.login(username=self.other_user.username, password=self.password)
        resp = self.client.get(self.get_url(self.other_user.username))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'user_or_course_does_not_exist'
        )

    def test_wrong_course_key(self):
        """
        Test that a request for an invalid course key returns an error.
        """
        def mock_from_string(*args, **kwargs):  # pylint: disable=unused-argument
            """Mocked function to always raise an exception"""
            raise InvalidKeyError('foo', 'bar')

        with patch('opaque_keys.edx.keys.CourseKey.from_string', side_effect=mock_from_string):
            resp = self.client.get(self.get_url(self.student.username))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'invalid_course_key'
        )

    def test_course_does_not_exist(self):
        """
        Test that requesting a valid, nonexistent course key returns an error as expected.
        """
        base_url = reverse(
            self.namespaced_url,
            kwargs={
                'course_id': 'course-v1:MITx+8.MechCX+2014_T1',
            }
        )
        url = "{0}?username={1}".format(base_url, self.student.username)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(
            resp.data['error_code'],  # pylint: disable=no-member
            'user_or_course_does_not_exist'
        )

    def test_no_grade(self):
        """
        Test the grade for a user who has not answered any test.
        """
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        expected_data = [{
            'user': self.student.username,
            'course_key': str(self.course_keys[0]),
            'passed': False,
            'percent': 0.0,
            'letter_grade': None
        }]

        self.assertEqual(resp.data, expected_data)  # pylint: disable=no-member

    # @ddt.data(
    #     ((2, 5), {'letter_grade': None, 'percent': 0.4, 'passed': False}),
    #     ((5, 5), {'letter_grade': 'Pass', 'percent': 1, 'passed': True}),
    # )
    # @ddt.unpack
    # def test_grade(self, grade, result):
    #     """
    #     Test that the user gets her grade in case she answered tests with an insufficient score.
    #     """
    #     with mock_get_score(*grade):
    #         resp = self.client.get(self.get_url(self.student.username))
    #     self.assertEqual(resp.status_code, status.HTTP_200_OK)
    #     expected_data = {
    #         'user': self.student.username,
    #         'course_key': str(self.course_keys[0]),
    #     }
        
    #     expected_data.update(result)
    #     raise ValueError('RESPONSE: ', resp.data, result)
    #     self.assertEqual(resp.data, [expected_data])  # pylint: disable=no-member

    def test_username_all_as_student(self):
        """
        Test requesting with username == 'all' and no staff access
        returns 403 forbidden
        """
        resp = self.client.get(self.get_url('all'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error_code', resp.data)  # pylint: disable=no-member
        self.assertEqual(resp.data['error_code'], 'user_mismatch')  # pylint: disable=no-member

    def test_username_all_as_staff(self):
        """
        Test requesting with username == 'all' and staff access
        returns all user grades for course
        """
        self.client.logout()
        self.client.login(username=self.staff.username, password=self.password)
        resp = self.client.get(self.get_url('all'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)


@ddt.ddt
class UserGradesViewTest(GradeViewTestMixin, APITestCase):
    """
    Tests for grades related to a user
        i.e. /api/grades/v1/user_grades/{username}=(student|all)
    """

    @classmethod
    def setUpClass(cls):
        super(UserGradesViewTest, cls).setUpClass()
        cls.namespaced_url = 'grades_api:v1:user_grades'

    def setUp(self):
        super(UserGradesViewTest, self).setUp()

    def get_url(self, username):
        """
        Helper function to create the url
        """
        base_url = reverse(self.namespaced_url)
        return "{0}?username={1}".format(base_url, username)

    def test_anonymous(self):
        """
        """
        self.client.logout()
        resp = self.client.get(self.get_url(self.student.username))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

