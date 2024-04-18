# Copyright (c) 2017 Uber Technologies, Inc.
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

import math
import mock
import time
import unittest

from opentelemetry import trace
from opentelemetry.jaeger_remote_sampling import (
    AdaptiveSampler,
    GuaranteedThroughputProbabilisticSampler,
    RateLimitingSampler,
    RemoteControlledSampler,
    get_sampling_probability,
    get_rate_limit,
)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, StaticSampler

TO_DEFAULT = trace.TraceFlags(trace.TraceFlags.DEFAULT)
TO_SAMPLED = trace.TraceFlags(trace.TraceFlags.SAMPLED)

MAX_INT = 1 << 63

class TestDecision(unittest.TestCase):
    def test_adaptive_sampler(self):
        strategies = {
            'defaultSamplingProbability': 0.51,
            'defaultLowerBoundTracesPerSecond': 3,
            'perOperationStrategies':
            [
                {
                    'operation': 'op',
                    'probabilisticSampling': {
                        'samplingRate': 0.5
                    }
                }
            ]
        }
        sampler = AdaptiveSampler(strategies, 2)
        sample_result = sampler.should_sample(None, MAX_INT - 10, "op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.5})

        # This operation is seen for the first time by the sampler
        sample_result = sampler.should_sample(None, MAX_INT - 10, "new_op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.51})

        ts = time.time()
        with mock.patch('opentelemetry.jaeger_remote_sampling.rate_limiter.RateLimiter.timestamp') \
                as mock_time:

            # Move time forward by a second to guarantee the rate limiter has enough credits
            mock_time.side_effect = lambda: ts + 1

            sample_result = sampler.should_sample(None, int(MAX_INT + (MAX_INT / 4)), "new_op")
            self.assertTrue(sample_result.decision.is_sampled())
            self.assertEqual(sample_result.attributes, {'sampler.type': 'lowerbound', 'sampler.param': 0.51})

        # This operation is seen for the first time by the sampler but surpasses
        # max_operations of 2. The default probabilistic sampler will be used
        sample_result = sampler.should_sample(None, MAX_INT - 10, "new_op_2")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.51})

        sample_result = sampler.should_sample(None, int(MAX_INT + (MAX_INT / 4)), "new_op_2")
        self.assertFalse(sample_result.decision.is_sampled())
        self.assertEqual(sampler.get_description(), 'AdaptiveSampler{0.51, 3, 2}')

        # Update the strategies
        strategies = {
            'defaultSamplingProbability': 0.52,
            'defaultLowerBoundTracesPerSecond': 4,
            'perOperationStrategies':
            [
                {
                    'operation': 'op',
                    'probabilisticSampling': {
                        'samplingRate': 0.52
                    }
                },
                {
                    'operation': 'new_op_3',
                    'probabilisticSampling': {
                        'samplingRate': 0.53
                    }
                }
            ]
        }
        sampler.update(strategies)

        # The probability for op has been updated
        sample_result = sampler.should_sample(None, MAX_INT - 10, "op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.52})

        # A new operation has been added
        sample_result = sampler.should_sample(None, MAX_INT - 10, "new_op_3")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.53})
        self.assertEqual(sampler.get_description(), 'AdaptiveSampler{0.52, 4, 2}')

    def test_adaptive_sampler_default_values(self):
        adaptive_sampler = AdaptiveSampler({}, 2)
        self.assertEqual(adaptive_sampler.get_description(), \
            'AdaptiveSampler{0.001, 0.0016666666666666668, 2}', 'sampler should use default values')

        sample_result = adaptive_sampler.should_sample(None, 0, "op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.001})
        self.assertEqual(adaptive_sampler.samplers['op'].get_description(), \
            'GuaranteedThroughputProbabilisticSampler{op, 0.001, 0.0016666666666666668}')

        adaptive_sampler.update(strategies={
            'defaultLowerBoundTracesPerSecond': 4,
            'perOperationStrategies':
                [
                    {
                        'operation': 'new_op',
                        'probabilisticSampling': {
                            'samplingRate': 0.002
                        }
                    }
                ]
        })
        self.assertEqual(adaptive_sampler.get_description(), 'AdaptiveSampler{0.001, 4, 2}')

        sample_result = adaptive_sampler.should_sample(None, 0, "new_op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.002})
        self.assertEqual(adaptive_sampler.samplers['new_op'].get_description(), \
            'GuaranteedThroughputProbabilisticSampler{new_op, 0.002, 4}')

        sample_result = adaptive_sampler.should_sample(None, 0, "op")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.001})
        # TODO ruh roh, the lowerbound isn't changed
        #  if the operation isn't included in perOperationStrategies
        self.assertEqual(adaptive_sampler.samplers['op'].get_description(), \
            'GuaranteedThroughputProbabilisticSampler{op, 0.001, 0.0016666666666666668}')

    def test_rate_limiting_sampler(self):
        sampler = RateLimitingSampler(2)
        sampler.rate_limiter.balance = 2.0
        # stop time by overwriting timestamp() function to always return
        # the same time
        ts = time.time()
        sampler.rate_limiter.last_tick = ts
        with mock.patch('opentelemetry.jaeger_remote_sampling.rate_limiter.RateLimiter.timestamp') \
                as mock_time:
            mock_time.side_effect = lambda: ts  # always return same time

            self.assertEqual(sampler.rate_limiter.timestamp(), ts)
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'initial balance allows first item')
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'initial balance allows second item')
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertFalse(sampled, 'initial balance exhausted')

            # move time 250ms forward, not enough credits to pay for one sample
            mock_time.side_effect = lambda: ts + 0.25
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertFalse(sampled, 'not enough time passed for full item')

            # move time 500ms forward, now enough credits to pay for one sample
            mock_time.side_effect = lambda: ts + 0.5
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'enough time for new item')
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertFalse(sampled, 'no more balance')

            # move time 5s forward, enough to accumulate credits for 10 samples,
            # but it should still be capped at 2
            sampler.last_tick = ts  # reset the timer
            mock_time.side_effect = lambda: ts + 5
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'enough time for new item')
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'enough time for second new item')
            for i in range(0, 8):
                sample_result = sampler.should_sample(None, 0, "span name")
                self.assertFalse(sample_result.decision.is_sampled(), 'but no further, since time is stopped')
                self.assertEqual(sample_result.attributes, {'sampler.type': 'ratelimiting', 'sampler.param': 2})
        self.assertEqual(sampler.get_description(), 'RateLimitingSampler{2}')

        # Test with rate limit of greater than 1 second
        sampler = RateLimitingSampler(0.1)
        sampler.rate_limiter.balance = 1.0
        ts = time.time()
        sampler.rate_limiter.last_tick = ts
        with mock.patch('opentelemetry.jaeger_remote_sampling.rate_limiter.RateLimiter.timestamp') \
                as mock_time:
            mock_time.side_effect = lambda: ts  # always return same time
            self.assertEqual(sampler.rate_limiter.timestamp(), ts)
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled, 'initial balance allows first item')
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertFalse(sampled, 'initial balance exhausted')

            # move time 11s forward, enough credits to pay for one sample
            mock_time.side_effect = lambda: ts + 11
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled)
        self.assertEqual(sampler.get_description(), 'RateLimitingSampler{0.1}')

        # Test update
        sampler = RateLimitingSampler(3.0)
        sampler.rate_limiter.balance = 3.0
        ts = time.time()
        sampler.rate_limiter.last_tick = ts
        with mock.patch('opentelemetry.jaeger_remote_sampling.rate_limiter.RateLimiter.timestamp') \
                as mock_time:
            mock_time.side_effect = lambda: ts  # always return same time
            self.assertEqual(sampler.rate_limiter.timestamp(), ts)
            sampled = sampler.should_sample(None, 0, "span name").decision.is_sampled()
            self.assertTrue(sampled)
            self.assertEqual(sampler.rate_limiter.balance, 2.0)
            self.assertEqual(sampler.get_description(), 'RateLimitingSampler{3.0}')

            sampler.update(3.0)
            self.assertEqual(sampler.get_description(), \
                'RateLimitingSampler{3.0}', 'should short cirtcuit if rate is the same')

            sampler.update(2.0)
            self.assertEqual(sampler.rate_limiter.balance, 4.0 / 3.0)
            self.assertEqual(sampler.get_description(), 'RateLimitingSampler{2.0}')

    def test_guaranteed_throughput_probabilistic_sampler(self):
        sampler = GuaranteedThroughputProbabilisticSampler('op', 2, 0.5)
        sampler.lower_bound_sampler.rate_limiter.balance = 2.0
        sample_result = sampler.should_sample(None, MAX_INT - 10, "span name")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.5})
        sample_result = sampler.should_sample(None, MAX_INT + 10, "span name")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'lowerbound', 'sampler.param': 0.5})
        sample_result = sampler.should_sample(None, MAX_INT + 10, "span name")
        self.assertFalse(sample_result.decision.is_sampled())
        self.assertEqual(sampler.get_description(), 'GuaranteedThroughputProbabilisticSampler{op, 0.5, 2}')

        sampler.update(3, 0.51)
        sampler.lower_bound_sampler.rate_limiter.balance = 3.0
        sample_result = sampler.should_sample(None, MAX_INT - 10, "span name")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': 0.51})
        sample_result = sampler.should_sample(None, int(MAX_INT + (MAX_INT / 4)), "span name")
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {'sampler.type': 'lowerbound', 'sampler.param': 0.51})

        self.assertEqual(sampler.get_description(), 'GuaranteedThroughputProbabilisticSampler{op, 0.51, 3}')

    def test_sampler_equality(self):
        const1 = StaticSampler(True)
        const2 = StaticSampler(True)
        const3 = StaticSampler(False)
        self.assertEqual(const1, const2)
        self.assertNotEqual(const1, const3)

        prob1 = TraceIdRatioBased(rate=0.01)
        prob2 = TraceIdRatioBased(rate=0.01)
        prob3 = TraceIdRatioBased(rate=0.02)
        self.assertEqual(prob1, prob2)
        self.assertNotEqual(prob1, prob3)
        self.assertNotEqual(const1, prob1)

        rate1 = RateLimitingSampler(max_traces_per_second=0.01)
        rate2 = RateLimitingSampler(max_traces_per_second=0.01)
        rate3 = RateLimitingSampler(max_traces_per_second=0.02)
        self.assertEqual(rate1, rate2)
        self.assertNotEqual(rate1, rate3)
        self.assertNotEqual(rate1, const1)
        self.assertNotEqual(rate1, prob1)

    def test_remotely_controlled_sampler(self):
        sampler = RemoteControlledSampler(
            channel=mock.MagicMock(),
            service_name='x'
        )
        sample_result = sampler.should_sample(None, 1, "span name")
        self.assertTrue(sample_result.decision.is_sampled())

        # TODO: don't want to mess with TraceIdRatioBased attributes - what do we do about this assertion?
        # self.assertEqual(sample_result.attributes, {'sampler.type': 'traceidratio', 'sampler.param': sampling.DEFAULT_SAMPLING_PROBABILITY}

        init_sampler = mock.MagicMock()
        init_sampler.should_sample = mock.MagicMock()
        channel = mock.MagicMock()
        channel.io_loop = None
        sampler = RemoteControlledSampler(
            channel=channel,
            service_name='x',
            init_sampler=init_sampler,
            logger=mock.MagicMock(),
        )
        self.assertEqual(init_sampler.should_sample.call_count, 1)

        sampler.should_sample(None, 1, "span name")
        self.assertEqual(init_sampler.should_sample.call_count, 2)

        sampler.io_loop = mock.MagicMock()
        # noinspection PyProtectedMember
        sampler._init_polling()
        self.assertEqual(sampler.io_loop.call_later.call_count, 1)

        sampler._create_periodic_callback = mock.MagicMock()
        # noinspection PyProtectedMember
        sampler._delayed_polling()
        sampler.close()

        sampler = RemoteControlledSampler(
            channel=mock.MagicMock(),
            service_name='x',
        )

        sampler.close()
        self.assertFalse(sampler.running)
        sampler._init_polling()
        self.assertFalse(sampler.running)
        sampler._delayed_polling()
        self.assertFalse(sampler.running)

    # noinspection PyProtectedMember
    def test_sampling_request_callback(self):
        channel = mock.MagicMock()
        channel.io_loop = mock.MagicMock()
        error_reporter = mock.MagicMock()
        error_reporter.error = mock.MagicMock()
        sampler = RemoteControlledSampler(
            channel=channel,
            service_name='x',
            error_reporter=error_reporter,
            max_operations=10,
        )

        return_value = mock.MagicMock()
        return_value.exception = lambda *args: False

        probabilistic_strategy = """
        {
            "strategyType":"PROBABILISTIC",
            "probabilisticSampling":
            {
                "samplingRate":0.002
            }
        }
        """

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': probabilistic_strategy})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(sampler.sampler.get_description(), \
            'TraceIdRatioBased{0.002}', 'sampler should have changed to probabilistic')
        prev_sampler = sampler.sampler

        sampler._sampling_request_callback(return_value)
        self.assertTrue(prev_sampler is sampler.sampler, \
            "strategy hasn't changed so sampler should not change")

        adaptive_sampling_strategy = """
        {
            "strategyType":"PROBABILISTIC",
            "operationSampling":
            {
                "defaultSamplingProbability":0.001,
                "defaultLowerBoundTracesPerSecond":2,
                "perOperationStrategies":
                [
                    {
                        "operation":"op",
                        "probabilisticSampling":{
                            "samplingRate":0.002
                        }
                    }
                ]
            }
        }
        """
        return_value.result = lambda *args: \
            type('obj', (object,), {'body': adaptive_sampling_strategy})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(sampler.sampler.get_description(), 'AdaptiveSampler{0.001, 2, 10}', \
            'sampler should have changed to adaptive')
        prev_sampler = sampler.sampler

        sampler._sampling_request_callback(return_value)
        self.assertTrue(prev_sampler is sampler.sampler, "strategy hasn't changed so sampler should not change")

        probabilistic_strategy_bytes = probabilistic_strategy.encode('utf-8')

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': probabilistic_strategy_bytes})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(sampler.sampler.get_description(), \
            'TraceIdRatioBased{0.002}', 'sampler should have changed to probabilistic')

        adaptive_sampling_strategy_bytearray = bytearray(adaptive_sampling_strategy.encode('utf-8'))

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': adaptive_sampling_strategy_bytearray})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(sampler.sampler.get_description(), 'AdaptiveSampler{0.001, 2, 10}', \
            'sampler should have changed to adaptive')
        prev_sampler = sampler.sampler

        return_value.exception = lambda *args: True
        sampler._sampling_request_callback(return_value)
        self.assertEqual(error_reporter.error.call_count, 1)
        self.assertTrue(prev_sampler is sampler.sampler, 'error fetching strategy should not update the sampler')

        return_value.exception = lambda *args: False
        return_value.result = lambda *args: type('obj', (object,), {'body': 'bad_json'})()

        sampler._sampling_request_callback(return_value)
        self.assertEqual(error_reporter.error.call_count, 2)
        self.assertTrue(prev_sampler is sampler.sampler, 'error updating sampler should not update the sampler')

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': None})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(error_reporter.error.call_count, 3)
        self.assertTrue(prev_sampler is sampler.sampler, 'error updating sampler should not update the sampler')

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': {'decode': None}})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(error_reporter.error.call_count, 4)
        self.assertTrue(prev_sampler is sampler.sampler, 'error updating sampler should not update the sampler')

        return_value.result = lambda *args: \
            type('obj', (object,), {'body': probabilistic_strategy})()
        sampler._sampling_request_callback(return_value)
        self.assertEqual(sampler.sampler.get_description(), 'TraceIdRatioBased{0.002}', \
            'updating sampler from adaptive to probabilistic should work')

        sampler.close()

    def test_update_sampler(self):
        probabilistic_sampler = TraceIdRatioBased(0.002)
        other_probabilistic_sampler = TraceIdRatioBased(0.003)
        rate_limiting_sampler = RateLimitingSampler(10)
        other_rate_limiting_sampler = RateLimitingSampler(20)

        cases =    [
            (
                {'strategyType': 'PROBABILISTIC', 'probabilisticSampling': {'samplingRate': 0.003}},
                probabilistic_sampler,
                other_probabilistic_sampler,
                0,
                'sampler should update to new probabilistic sampler',
                False,
                10,
            ),
            (
                {'strategyType': 'PROBABILISTIC', 'probabilisticSampling': {'samplingRate': 400}},
                probabilistic_sampler,
                probabilistic_sampler,
                1,
                'sampler should remain the same if strategy is invalid',
                True,
                10,
            ),
            (
                {'strategyType': 'PROBABILISTIC', 'probabilisticSampling': {'samplingRate': 0.002}},
                probabilistic_sampler,
                probabilistic_sampler,
                0,
                'sampler should remain the same with the same strategy',
                True,
                10,
            ),
            (
                {'strategyType': 'RATE_LIMITING', 'rateLimitingSampling': {'maxTracesPerSecond': 10}},
                probabilistic_sampler,
                rate_limiting_sampler,
                0,
                'sampler should update to new rate limiting sampler',
                False,
                10,
            ),
            (
                {'strategyType': 'RATE_LIMITING', 'rateLimitingSampling': {'maxTracesPerSecond': 10}},
                rate_limiting_sampler,
                rate_limiting_sampler,
                0,
                'sampler should remain the same with the same strategy',
                True,
                10,
            ),
            (
                {'strategyType': 'RATE_LIMITING', 'rateLimitingSampling': {'maxTracesPerSecond': -10}},
                rate_limiting_sampler,
                rate_limiting_sampler,
                1,
                'sampler should remain the same if strategy is invalid',
                True,
                10,
            ),
            (
                {'strategyType': 'RATE_LIMITING', 'rateLimitingSampling': {'maxTracesPerSecond': 20}},
                rate_limiting_sampler,
                other_rate_limiting_sampler,
                0,
                'sampler should update to new rate limiting sampler',
                False,
                10,
            ),
            (
                {},
                rate_limiting_sampler,
                rate_limiting_sampler,
                1,
                'sampler should remain the same if strategy is empty',
                True,
                10,
            ),
            (
                {'strategyType': 'INVALID_TYPE'},
                rate_limiting_sampler,
                rate_limiting_sampler,
                1,
                'sampler should remain the same if strategy is invalid',
                True,
                10,
            ),
            (
                {'strategyType': 'INVALID_TYPE'},
                rate_limiting_sampler,
                rate_limiting_sampler,
                1,
                'sampler should remain the same if strategy is invalid',
                True,
                None,
            ),
        ]

        for response, init_sampler, expected_sampler, err_count, err_msg, reference_equivalence, max_operations in cases:
            error_reporter = mock.MagicMock()
            error_reporter.error = mock.MagicMock()
            remote_sampler = RemoteControlledSampler(
                channel=mock.MagicMock(),
                service_name='x',
                error_reporter=error_reporter,
                max_operations=max_operations,
                init_sampler=init_sampler,
            )

            # noinspection PyProtectedMember
            remote_sampler._update_sampler(response)
            self.assertEqual(error_reporter.error.call_count, err_count)
            if reference_equivalence:
                self.assertTrue(remote_sampler.sampler is expected_sampler, err_msg)
            else:
                self.assertEqual(remote_sampler.sampler, expected_sampler, err_msg)

            remote_sampler.close()

    # noinspection PyProtectedMember
    def test_update_sampler_adaptive_sampler(self):
        error_reporter = mock.MagicMock()
        error_reporter.error = mock.MagicMock()
        remote_sampler = RemoteControlledSampler(
            channel=mock.MagicMock(),
            service_name='x',
            error_reporter=error_reporter,
            max_operations=10,
        )

        response = {
            'strategyType': 'RATE_LIMITING',
            'operationSampling':
            {
                'defaultSamplingProbability': 0.001,
                'defaultLowerBoundTracesPerSecond': 2,
                'perOperationStrategies':
                [
                    {
                        'operation': 'op',
                        'probabilisticSampling': {
                            'samplingRate': 0.002
                        }
                    }
                ]
            }
        }

        remote_sampler._update_sampler(response)
        self.assertEqual(remote_sampler.sampler.get_description(), 'AdaptiveSampler{0.001, 2, 10}')

        new_response = {
            'strategyType': 'RATE_LIMITING',
            'operationSampling':
            {
                'defaultSamplingProbability': 0.51,
                'defaultLowerBoundTracesPerSecond': 3,
                'perOperationStrategies':
                [
                    {
                        'operation': 'op',
                        'probabilisticSampling': {
                            'samplingRate': 0.002
                        }
                    }
                ]
            }
        }

        remote_sampler._update_sampler(new_response)
        self.assertEqual(remote_sampler.sampler.get_description(), 'AdaptiveSampler{0.51, 3, 10}')

        remote_sampler._update_sampler(
            {'strategyType': 'PROBABILISTIC', 'probabilisticSampling': {'samplingRate': 0.004}})
        self.assertEqual(remote_sampler.sampler.get_description(), 'TraceIdRatioBased{0.004}', \
            'should not fail going from adaptive sampler to probabilistic sampler')

        remote_sampler._update_sampler({'strategyType': 'RATE_LIMITING',
                                        'operationSampling': {'defaultSamplingProbability': 0.4}})
        self.assertEqual(remote_sampler.sampler.get_description(), 'AdaptiveSampler{0.4, 0.0016666666666666668, 10}')

        remote_sampler.close()

    def test_get_sampling_probability(self):
        cases = [
            ({'probabilisticSampling': {'samplingRate': 0.003}}, 0.003),
            ({}, 0.001),
            (None, 0.001),
            ({'probabilisticSampling': {}}, 0.001),
            ({'probabilisticSampling': None}, 0.001),
        ]

        for strategy, expected in cases:
            self.assertEqual(expected, get_sampling_probability(strategy))

    def test_get_rate_limit(self):
        cases = [
            ({'rateLimitingSampling': {'maxTracesPerSecond': 1}}, 1),
            ({}, 0.0016666),
            (None, 0.0016666),
            ({'rateLimitingSampling': {}}, 0.0016666),
            ({'rateLimitingSampling': None}, 0.0016666),
        ]

        for strategy, expected in cases:
            self.assertTrue(math.fabs(expected - get_rate_limit(strategy)) < 0.0001)
