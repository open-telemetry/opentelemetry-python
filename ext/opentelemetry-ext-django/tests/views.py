from django.http import HttpResponse


def traced(request):  # pylint: disable=unused-argument
    return HttpResponse()


def error(request):  # pylint: disable=unused-argument
    raise ValueError("error")


def excluded(request):  # pylint: disable=unused-argument
    return HttpResponse()


def excluded2(request):  # pylint: disable=unused-argument
    return HttpResponse()
