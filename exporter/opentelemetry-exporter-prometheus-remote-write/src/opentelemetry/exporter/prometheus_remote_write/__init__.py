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


from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)

from opentelemetry.sdk.metrics.export.aggregate import (
    ValueObserverAggregator,
    LastValueAggregator,
    HistogramAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
)

class PrometheusRemoteWriteMetricsExporter(MetricsExporter):
    """
    Prometheus remote write metric exporter for OpenTelemetry.

    Args:
        config: configuration object containing all necessary information to make remote write requests
    """

    def __init__(self, prefix: str = ""):
        pass

    def export(self, metric_records: Sequence[MetricRecord]) -> MetricsExportResult:
        pass

    def shutdown(self) -> None:
        pass
    
    def convert_to_timeseries(self, metric_records: Sequence[MetricRecord]) -> Sequence[TimeSeriesData]:
        pass
    
    def convert_from_sum(self, sum_record: MetricRecord) -> TimeSeriesData:
        pass

    def convert_from_min_max_sum_count(self, min_max_sum_count_record: MetricRecord) -> TimeSeriesData:
        pass

    def convert_from_histogram(self, histogram_record: MetricRecord) -> TimeSeriesData:
        pass

    def convert_from_last_value(self, last_value_record: MetricRecord) -> TimeSeriesData:
        pass

    def convert_from_value_observer(self, value_observer_record: MetricRecord) -> TimeSeriesData:
        pass

    def convert_from_summary(self, summary_record: MetricRecord) -> TimeSeriesData:
        pass

    def build_message(self) -> String:
        pass

    def get_headers(self) -> dict:
        pass

    def send_message(self, message: String) -> bool:
        pass

    def build_client(self) -> HTTPConnection:
        pass

    def build_tls_config(self) -> TLSConfig:
        pass

    def sanitize_label(self, label: String) -> String:
        pass


class Config():
    """
    Configuration containing all necessary information to make remote write requests
    
    Args:
        config_dict: dictionary containing all config properties
    """

    def __init__(self):
        pass

    def validate(self):
        pass


class TLSConfig():
    """
    Configuration containing all necessary information to add TLS to HTTPConnection
    
    Args:
        ca_file: dictionary containing all config properties
    """

    def __init__(self):
        pass

    def validate(self):
        pass

class TimeSeriesData:
    def __init__(self, labels, samples):
        self.labels = labels
        self.samples = samples

    def __eq__(self, other) -> bool:
        if len(self.labels) != len(other.labels) or len(self.samples) != len(other.samples):
            return False
        for i in range(len(labels)):
            if self.labels[i] != other.labels[i]:
                return False

        for i in range(len(samples)):
            if self.samples[i] != other.samples[i]:
                return False
        return True

def parse_config(filepath: String) -> Config:
    pass