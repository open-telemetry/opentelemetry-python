# Copyright 2019, OpenTelemetry Authors
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

import os

import setuptools

BASE_DIR = os.path.dirname(__file__)
VERSION_FILENAME = os.path.join(BASE_DIR, "src", "ot_otel_bridge", "version.py")
PACKAGE_INFO = {}
with open(VERSION_FILENAME) as f:
    exec(f.read(), PACKAGE_INFO)

setuptools.setup(
    name="ot_otel_bridge",
    version=PACKAGE_INFO["__version__"],
    author="OpenTelemetry Authors",
    author_email="cncf-opentelemetry-contributors@lists.cncf.io",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="OpenTracing OpenTelemetry Python bridge",
    include_package_data=True,
    long_description="OpenTracing OpenTelemetry Python bridge",
    install_requires=[
        "opentelemetry-api==0.1.dev0",
        "opentelemetry-sdk==0.1.dev0",
        "typing; python_version<'3.5'",
        "basictracer>=3.0,<4",
    ],
    extras_require={},
    license="Apache-2.0",
    package_dir={"": "src"},
    packages=setuptools.find_namespace_packages(
        where="src", include="ot_otel_bridge.*"
    ),
    url=(
        "https://github.com/open-telemetry/opentelemetry-python"
        "/tree/master/bridge/opentracing"
    ),
    zip_safe=False,
)
