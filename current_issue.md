What happened?
Following the examples in the docs, the autoinstrumentation on Django is not sufficient to cause data to be sent to STDOUT, as the docs claim would happen

Steps to Reproduce
mkdir /tmp/bob
cd /tmp/bob
virtualenv venv
venv/bin/pip install django opentelemetry-instrumentation-django opentelemetry-sdk requests
venv/bin/django-admin startproject mysite
Then edited mysite to insert:

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from opentelemetry.instrumentation.django import DjangoInstrumentor # NEW
def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    DjangoInstrumentor().instrument() # NEW
...
Run the site:

venv/bin/python mysite/manage.py runserver
View localhost:8000 on the browser, curl it, etc. The only thing that shows up:

Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).

You have 18 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): admin, auth, contenttypes, sessions.
Run 'python manage.py migrate' to apply them.
September 18, 2024 - 20:41:30
Django version 5.1.1, using settings 'mysite.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.

[18/Sep/2024 20:41:34] "GET / HTTP/1.1" 200 12068
Not Found: /favicon.ico
[18/Sep/2024 20:41:34] "GET /favicon.ico HTTP/1.1" 404 2208
[18/Sep/2024 20:41:47] "GET /?param=hello HTTP/1.1" 200 12068
Expected Result
something like the docs say:

{
    "name": "home_page_view",
    "context": {
        "trace_id": "0xed88755c56d95d05a506f5f70e7849b9",
        "span_id": "0x0a94c7a60e0650d5",
        "trace_state": "{}"
    },
    "kind": "SpanKind.SERVER",
    "parent_id": "0x3096ef92e621c22d",
    "start_time": "2020-04-26T01:49:57.205833Z",
    "end_time": "2020-04-26T01:49:57.206214Z",
    "status": {
        "status_code": "OK"
    },
    "attributes": {
        "http.request.method": "GET",
        "server.address": "localhost",
        "url.scheme": "http",
        "server.port": 8000,
        "url.full": "http://localhost:8000/?param=hello",
        "server.socket.address": "127.0.0.1",
        "network.protocol.version": "1.1",
        "http.response.status_code": 200
    },
    "events": [],
    "links": []
}
Actual Result
No fancy open telemetry output, as the docs claim.

Additional context
#4125 indicates that there's something possibly missing in the docs, and that the auto-instrumentor works.
While this is possible and I'll try that later this week, I was hoping to not have to modify the execution command and instead do the manage.py modification.

Happy to put some work into this, but I'd like to first confirm that I'm not doing something silly