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


from sys import version_info
from typing import Dict, Tuple, Union, overload, Optional, List

# FIXME remove this when support for 3.7 is dropped.
if version_info.minor == 7:
    # pylint: disable=import-error
    from importlib_metadata import EntryPoint
    from importlib_metadata import (
        entry_points as importlib_metadata_entry_points,
    )
    from importlib_metadata import version

    # This is a cache to avoid going through creating a dictionary for all
    # entry points for 3.7 every time the entry points function is called.
    result_entry_points_37: Dict[str, Tuple[EntryPoint, ...]] = {}

    @overload
    def entry_points(
        group: None, name: None
    ) -> Dict[str, Tuple[EntryPoint, ...]]:
        ...

    @overload
    def entry_points(group: str, name: None) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: None, name: str) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: str, name: str) -> Tuple[EntryPoint, ...]:
        ...

    def entry_points(
        group: Optional[str] = None,
        name: Optional[str] = None
    ) -> Union[Tuple[EntryPoint, ...], Dict[str, Tuple[EntryPoint, ...]]]:

        if group is None and name is None:

            if not result_entry_points_37:

                entry_point: EntryPoint

                for entry_point in importlib_metadata_entry_points():

                    if entry_point.group not in result_entry_points_37.keys():
                        result_entry_points_37[entry_point.group] = []  # type: ignore

                    result_entry_points_37[entry_point.group].append(  # type: ignore
                        entry_point
                    )

                for key, value in result_entry_points_37.items():
                    result_entry_points_37[key] = tuple(value)

            return result_entry_points_37

        if group is not None and name is None:
            return tuple(  # type: ignore
                entry_point  # type: ignore
                for entry_point in importlib_metadata_entry_points(group=group)
            )

        if group is None and name is not None:
            return tuple(  # type: ignore
                entry_point  # type: ignore
                for entry_point in importlib_metadata_entry_points(name=name)
            )

        return tuple(  # type: ignore
            entry_point  # type: ignore
            for entry_point in importlib_metadata_entry_points(
                group=group, name=name
            )
        )

# FIXME remove this file when support for 3.9 is dropped.
elif version_info.minor in (8, 9):
    # pylint: disable=import-error
    from importlib.metadata import EntryPoint  # type: ignore
    from importlib.metadata import (  # type: ignore
        entry_points as importlib_metadata_entry_points,
    )
    from importlib.metadata import version

    @overload  # type: ignore
    def entry_points(
        group: None, name: None
    ) -> Dict[str, Tuple[EntryPoint, ...]]:
        ...

    @overload
    def entry_points(group: str, name: None) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: None, name: str) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: str, name: str) -> Tuple[EntryPoint, ...]:
        ...

    def entry_points(
        group: Optional[str] = None,
        name: Optional[str] = None
    ) -> Union[Tuple[EntryPoint, ...], Dict[str, Tuple[EntryPoint, ...]]]:

        result_key_entry_points: Dict[str, Tuple[EntryPoint, ...]] = (
            importlib_metadata_entry_points()  # type: ignore
        )

        if group is None and name is None:
            return result_key_entry_points

        if group is not None and group not in result_key_entry_points.keys():
            return tuple()

        if group is not None and name is None:
            return result_key_entry_points[group]

        if group is None and name is not None:

            name_entry_points = []

            for result_entry_points in result_key_entry_points.values():
                for result_entry_point in result_entry_points:
                    if result_entry_point.name == name:
                        name_entry_points.append(result_entry_point)

            return tuple(name_entry_points)

        name_group_entry_points = []

        for result_entry_point in result_key_entry_points[group]:  # type: ignore
            if result_entry_point.name == name:
                name_group_entry_points.append(result_entry_point)
                break

        return tuple(name_group_entry_points)

else:
    from importlib.metadata import EntryPoint  # type: ignore
    from importlib.metadata import (  # type: ignore
        entry_points as importlib_metadata_entry_points,
    )
    from importlib.metadata import version

    @overload  # type: ignore
    def entry_points(
        group: None, name: None
    ) -> Dict[str, Tuple[EntryPoint, ...]]:
        ...

    @overload
    def entry_points(group: str, name: None) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: None, name: str) -> Tuple[EntryPoint, ...]:
        ...

    @overload
    def entry_points(group: str, name: str) -> Tuple[EntryPoint, ...]:
        ...

    def entry_points(
        group: Optional[str] = None,
        name: Optional[str] = None
    ) -> Union[Tuple[EntryPoint, ...], Dict[str, Tuple[EntryPoint, ...]]]:

        if group is None and name is None:
            result_entry_points: Dict[str, Tuple[EntryPoint, ...]] = {}

            key: str
            value: List[EntryPoint]

            for key, value in importlib_metadata_entry_points().items():  # type: ignore
                result_entry_points[key] = tuple(value)

            return result_entry_points

        if group is not None and name is None:
            return tuple(  # type: ignore
                entry_point  # type: ignore
                for entry_point in importlib_metadata_entry_points(group=group)
            )

        if group is None and name is not None:
            return tuple(  # type: ignore
                entry_point  # type: ignore
                for entry_point in importlib_metadata_entry_points(name=name)
            )

        return tuple(  # type: ignore
            entry_point  # type: ignore
            for entry_point in importlib_metadata_entry_points(
                group=group, name=name
            )
        )

__all__ = [
    "entry_points",
    "version",
    "EntryPoint",
]
