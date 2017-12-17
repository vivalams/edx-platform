"""
EdX Branding package.

Provides a way to retrieve "branded" parts of the site.

This module provides functions to retrieve basic branded parts
such as the site visible courses, university name and logo.
"""

from xmodule.modulestore.django import modulestore
from xmodule.course_module import CourseDescriptor
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from opaque_keys.edx.locations import SlashSeparatedCourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


def get_visible_courses(orgl,org=None, filter_=None):
    """
    Return the set of CourseOverviews that should be visible in this branded
    instance.

    Arguments:
        org (string): Optional parameter that allows case-insensitive
            filtering by organization.
        filter_ (dict): Optional parameter that allows custom filtering by
            fields on the course.
    """
    courses = []
    current_site_orgs = configuration_helpers.get_current_site_orgs()
    #CourseOverview()
    #k.load_from_module_store('course-v1:edX+DemoX+Demo_Course')
    from opaque_keys.edx.keys import CourseKey
    #CourseKey.from_string(course_id)
    #c_orgs = CourseOverview.load_from_module_store(CourseKey.from_string(course_id)).course_org_new
    #if user:
    #    email = user.email
    #elif user.is_anonymous():
    #    email = None
    #current_course_orgs = k2.split('/') 
    if org:
        # Check the current site's orgs to make sure the org's courses should be displayed
        if not current_site_orgs or org in current_site_orgs:
            courses = CourseOverview.get_all_courses(orgs=[org], filter_=filter_)
    elif current_site_orgs:
        # Only display courses that should be displayed on this site
        courses = CourseOverview.get_all_courses(orgs=current_site_orgs, filter_=filter_)
    else:
        courses = CourseOverview.get_all_courses(filter_=filter_)

    courses = sorted(courses, key=lambda course: course.number)

    # Filtering can stop here.
    if current_site_orgs:
        return courses

    # See if we have filtered course listings in this domain
    filtered_visible_ids = None

    # this is legacy format, which also handle dev case, which should not filter
    subdomain = configuration_helpers.get_value('subdomain', 'default')
    if hasattr(settings, 'COURSE_LISTINGS') and subdomain in settings.COURSE_LISTINGS and not settings.DEBUG:
        filtered_visible_ids = frozenset(
            [SlashSeparatedCourseKey.from_deprecated_string(c) for c in settings.COURSE_LISTINGS[subdomain]]
        )

    #c_orgs = CourseOverview.load_from_module_store(CourseKey.from_string(course_id)).course_org_new
    #aaaallllcourses = []
    #user_oorgs = ['Microsoft']
    #for c_org in c_orgs:
    #for u_org in user_oorgs:
    #        return [course for course in courses if u_org in CourseOverview.load_from_module_store(CourseKey.from_string(course)).course_org_new]
        
    if filtered_visible_ids:
        return [course for course in courses if course.id in filtered_visible_ids]
    else:
        # Filter out any courses based on current org, to avoid leaking these.
        #orgs = configuration_helpers.get_all_orgs()
        #return [course for course in courses if course.location.org not in orgs]
        #user_oorgs = ['edx']
        #user_oorgs = ['Shared']
        #c_orgs = CourseOverview.load_from_module_store(CourseKey.from_string(course_id)).course_org_new
        emty_list = []
        for u_org in orgl:
            for course in courses:
                #if u_org in CourseOverview.load_from_module_store(CourseKey.from_string(str(course.id.to_deprecated_string()))).course_org_new:
                if course.org == u_org:           
                     emty_list.append(course)
        return emty_list
        #return [course for course in courses if u_org in CourseOverview.load_from_module_store(CourseKey.from_string(str(course.id.to_deprecated_string()))).course_org_new]

def get_university_for_request():
    """
    Return the university name specified for the domain, or None
    if no university was specified
    """
    return configuration_helpers.get_value('university')
