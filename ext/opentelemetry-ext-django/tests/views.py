from django.http import HttpResponse


def traced(request):
    return HttpResponse()


def error(request):
    return HttpResponse()
    raise ValueError("error")
