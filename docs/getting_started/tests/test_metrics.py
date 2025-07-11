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

import json
import os
import subprocess
import sys
import unittest

class TestMetrics(unittest.TestCase):
    def test_metrics(self):
        """Test that metrics example produces expected values"""
        # Run the metrics example
        dirpath = os.path.dirname(os.path.realpath(__file__))
        test_script = f"{dirpath}/../metrics_example.py"
        
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Script should run successfully
        self.assertEqual(result.returncode, 0)
        
        # Parse the JSON output
        output_data = json.loads(result.stdout)
        
        # Get the metrics from the JSON structure
        metrics = output_data["resource_metrics"][0]["scope_metrics"][0]["metrics"]
        
        # Create a lookup dict for easier testing
        metrics_by_name = {metric["name"]: metric for metric in metrics}
        
        # Test Counter: should be 1 (called counter.add(1))
        counter_metric = metrics_by_name["counter"]
        counter_value = counter_metric["data"]["data_points"][0]["value"]
        self.assertEqual(counter_value, 1, "Counter should have value 1")
        
        # Test UpDownCounter: should be -4 (1 + (-5) = -4)
        updown_metric = metrics_by_name["updown_counter"]
        updown_value = updown_metric["data"]["data_points"][0]["value"]
        self.assertEqual(updown_value, -4, "UpDownCounter should have value -4")
        
        # Test Histogram: should have count=1, sum=99.9
        histogram_metric = metrics_by_name["histogram"]
        histogram_data = histogram_metric["data"]["data_points"][0]
        self.assertEqual(histogram_data["count"], 1, "Histogram should have count 1")
        self.assertEqual(histogram_data["sum"], 99.9, "Histogram should have sum 99.9")
        
        # Test Gauge: should be 1 (last value set)
        gauge_metric = metrics_by_name["gauge"]
        gauge_value = gauge_metric["data"]["data_points"][0]["value"]
        self.assertEqual(gauge_value, 1, "Gauge should have value 1")
        
        # Test Observable Counter: should be 1 (from callback)
        obs_counter_metric = metrics_by_name["observable_counter"]
        obs_counter_value = obs_counter_metric["data"]["data_points"][0]["value"]
        self.assertEqual(obs_counter_value, 1, "Observable counter should have value 1")
        
        # Test Observable UpDownCounter: should be -10 (from callback)
        obs_updown_metric = metrics_by_name["observable_updown_counter"]
        obs_updown_value = obs_updown_metric["data"]["data_points"][0]["value"]
        self.assertEqual(obs_updown_value, -10, "Observable updown counter should have value -10")
        
        # Test Observable Gauge: should be 9 (from callback)
        obs_gauge_metric = metrics_by_name["observable_gauge"]
        obs_gauge_value = obs_gauge_metric["data"]["data_points"][0]["value"]
        self.assertEqual(obs_gauge_value, 9, "Observable gauge should have value 9")
