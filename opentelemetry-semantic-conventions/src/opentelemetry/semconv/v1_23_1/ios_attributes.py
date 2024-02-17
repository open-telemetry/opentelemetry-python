
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

# pylint: disable=too-many-lines

from enum import Enum


IOS_STATE = "ios.state"
"""
This attribute represents the state the application has transitioned into at the occurrence of the event.
Note: The iOS lifecycle states are defined in the [UIApplicationDelegate documentation](https://developer.apple.com/documentation/uikit/uiapplicationdelegate#1656902), and from which the `OS terminology` column values are derived.
"""


class IosStateValues(Enum):
    ACTIVE = "active"
    """The app has become `active`. Associated with UIKit notification `applicationDidBecomeActive`."""

    INACTIVE = "inactive"
    """The app is now `inactive`. Associated with UIKit notification `applicationWillResignActive`."""

    BACKGROUND = "background"
    """The app is now in the background. This value is associated with UIKit notification `applicationDidEnterBackground`."""

    FOREGROUND = "foreground"
    """The app is now in the foreground. This value is associated with UIKit notification `applicationWillEnterForeground`."""

    TERMINATE = "terminate"
    """The app is about to terminate. Associated with UIKit notification `applicationWillTerminate`."""

