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

from os.path import dirname, join

import setuptools

BASE_DIR = dirname(__file__)
VERSION_FILENAME = join(BASE_DIR, "src", "opentelemetry", "util", "version.py")
PACKAGE_INFO = {}
with open(VERSION_FILENAME) as f:
    exec(f.read(), PACKAGE_INFO)

setuptools.setup(
    name="opentelemetry-api",
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
    description="OpenTelemetry Python API",
    include_package_data=True,
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    install_requires=[
        "typing; python_version<'3.5'",
        "aiocontextvars; python_version<'3.7' and python_version>='3.5'",
    ],
    extras_require={},
    license="Apache-2.0",
    package_dir={"": "src"},
    packages=setuptools.find_namespace_packages(
        where="src", include="opentelemetry.*"
    ),
    url=(
        "https://github.com/open-telemetry/opentelemetry-python"
        "/tree/master/opentelemetry-api"
    ),
    zip_safe=False,
    entry_points={
        "opentelemetry_context": [
            "contextvars_context = "
            "opentelemetry.context.contextvars_context:"
            "ContextVarsRuntimeContext",
            "threadlocal_context = "
            "opentelemetry.context.threadlocal_context:"
            "ThreadLocalRuntimeContext",
        ],
        "opentelemetry_meter_provider": [
            "default_meter_provider = "
            "opentelemetry.metrics:DefaultMeterProvider"
        ],
        "opentelemetry_tracer_provider": [
            "default_tracer_provider = "
            "opentelemetry.trace:DefaultTracerProvider"
        ],
    },
)
