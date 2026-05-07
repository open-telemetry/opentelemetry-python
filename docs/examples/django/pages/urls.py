# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from django.urls import path

from .views import home_page_view

urlpatterns = [path("", home_page_view, name="home")]
