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

import abc
import dataclasses
import json
from typing import List, Mapping, Optional


@dataclasses.dataclass
class Request:
    request: dict
    headers: dict

    def get_header(self, name):
        return self.headers.get(name)

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        return {
            "request": self.request,
            "headers": self.headers,
        }


class Telemetry:
    def __init__(
        self,
        log_reqs: Optional[List[Request]] = None,
        metric_reqs: Optional[List[Request]] = None,
        trace_reqs: Optional[List[Request]] = None,
    ):
        self.log_reqs: List[Request] = log_reqs or []
        self.metric_reqs: List[Request] = metric_reqs or []
        self.trace_reqs: List[Request] = trace_reqs or []

    def add_log(self, log: dict, headers: dict):
        self.log_reqs.append(Request(log, headers))

    def add_metric(self, metric: dict, headers: dict):
        self.metric_reqs.append(Request(metric, headers))

    def add_trace(self, trace: dict, headers: dict):
        self.trace_reqs.append(Request(trace, headers))

    def get_trace_requests(self) -> List[Request]:
        return self.trace_reqs

    def num_metrics(self) -> int:
        out = 0
        for req in self.metric_reqs:
            for rm in req.request["resourceMetrics"]:
                for sm in rm["scopeMetrics"]:
                    out += len(sm["metrics"])
        return out

    def metric_names(self) -> set:
        out = set()
        for req in self.metric_reqs:
            for rm in req.request["resourceMetrics"]:
                for sm in rm["scopeMetrics"]:
                    for m in sm["metrics"]:
                        out.add(m["name"])
        return out

    def num_spans(self) -> int:
        out = 0
        for req in self.trace_reqs:
            for rs in req.request["resourceSpans"]:
                for ss in rs["scopeSpans"]:
                    out += len(ss["spans"])
        return out

    def has_trace_header(self, key, expected) -> bool:
        for req in self.trace_reqs:
            actual = req.get_header(key)
            if expected == actual:
                return True
        return False

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self):
        return {
            "log_reqs": [req.to_dict() for req in self.log_reqs],
            "metric_reqs": [req.to_dict() for req in self.metric_reqs],
            "trace_reqs": [req.to_dict() for req in self.trace_reqs],
        }

    def __str__(self):
        return self.to_json()


def trace_attribute_as_str_array(tr: dict, attr_name) -> [str]:
    out = []
    for rs in tr["resourceSpans"]:
        for attr in rs["resource"]["attributes"]:
            if attr["key"] == attr_name:
                out.append(attr["value"]["stringValue"])
    return out


class OtelTest(abc.ABC):
    @abc.abstractmethod
    def environment_variables(self) -> Mapping[str, str]:
        pass

    @abc.abstractmethod
    def requirements(self) -> List[str]:
        pass

    @abc.abstractmethod
    def wrapper_script(self) -> str:
        pass

    @abc.abstractmethod
    def validate(self, telemetry: Telemetry) -> None:
        pass
