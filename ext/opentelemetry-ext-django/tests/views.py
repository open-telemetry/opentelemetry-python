from django.http import HttpResponse


def traced(request):
    return HttpResponse()


def error(request):
    raise ValueError("error")
