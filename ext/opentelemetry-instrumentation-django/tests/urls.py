from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^traced/', views.traced_func),
]
