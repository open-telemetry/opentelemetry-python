# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

OPENAI_API_TYPE: Final = "openai.api.type"
"""
The type of OpenAI API being used.
"""

OPENAI_REQUEST_SERVICE_TIER: Final = "openai.request.service_tier"
"""
The service tier requested. May be a specific tier, default, or auto.
"""

OPENAI_RESPONSE_SERVICE_TIER: Final = "openai.response.service_tier"
"""
The service tier used for the response.
"""

OPENAI_RESPONSE_SYSTEM_FINGERPRINT: Final = (
    "openai.response.system_fingerprint"
)
"""
A fingerprint to track any eventual change in the Generative AI environment.
"""


class OpenaiApiTypeValues(Enum):
    CHAT_COMPLETIONS = "chat_completions"
    """The OpenAI [Chat Completions API](https://developers.openai.com/api/reference/chat-completions/overview)."""
    RESPONSES = "responses"
    """The OpenAI [Responses API](https://developers.openai.com/api/reference/responses/overview)."""


class OpenaiRequestServiceTierValues(Enum):
    AUTO = "auto"
    """The system will utilize scale tier credits until they are exhausted."""
    DEFAULT = "default"
    """The system will utilize the default scale tier."""
