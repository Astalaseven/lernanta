import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q

from tags.models import GeneralTaggedItem
from projects.models import Project
from signups.models import Signup
from learn import db


def _get_listed_courses():
    listed = db.Course.objects.filter(
        date_removed__isnull=True, 
        verified=True
    ).order_by("-date_added")
    return listed


def get_active_languages():
    """ Return a list of the active language currently in use """
    language_list = _get_listed_courses().values_list('language').distinct('language')
    language_dict = dict(settings.LANGUAGES)
    languages = [(l[0], language_dict[l[0]],) for l in language_list]
    return languages


def get_listed_courses():
    """ return all the projects that should be listed """
    listed = _get_listed_courses()
    #TODO convert to JSON?
    return listed


def get_popular_tags(max_count=10):
    """ return a list of popular tags """
    listed = _get_listed_courses()
    return db.CourseTags.objects.filter(course__in=listed).values(
        'tag').annotate(tagged_count=Count('course')).order_by(
        '-tagged_count')[:max_count]


def get_weighted_tags(min_count=2, min_weight=1.0, max_weight=7.0):
    return []


def get_tags_for_courses(courses, exclude=[], max_tags=6):
    tags = db.CourseTags.objects.filter(course__url__in=[c.url for c in courses])
    tags = tags.exclude(tag__in=exclude)
    tags = tags.values('tag')
    tags = tags.annotate(tagged_count=Count('course'))
    tags = tags.order_by('-tagged_count')[:max_tags]
    return tags


def get_courses_by_tag(tag_name, courses=None):
    course_ids = db.CourseTags.objects.filter(
        tag=tag_name
    ).values_list('course', flat=True)
    ret = db.Course.objects.filter(id__in=course_ids)
    if courses:
        ret.filter(url__in=[c.url for c in courses])
    return ret


def get_courses_by_tags(tag_list, courses=None):
    "this will return courses that have all the tags in tag_list"
    if not courses:
        courses = get_listed_courses()
    for tag in tag_list:
        courses = get_courses_by_tag(tag, courses)
    return courses


def get_courses_by_list(list_name, courses=None):
    """ return a list of projects
        if courses != None, only the courses in courses and the list
        will be returned.
    """
    course_ids = db.CourseListEntry.objects.filter(
        course_list__name = list_name
    ).values_list('course', flat=True)
    ret = db.Course.objects.filter(id__in=course_ids)
    if courses:
        ret.filter(url__in=[c.url for c in courses])
    return ret


# new course index API functions ->
def add_course_listing(course_url, title, description, data_url, language, thumbnail_url, tags):
    if db.Course.objects.filter(url=course_url).exists():
        raise Exception("A course with that URL already exist. Try update?")
    course_listing_db = db.Course(
        title=title,
        description=description,
        url=course_url,
        data_url=data_url,
        language=language,
        thumbnail_url=thumbnail_url
    )
    course_listing_db.save()
    update_course_listing(course_url, tags=tags)
    #TODO schedule task to verify listing


def update_course_listing(course_url, title=None, description=None, data_url=None, language=None, thumbnail_url=None, tags=None):
    listing= db.Course.objects.get(url=course_url)
    if title:
        listing.title = title
    if description:
        listing.description = description
    if data_url:
        listing.data_url = data_url
    if language:
        listing.language = language
    if thumbnail_url:
        listing.thumbnail_url = thumbnail_url
    listing.save()

    if tags:
        db.CourseTags.objects.filter(course=listing, internal=False).delete()
        for tag in tags:
            if not db.CourseTags.objects.filter(course=listing, tag=tag).exists():
                course_tag = db.CourseTags(tag=tag, course=listing)
                course_tag.save()


def remove_course_listing(course_url, reason):
    course_listing_db = db.Course.objects.get(url=course_url)
    course_listing_db.date_removed = datetime.datetime.utcnow()
    course_listing_db.save()


def create_list(name, title, url):
    if db.List.objects.filter(name=name).exists():
        raise Exception("A list with that name already exists")

    course_list = db.List(
        name = name,
        title = title,
        url = url
    )
    course_list.save()


def add_course_to_list(course_url, list_name):
    try:
        course_list = db.List.objects.get(name=list_name)
    except:
        raise Exception("List doesn't exist")

    try:
        course = db.Course.objects.get(url=course_url)
    except:
        raise Exception("Course at given URL doesn't exist")

    if db.CourseListEntry.objects.filter(course_list=course_list, course=course).exists():
        raise Exception("Course already in list")

    entry = db.CourseListEntry(
        course_list = course_list,
        course = course
    )
    entry.save()

