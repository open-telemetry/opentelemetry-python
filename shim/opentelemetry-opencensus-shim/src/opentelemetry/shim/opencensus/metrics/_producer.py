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


from abc import ABC, abstractmethod
from opencensus.stats import stats as stats_module


class MetricProducer(ABC):
    
    @abstractmethod
    def produce(self, oc_metrics):
        pass


class OpenCensusMetricProducer(MetricProducer):
    
    def produce(self, oc_metrics):
     """Convert OC metrics to OT metrics"""
     pass

class Foo(MetricProducer):
   def produce (self, oc_metrics):
      pass
   
   def Foobar(self):
      print ("Hi there")
 


