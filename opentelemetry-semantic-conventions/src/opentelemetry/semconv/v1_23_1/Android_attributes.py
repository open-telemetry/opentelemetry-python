
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

class AndroidAttributes:

    
    ANDROID_OS_API_LEVEL = "android.os.api_level"
    
    """
    Uniquely identifies the framework API revision offered by a version (`os.version`) of the android operating system. More information can be found [here](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels).
    """

    
    ANDROID_STATE = "android.state"
    
    """
    This attribute represents the state the application has transitioned into at the occurrence of the event.
    Note: The Android lifecycle states are defined in [Activity lifecycle callbacks](https://developer.android.com/guide/components/activities/activity-lifecycle#lc), and from which the `OS identifiers` are derived.
    """
class AndroidStateValues(Enum):
    CREATED = "created"
    """Any time before Activity.onResume() or, if the app has no Activity, Context.startService() has been called in the app for the first time."""

    BACKGROUND = "background"
    """Any time after Activity.onPause() or, if the app has no Activity, Context.stopService() has been called when the app was in the foreground state."""

    FOREGROUND = "foreground"
    """Any time after Activity.onResume() or, if the app has no Activity, Context.startService() has been called when the app was in either the created or background states."""

