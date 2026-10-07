# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

BROWSER_BRANDS: Final = "browser.brands"
"""
Array of brand name and version separated by a space.
Note: This value is intended to be taken from the [UA client hints API](https://wicg.github.io/ua-client-hints/#interface) (`navigator.userAgentData.brands`).
"""

BROWSER_DOCUMENT_URL_FULL: Final = "browser.document.url.full"
"""
Absolute URL of the current browser document according to [RFC3986](https://www.rfc-editor.org/rfc/rfc3986).
"""

BROWSER_LANGUAGE: Final = "browser.language"
"""
Preferred language of the user using the browser.
Note: This value is intended to be taken from the Navigator API `navigator.language`.
"""

BROWSER_MOBILE: Final = "browser.mobile"
"""
A boolean that is true if the browser is running on a mobile device.
Note: This value is intended to be taken from the [UA client hints API](https://wicg.github.io/ua-client-hints/#interface) (`navigator.userAgentData.mobile`). If unavailable, this attribute SHOULD be left unset.
"""

BROWSER_PLATFORM: Final = "browser.platform"
"""
The platform on which the browser is running.
Note: This value is intended to be taken from the [UA client hints API](https://wicg.github.io/ua-client-hints/#interface) (`navigator.userAgentData.platform`). If unavailable, the legacy `navigator.platform` API SHOULD NOT be used instead and this attribute SHOULD be left unset in order for the values to be consistent.
The list of possible values is defined in the [W3C User-Agent Client Hints specification](https://wicg.github.io/ua-client-hints/#sec-ch-ua-platform). Note that some (but not all) of these values can overlap with values in the [`os.type` and `os.name` attributes](./os.md). However, for consistency, the values in the `browser.platform` attribute should capture the exact value that the user agent provides.
"""

BROWSER_WEB_VITAL_DELTA: Final = "browser.web_vital.delta"
"""
The delta between the current value and the last-reported value. See [delta](https://github.com/GoogleChrome/web-vitals?tab=readme-ov-file#report-only-the-delta-of-changes).
"""

BROWSER_WEB_VITAL_ID: Final = "browser.web_vital.id"
"""
A unique ID representing this particular metric instance.
"""

BROWSER_WEB_VITAL_NAME: Final = "browser.web_vital.name"
"""
Name of the web vital.
"""

BROWSER_WEB_VITAL_NAVIGATION_TYPE: Final = "browser.web_vital.navigation_type"
"""
The type of navigation, as reported by the [Navigation Timing API](https://developer.mozilla.org/docs/Web/API/PerformanceNavigationTiming/type), with additional values reported by the web-vitals library.
"""

BROWSER_WEB_VITAL_RATING: Final = "browser.web_vital.rating"
"""
The rating of the web vital value against the "good", "needs improvement", and "poor" thresholds defined for the metric.
"""

BROWSER_WEB_VITAL_VALUE: Final = "browser.web_vital.value"
"""
Value of the web vital.
"""


class BrowserWebVitalNameValues(Enum):
    CLS = "cls"
    """Cumulative Layout Shift. See [cls](https://web.dev/articles/cls)."""
    LCP = "lcp"
    """Largest Contentful Paint. See [lcp](https://web.dev/articles/lcp)."""
    FCP = "fcp"
    """First Contentful Paint. See [fcp](https://web.dev/articles/fcp)."""
    INP = "inp"
    """Interaction to Next Paint. See [inp](https://web.dev/articles/inp)."""
    TTFB = "ttfb"
    """Time to First Byte. See [ttfb](https://web.dev/articles/ttfb)."""
    FID = "fid"
    """Deprecated: Replaced by Interaction to Next Paint (`inp`), which became a Core Web Vital in March 2024. See [inp](https://web.dev/articles/inp)."""


class BrowserWebVitalNavigationTypeValues(Enum):
    NAVIGATE = "navigate"
    """Navigation started by clicking a link, entering a URL, form submission, or a script operation."""
    RELOAD = "reload"
    """Navigation through a reload operation or a `Location.reload()` call."""
    BACK_FORWARD = "back-forward"
    """Navigation through the browser's history traversal (e.g. back/forward buttons)."""
    BACK_FORWARD_CACHE = "back-forward-cache"
    """Navigation restoring a page from the back/forward cache (bfcache)."""
    PRERENDER = "prerender"
    """Navigation to a page that was prerendered."""
    RESTORE = "restore"
    """Navigation restoring a page that was previously discarded by the browser."""


class BrowserWebVitalRatingValues(Enum):
    GOOD = "good"
    """The metric value is within the "good" threshold."""
    NEEDS_IMPROVEMENT = "needs-improvement"
    """The metric value is within the "needs improvement" threshold."""
    POOR = "poor"
    """The metric value is within the "poor" threshold."""
