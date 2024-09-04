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

# The importlib-metadata library has introduced breaking changes before to its
# API, this module is kept just to act as a layer between the
# importlib-metadata library and our project if in any case it is necessary to
# do so.

from sys import version_info

if version_info.minor < 10:

    # pylint: disable=import-error
    from importlib_metadata import version  # type: ignore
    from importlib_metadata import EntryPoint, EntryPoints
    from importlib_metadata import (
        entry_points as importlib_metadata_entry_points,
    )

else:

    from importlib.metadata import EntryPoint, EntryPoints
    from importlib.metadata import (
        entry_points as importlib_metadata_entry_points,
    )
    from importlib.metadata import version


def entry_points(**params) -> EntryPoints:  # type: ignore
    """
    Same as entry_points but requires at least one argument

    For Python 3.8 or 3.9:

    isinstance(
        importlib_metadata.entry_points(), importlib_metadata.EntryPoints
    )

    evaluates to True.

    For Python 3.10, 3.11:

    isinstance(
        importlib.metadata.entry_points(), importlib.metadata.SelectableGroups
    )

    evaluates to True.

    For Python 3.12:

    isinstance(
        importlib.metadata.entry_points(), importlib.metadata.EntryPoints
    )

    evaluates to True.

    So, when called with no arguments, entry_points returns objects of
    different types depending on the Python version that is being used. This is
    obviously very problematic. Nevertheless, in our code we don't ever call
    entry_points without arguments, so the approach here is to redefine
    entry_points so that it requires at least one argument.
    """

    if not params:  # type: ignore
        raise ValueError("entry_points requires at least one argument")
    return importlib_metadata_entry_points(**params)  # type: ignore


__all__ = ["entry_points", "version", "EntryPoint", "EntryPoints"]
