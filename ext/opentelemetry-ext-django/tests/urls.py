from django.conf.urls import url
from .views import traced, error

urlpatterns = [
    url(r'^traced/', traced),
    url(r'^error/', error),
]
