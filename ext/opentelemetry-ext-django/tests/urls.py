from django.conf.urls import url

from .views import error, traced  # pylint: disable=import-error

urlpatterns = [
    url(r"^traced/", traced),
    url(r"^error/", error),
]
