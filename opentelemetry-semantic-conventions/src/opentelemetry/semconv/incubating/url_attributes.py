# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

URL_FRAGMENT = "url.fragment"
"""
The [URI fragment](https://www.rfc-editor.org/rfc/rfc3986#section-3.5) component.
See Also: the attribute is stable now, use :py:const:`opentelemetry.semconv.url_attributes.URL_FRAGMENT` instead.
"""


URL_FULL = "url.full"
"""
Absolute URL describing a network resource according to [RFC3986](https://www.rfc-editor.org/rfc/rfc3986).Note: For network calls, URL usually has `scheme://host[:port][path][?query][#fragment]` format, where the fragment is not transmitted over HTTP, but if it is known, it SHOULD be included nevertheless.
    `url.full` MUST NOT contain credentials passed via URL in form of `https://username:password@www.example.com/`. In such case username and password SHOULD be redacted and attribute's value SHOULD be `https://REDACTED:REDACTED@www.example.com/`.
    `url.full` SHOULD capture the absolute URL when it is available (or can be reconstructed) and SHOULD NOT be validated or modified except for sanitizing purposes.
See Also: the attribute is stable now, use :py:const:`opentelemetry.semconv.url_attributes.URL_FULL` instead.
"""


URL_PATH = "url.path"
"""
The [URI path](https://www.rfc-editor.org/rfc/rfc3986#section-3.3) component.
See Also: the attribute is stable now, use :py:const:`opentelemetry.semconv.url_attributes.URL_PATH` instead.
"""


URL_QUERY = "url.query"
"""
The [URI query](https://www.rfc-editor.org/rfc/rfc3986#section-3.4) component.Note: Sensitive content provided in query string SHOULD be scrubbed when instrumentations can identify it.
See Also: the attribute is stable now, use :py:const:`opentelemetry.semconv.url_attributes.URL_QUERY` instead.
"""


URL_SCHEME = "url.scheme"
"""
The [URI scheme](https://www.rfc-editor.org/rfc/rfc3986#section-3.1) component identifying the used protocol.
See Also: the attribute is stable now, use :py:const:`opentelemetry.semconv.url_attributes.URL_SCHEME` instead.
"""


