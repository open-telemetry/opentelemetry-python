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

from unittest import TestCase

from opentelemetry.opentelemetry import OpenTelemetry


class TestOpenTelemetry(TestCase):
    def test_opentelemetry(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self):
                super().__init__()

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")

    def test_opentelemetry_slash(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, /):
                super().__init__()

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")

    def test_opentelemetry_args(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, *args):
                super().__init__(*args)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )

    def test_opentelemetry_slash_args(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, /, *args):
                super().__init__(*args)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )

    def test_opentelemetry_a_b(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b):
                super().__init__(a, b)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )

    def test_opentelemetry_a_b_slash(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /):
                super().__init__(a, b)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )

    def test_opentelemetry_a_b_args(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, *args):
                super().__init__(a, b, *args)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )

    def test_opentelemetry_a_b_slash_args(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, *args):
                super().__init__(a, b, *args)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )

    def test_opentelemetry_a_b_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, c="c", d="d"):
                super().__init__(a, b, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )

    def test_opentelemetry_a_b_slash_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, c="c", d="d"):
                super().__init__(a, b, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )

    def test_opentelemetry_a_b_args_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, *args, c="c", d="d"):
                super().__init__(a, b, *args, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc', d='dd')",
        )

    def test_opentelemetry_a_b_slash_args_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, *args, c="c", d="d"):
                super().__init__(a, b, *args, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', c='cc', d='dd')",
        )

    def test_opentelemetry_asterisk_a_b(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, *, a, b):
                super().__init__(a, b)

        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )

    def test_opentelemetry_slash_asterisk_a_b(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, /, *, a, b):
                super().__init__(a, b)

        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )

    def test_x_opentelemetry_a_b_asterisk_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, *, c, d):
                super().__init__(a, b, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, *, c="c", d="d"):
                super().__init__(a, b, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="dd")),
            "OpenTelemetryChild('a', 'b', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )

    def test_x_opentelemetry_a_b_slash_asterisk_c_d(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, *, c, d):
                super().__init__(a, b, c=c, d=d)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

    def test_opentelemetry_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )

    def test_opentelemetry_slash_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, /, **kwargs):
                super().__init__(**kwargs)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )

    def test_opentelemetry_args_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

    def test_opentelemetry_slash_args_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, /, *args, **kwargs):
                super().__init__(*args, **kwargs)

        self.assertEqual(repr(OpenTelemetryChild()), "OpenTelemetryChild()")
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild(a='a', b='b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

    def test_opentelemetry_a_b_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, **kwargs):
                super().__init__(a, b, **kwargs)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", b="b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild(a="a", b="b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

    def test_opentelemetry_a_b_slash_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, **kwargs):
                super().__init__(a, b, **kwargs)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c", d="d")),
            "OpenTelemetryChild('a', 'b', c='c', d='d')",
        )

    def test_opentelemetry_a_b_args_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, *args, **kwargs):
                super().__init__(a, b, *args, **kwargs)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )

    def test_opentelemetry_a_b_slash_args_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, /, *args, **kwargs):
                super().__init__(a, b, *args, **kwargs)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d")),
            "OpenTelemetryChild('a', 'b', 'c', 'd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", "c", "d", e="e", f="f")),
            "OpenTelemetryChild('a', 'b', 'c', 'd', e='e', f='f')",
        )

    def test_opentelemetry_a_b_c_d_kwargs(self):
        class OpenTelemetryChild(OpenTelemetry):
            def __init__(self, a, b, c="c", d="d", **kwargs):
                super().__init__(a, b, c=c, d=d, **kwargs)

        self.assertEqual(
            repr(OpenTelemetryChild("a", "b")), "OpenTelemetryChild('a', 'b')"
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="c")),
            "OpenTelemetryChild('a', 'b')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="d")),
            "OpenTelemetryChild('a', 'b', c='cc')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd')",
        )
        self.assertEqual(
            repr(OpenTelemetryChild("a", "b", c="cc", d="dd", e="e", f="f")),
            "OpenTelemetryChild('a', 'b', c='cc', d='dd', e='e', f='f')",
        )
