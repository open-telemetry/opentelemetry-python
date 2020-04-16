from django.http import HttpResponse


def traced_func(request):
    response = HttpResponse()
    response['numspans'] = 1
    return response
