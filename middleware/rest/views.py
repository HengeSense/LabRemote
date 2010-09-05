from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django.core import serializers
from django.http import HttpResponse, Http404
import json

from models import *

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]

def json_response(obj):
    """ A shorthand for dumping json data """
    data = json.dumps(obj)
    return HttpResponse(data, mimetype='application/json')
    
def valid_key(view_func):
    """ A decorator checking the key for validity """
    def _decorated(request, user, session_key, *args, **kwargs):
        try:
            assistant = Assistant.objects.get(pk=user)
        except Assistant.DoesNotExist:
            return json_response({"error":"no such user"})
            
        if assistant.get_session_key() != session_key:
            return json_response({"error":"invalid session key"})
            
        request.assistant = assistant
        return view_func(request, user, session_key, *args, **kwargs)
    return _decorated

def get_object(request, object, id):
    """ Generic dump json method """
    if object not in ('student', 'course', 'activity', 'attendance'):
        raise Http404

    if object == 'student':
        klass = Student
    elif object == 'course':
        klass = Course
    elif object == 'activity':
        klass = Activity
    elif object == 'attendance':
        klass = Attendance
        
    obj = get_object_or_404(klass, pk=id)
    data = serializers.serialize('json', [obj])
    return HttpResponse(data, mimetype='application/json')

def login(request, qr_code):
    """ Validates a login request """
    try:
        assistant = Assistant.objects.get(code=qr_code)
    except Assistant.DoesNotExist:
        return json_response({"login": "invalid"})

    courses = [c.name for c in assistant.courses.all()]
    response = {"login": "ok", "user": assistant.id, "name": assistant.name, "courses": courses}
    
    return json_response(response)
    
@valid_key
def timetable(request, user, session_key):
    assistant = request.assistant
    timetable = dict()
    
    for (i, day) in enumerate(DAYS):
        activities = {}
        for c in assistant.courses.all():
            acts = Activity.objects.filter(course=c, day=i) 
            for a in acts:
                activities[a.interval] = a.group.name
        timetable[day] = activities
    
    return json_response({"timetable" : timetable})

@valid_key
def group(request, user, session_key, name):
    assistant = request.assistant
    
    group = get_object_or_404(Group, name=name)
    students = [ {"name": s.name, 
                "grade": 0, # TODO
                "id": s.id,
                "avatar": s.avatar} for s in group.students.all() ]
                
    return json_response({"name": name, "students": students})
    
@valid_key
def student(request, user, session_key, course, id):
    student = get_object_or_404(Student, pk=id)
    course = get_object_or_404(Course, name=course)
    
    atts = Attendance.objects.filter(student=student, course=course)
    attendance = [ {a.week :
                    {"grade": a.grade}
                    } for a in atts ]
    
    return json_response({"name": student.name,
        "grade": 0, #TODO
        "id": student.id,
        "avatar": student.avatar,
        "attendance": attendance})
        
@valid_key
def search(request, user, session_key, query):
    """ Search for users having query in name.
    Returns a list of maximum 20 results """
    
    limit = 20
    # TODO: query db, not this crap
    query = query.lower()
    results = []
    for u in Student.objects.all():
        if query in u.name.lower():
            results.append(u.info_dict())
            if len(results) >= limit:
                break
    
    return json_response(results)