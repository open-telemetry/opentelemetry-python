# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# A default event name to be used for logging events when a better event name
# can't be derived from the event's key-value pairs.
DEFAULT_EVENT_NAME = "log"


def time_seconds_to_ns(time_seconds):
    """Converts a time value in seconds to a time value in nanoseconds.

    `time_seconds` is a `float` as returned by `time.time()` which represents
    the number of seconds since the epoch.

    The returned value is an `int` representing the number of nanoseconds since
    the epoch.
    """

    return int(time_seconds * 1e9)


def time_seconds_from_ns(time_nanoseconds):
    """Converts a time value in nanoseconds to a time value in seconds.

    `time_nanoseconds` is an `int` representing the number of nanoseconds since
    the epoch.

    The returned value is a `float` representing the number of seconds since
    the epoch.
    """

    return time_nanoseconds / 1e9


def event_name_from_kv(key_values):
    """A helper function which returns an event name from the given dict, or a
    default event name.
    """

    if key_values is None or "event" not in key_values:
        return DEFAULT_EVENT_NAME

    return key_values["event"]
