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

base_dir = os.path.dirname(__file__)

package_info = {}
with open(os.path.join(base_dir, "src", "opentelemetry", "sdk", "version.py")) as f:
    exec(f.read(), package_info)

setuptools.setup(
    name="opentelemetry-sdk",
    version=package_info["__version__"],  # noqa
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
    description="OpenTelemetry Python SDK",
    include_package_data=True,
    long_description=open("README.rst").read(),
    install_requires=[
    ],
    extras_require={},
    license="Apache-2.0",
    package_dir={"": "src"},
    packages=setuptools.find_namespace_packages(where="src"),
    url="https://github.com/open-telemetry/opentelemetry-python/tree/master/opentelemetry-sdk",
    zip_safe=False,
)
