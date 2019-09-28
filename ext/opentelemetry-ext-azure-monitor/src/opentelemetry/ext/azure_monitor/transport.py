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

import json
import logging
import requests

logger = logging.getLogger(__name__)


class TransportMixin(object):

    def _transmit(self, envelopes):
        try:
            response = requests.post(
                url=self.options.endpoint,
                data=json.dumps(envelopes),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=self.options.timeout,
            )
        except requests.RequestException as ex:
            logger.warning("Transient client side error %s.", ex)
            return self.export_result_type.FAILED_RETRYABLE

        text = "N/A"
        data = None  # noqa pylint: disable=unused-variable
        try:
            text = response.text
        except Exception as ex:  # noqa pylint: disable=broad-except
            logger.warning("Error while reading response body %s.", ex)
        else:
            try:
                data = json.loads(text)  # noqa pylint: disable=unused-variable
            except Exception:  # noqa pylint: disable=broad-except
                pass

        if response.status_code == 200:
            logger.info("Transmission succeeded: %s.", text)
            return self.export_result_type.SUCCESS

        if response.status_code in (
            206,  # Partial Content
            429,  # Too Many Requests
            500,  # Internal Server Error
            503,  # Service Unavailable
        ):
            return self.export_result_type.FAILED_RETRYABLE

        return self.export_result_type.FAILED_NOT_RETRYABLE
