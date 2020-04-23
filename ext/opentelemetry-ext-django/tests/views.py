from django.http import HttpResponse


def traced(request):  # pylint: disable=unused-argumentt
    return HttpResponse()


def error(request):
    raise ValueError("error")
