# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.configuration._tracer_provider import (
    configure_tracer_provider,
    create_tracer_provider,
)
from opentelemetry.configuration.file._loader import ConfigurationError
from opentelemetry.configuration.models import (
    AttributeNameValue,
)
from opentelemetry.configuration.models import (
    BatchSpanProcessor as BatchSpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableProbabilitySampler as ComposableProbabilityConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableRuleBasedSampler as RuleBasedSamplerConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableRuleBasedSamplerRule as RuleBasedSamplerRuleConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableRuleBasedSamplerRuleAttributePatterns as RuleAttributePatternsConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableRuleBasedSamplerRuleAttributeValues as RuleAttributeValuesConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableSampler as ComposableSamplerConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalOtlpFileExporter as ExperimentalOtlpFileExporterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalRuleBasedTraceContinuationDecider as RuleBasedTraceContinuationDeciderConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalRuleBasedTraceContinuationDeciderAttributePatterns as TraceContinuationAttributePatternsConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalRuleBasedTraceContinuationDeciderAttributeValues as TraceContinuationAttributeValuesConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalRuleBasedTraceContinuationDeciderConditions as TraceContinuationConditionsConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalRuleBasedTraceContinuationDeciderRule as TraceContinuationRuleConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalSpanParent as SpanParentConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTraceContinuationDecider as TraceContinuationDeciderConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTraceContinuationDirection as TraceContinuationDirectionConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTraceContinuationEgressAction as TraceContinuationEgressActionConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTraceContinuationStrategy as TraceContinuationStrategyConfig,
)
from opentelemetry.configuration.models import (
    IdGenerator as IdGeneratorConfig,
)
from opentelemetry.configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.configuration.models import (
    ParentBasedSampler as ParentBasedSamplerConfig,
)
from opentelemetry.configuration.models import (
    Sampler as SamplerConfig,
)
from opentelemetry.configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.configuration.models import (
    SpanKind as SpanKindConfig,
)
from opentelemetry.configuration.models import (
    SpanLimits as SpanLimitsConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TraceIdRatioBasedSampler as TraceIdRatioBasedConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    Decision,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)
from opentelemetry.sdk.trace.trace_continuation import (
    ALWAYS_CONTINUE,
    ALWAYS_RESTART_WITH_LINK,
    ALWAYS_RESTART_WITHOUT_LINK,
    EgressAction,
)
from opentelemetry.trace import SpanContext, TraceFlags
from opentelemetry.trace import SpanKind as TraceSpanKind

TRACE_ID = int("00112233445566778800000000000000", 16)
SPAN_ID = int("0123456789abcdef", 16)


class TestCreateTracerProviderBasic(unittest.TestCase):
    def test_none_config_returns_provider(self):
        resource = Resource({"service.name": "test"})
        provider = create_tracer_provider(None, resource)
        self.assertIsInstance(provider, TracerProvider)

    def test_none_config_uses_supplied_resource(self):
        resource = Resource({"service.name": "svc"})
        provider = create_tracer_provider(None, resource)
        self.assertIs(provider._resource, resource)

    def test_none_config_uses_default_sampler(self):
        provider = create_tracer_provider(None)
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_none_config_no_processors(self):
        provider = create_tracer_provider(None)
        self.assertEqual(
            len(provider._active_span_processor._span_processors), 0
        )

    def test_none_config_does_not_read_sampler_env_var(self):
        with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "always_off"}):
            provider = create_tracer_provider(None)
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_none_config_does_not_read_span_limit_env_var(self):
        with patch.dict(os.environ, {"OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "1"}):
            provider = create_tracer_provider(None)
        self.assertEqual(provider._span_limits.max_span_attributes, 128)

    def test_configure_none_does_not_set_global(self):
        original = __import__(
            "opentelemetry.trace", fromlist=["get_tracer_provider"]
        ).get_tracer_provider()
        configure_tracer_provider(None)
        after = __import__(
            "opentelemetry.trace", fromlist=["get_tracer_provider"]
        ).get_tracer_provider()
        self.assertIs(original, after)

    def test_configure_with_config_sets_global(self):
        config = TracerProviderConfig(processors=[])
        with patch(
            "opentelemetry.configuration._tracer_provider.trace.set_tracer_provider"
        ) as mock_set:
            configure_tracer_provider(config)
            mock_set.assert_called_once()
            arg = mock_set.call_args[0][0]
            self.assertIsInstance(arg, TracerProvider)

    def test_processors_added_in_order(self):
        mock_proc_a = MagicMock()
        mock_proc_b = MagicMock()
        config = TracerProviderConfig(processors=[])
        provider = create_tracer_provider(config)
        provider.add_span_processor(mock_proc_a)
        provider.add_span_processor(mock_proc_b)
        procs = provider._active_span_processor._span_processors
        self.assertIs(procs[0], mock_proc_a)
        self.assertIs(procs[1], mock_proc_b)

    def test_span_limits_from_config(self):
        config = TracerProviderConfig(
            processors=[],
            limits=SpanLimitsConfig(
                attribute_count_limit=5,
                event_count_limit=10,
                link_count_limit=3,
            ),
        )
        provider = create_tracer_provider(config)
        self.assertEqual(provider._span_limits.max_span_attributes, 5)
        self.assertEqual(provider._span_limits.max_events, 10)
        self.assertEqual(provider._span_limits.max_links, 3)


class TestCreateSampler(unittest.TestCase):
    @staticmethod
    def _make_provider(sampler_config):
        return create_tracer_provider(
            TracerProviderConfig(processors=[], sampler=sampler_config)
        )

    def test_always_on(self):
        provider = self._make_provider(SamplerConfig(always_on={}))
        self.assertIs(provider.sampler, ALWAYS_ON)

    def test_always_off(self):
        provider = self._make_provider(SamplerConfig(always_off={}))
        self.assertIs(provider.sampler, ALWAYS_OFF)

    def test_trace_id_ratio_based(self):
        provider = self._make_provider(
            SamplerConfig(
                trace_id_ratio_based=TraceIdRatioBasedConfig(ratio=0.5)
            )
        )
        self.assertIsInstance(provider.sampler, TraceIdRatioBased)
        self.assertAlmostEqual(provider.sampler._rate, 0.5)

    def test_trace_id_ratio_based_none_ratio_defaults_to_1(self):
        provider = self._make_provider(
            SamplerConfig(trace_id_ratio_based=TraceIdRatioBasedConfig())
        )
        self.assertIsInstance(provider.sampler, TraceIdRatioBased)
        self.assertAlmostEqual(provider.sampler._rate, 1.0)

    def test_parent_based_with_root(self):
        provider = self._make_provider(
            SamplerConfig(
                parent_based=ParentBasedSamplerConfig(
                    root=SamplerConfig(always_on={})
                )
            )
        )
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_parent_based_no_root_defaults_to_always_on(self):
        provider = self._make_provider(
            SamplerConfig(parent_based=ParentBasedSamplerConfig())
        )
        self.assertIsInstance(provider.sampler, ParentBased)
        self.assertIs(provider.sampler._root, ALWAYS_ON)

    def test_parent_based_with_delegate_samplers(self):
        provider = self._make_provider(
            SamplerConfig(
                parent_based=ParentBasedSamplerConfig(
                    root=SamplerConfig(always_on={}),
                    remote_parent_sampled=SamplerConfig(always_on={}),
                    remote_parent_not_sampled=SamplerConfig(always_off={}),
                    local_parent_sampled=SamplerConfig(always_on={}),
                    local_parent_not_sampled=SamplerConfig(always_off={}),
                )
            )
        )
        sampler = provider.sampler
        self.assertIsInstance(sampler, ParentBased)
        self.assertIs(sampler._remote_parent_sampled, ALWAYS_ON)
        self.assertIs(sampler._remote_parent_not_sampled, ALWAYS_OFF)
        self.assertIs(sampler._local_parent_sampled, ALWAYS_ON)
        self.assertIs(sampler._local_parent_not_sampled, ALWAYS_OFF)

    def test_no_sampler_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            self._make_provider(SamplerConfig())

    def test_user_defined_sampler_loaded_via_entry_point(self):
        mock_sampler = MagicMock(spec=Sampler)
        mock_class = MagicMock(return_value=mock_sampler)
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[MagicMock(**{"load.return_value": mock_class})],
        ):
            # pylint: disable=unexpected-keyword-arg
            provider = self._make_provider(SamplerConfig(my_custom_sampler={}))
        self.assertIs(provider.sampler, mock_sampler)

    def test_user_defined_sampler_not_found_raises_configuration_error(self):
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[],
        ):
            with self.assertRaises(ConfigurationError):
                # pylint: disable=unexpected-keyword-arg
                self._make_provider(SamplerConfig(no_such_sampler={}))


class TestCreateCompositeRuleBasedSampler(unittest.TestCase):
    @staticmethod
    def _make_provider(rule_based_config):
        return create_tracer_provider(
            TracerProviderConfig(
                processors=[],
                sampler=SamplerConfig(
                    composite_development=ComposableSamplerConfig(
                        rule_based=rule_based_config
                    )
                ),
            )
        )

    @staticmethod
    def _rule(sampler, **kwargs):
        return RuleBasedSamplerRuleConfig(sampler=sampler, **kwargs)

    @staticmethod
    def _always_on():
        return ComposableSamplerConfig(always_on={})

    @staticmethod
    def _always_off():
        return ComposableSamplerConfig(always_off={})

    @staticmethod
    def _attribute_values(key, values):
        return RuleAttributeValuesConfig(key=key, values=values)

    @staticmethod
    def _attribute_patterns(key, included=None, excluded=None):
        return RuleAttributePatternsConfig(
            key=key,
            included=included,
            excluded=excluded,
        )

    def _decision(
        self,
        rule_based_config,
        *,
        name="span",
        kind=None,
        attributes=None,
        parent_context=None,
    ):
        provider = self._make_provider(rule_based_config)
        return provider.sampler.should_sample(
            parent_context,
            TRACE_ID,
            name,
            kind,
            attributes,
            None,
        ).decision

    def test_composite_rule_based_no_rules_drops(self):
        decision = self._decision(RuleBasedSamplerConfig())

        self.assertEqual(decision, Decision.DROP)

    def test_composite_rule_based_no_condition_rule_matches(self):
        decision = self._decision(
            RuleBasedSamplerConfig(rules=[self._rule(self._always_on())])
        )

        self.assertEqual(decision, Decision.RECORD_AND_SAMPLE)

    def test_composite_rule_based_first_match_wins(self):
        rule_based = RuleBasedSamplerConfig(
            rules=[
                self._rule(
                    self._always_off(),
                    attribute_values=self._attribute_values(
                        "http.route", ["/health"]
                    ),
                ),
                self._rule(
                    self._always_on(),
                    attribute_values=self._attribute_values(
                        "http.route", ["/health"]
                    ),
                ),
            ]
        )

        decision = self._decision(
            rule_based, attributes={"http.route": "/health"}
        )

        self.assertEqual(decision, Decision.DROP)

    def test_composite_rule_based_attribute_values_stringifies_values(self):
        decision = self._decision(
            RuleBasedSamplerConfig(
                rules=[
                    self._rule(
                        self._always_on(),
                        attribute_values=self._attribute_values(
                            "http.response.status_code", ["404"]
                        ),
                    )
                ]
            ),
            attributes={"http.response.status_code": 404},
        )

        self.assertEqual(decision, Decision.RECORD_AND_SAMPLE)

    def test_composite_rule_based_attribute_values_match_array_item(self):
        decision = self._decision(
            RuleBasedSamplerConfig(
                rules=[
                    self._rule(
                        self._always_on(),
                        attribute_values=self._attribute_values(
                            "http.request.method", ["POST"]
                        ),
                    )
                ]
            ),
            attributes={"http.request.method": ("GET", "POST")},
        )

        self.assertEqual(decision, Decision.RECORD_AND_SAMPLE)

    def test_composite_rule_based_attribute_patterns_include_exclude(self):
        rule_based = RuleBasedSamplerConfig(
            rules=[
                self._rule(
                    self._always_on(),
                    attribute_patterns=self._attribute_patterns(
                        "http.route",
                        ["/api/*"],
                        ["/api/private/*"],
                    ),
                )
            ]
        )

        included = self._decision(
            rule_based, attributes={"http.route": "/api/users"}
        )
        excluded = self._decision(
            rule_based, attributes={"http.route": "/api/private/user"}
        )
        case_mismatch = self._decision(
            rule_based, attributes={"http.route": "/API/users"}
        )

        self.assertEqual(included, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(excluded, Decision.DROP)
        self.assertEqual(case_mismatch, Decision.DROP)

    def test_composite_rule_based_span_kind(self):
        rule_based = RuleBasedSamplerConfig(
            rules=[
                self._rule(
                    self._always_on(),
                    span_kinds=[SpanKindConfig.server],
                )
            ]
        )

        server = self._decision(rule_based, kind=TraceSpanKind.SERVER)
        client = self._decision(rule_based, kind=TraceSpanKind.CLIENT)

        self.assertEqual(server, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(client, Decision.DROP)

    def test_composite_rule_based_parent(self):
        local_parent_context = trace_api.set_span_in_context(
            trace_api.NonRecordingSpan(
                SpanContext(
                    TRACE_ID,
                    SPAN_ID,
                    is_remote=False,
                    trace_flags=TraceFlags.get_default(),
                )
            )
        )
        remote_parent_context = trace_api.set_span_in_context(
            trace_api.NonRecordingSpan(
                SpanContext(
                    TRACE_ID,
                    SPAN_ID,
                    is_remote=True,
                    trace_flags=TraceFlags.get_default(),
                )
            )
        )
        rule_based = RuleBasedSamplerConfig(
            rules=[
                self._rule(
                    self._always_on(),
                    parent=[SpanParentConfig.local],
                )
            ]
        )

        local = self._decision(rule_based, parent_context=local_parent_context)
        remote = self._decision(
            rule_based, parent_context=remote_parent_context
        )
        no_parent = self._decision(rule_based)

        self.assertEqual(local, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(remote, Decision.DROP)
        self.assertEqual(no_parent, Decision.DROP)

    def test_composite_rule_based_multiple_conditions_are_anded(self):
        rule_based = RuleBasedSamplerConfig(
            rules=[
                self._rule(
                    self._always_on(),
                    attribute_values=self._attribute_values(
                        "http.route", ["/users"]
                    ),
                    span_kinds=[SpanKindConfig.server],
                )
            ]
        )

        matching = self._decision(
            rule_based,
            kind=TraceSpanKind.SERVER,
            attributes={"http.route": "/users"},
        )
        wrong_kind = self._decision(
            rule_based,
            kind=TraceSpanKind.CLIENT,
            attributes={"http.route": "/users"},
        )

        self.assertEqual(matching, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(wrong_kind, Decision.DROP)

    def test_composite_rule_based_nested_probability_sampler(self):
        provider = self._make_provider(
            RuleBasedSamplerConfig(
                rules=[
                    self._rule(
                        ComposableSamplerConfig(
                            probability=ComposableProbabilityConfig(ratio=0.0)
                        )
                    )
                ]
            )
        )

        expected = (
            "ComposableRuleBased{[(AlwaysMatch:"
            "ComposableTraceIDRatioBased{threshold=max, ratio=0.0})]}"
        )
        self.assertEqual(
            provider.sampler.get_description(),
            expected,
        )


class TestCreateSpanExporterAndProcessor(unittest.TestCase):
    # pylint: disable=no-self-use

    @staticmethod
    def _make_batch_config(exporter_config):
        return TracerProviderConfig(
            processors=[
                SpanProcessorConfig(
                    batch=BatchSpanProcessorConfig(exporter=exporter_config)
                )
            ]
        )

    @staticmethod
    def _make_simple_config(exporter_config):
        return TracerProviderConfig(
            processors=[
                SpanProcessorConfig(
                    simple=SimpleSpanProcessorConfig(exporter=exporter_config)
                )
            ]
        )

    def test_console_exporter_batch(self):
        config = self._make_batch_config(SpanExporterConfig(console={}))
        provider = create_tracer_provider(config)
        procs = provider._active_span_processor._span_processors
        self.assertEqual(len(procs), 1)
        self.assertIsInstance(procs[0], BatchSpanProcessor)
        self.assertIsInstance(procs[0].span_exporter, ConsoleSpanExporter)

    def test_console_exporter_simple(self):
        config = self._make_simple_config(SpanExporterConfig(console={}))
        provider = create_tracer_provider(config)
        procs = provider._active_span_processor._span_processors
        self.assertIsInstance(procs[0], SimpleSpanProcessor)
        self.assertIsInstance(procs[0].span_exporter, ConsoleSpanExporter)

    def test_otlp_http_missing_package_raises(self):
        config = self._make_batch_config(
            SpanExporterConfig(otlp_http=OtlpHttpExporterConfig())
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": None,
                "opentelemetry.exporter.otlp.proto.http": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn("otlp-proto-http", str(ctx.exception))

    def test_otlp_http_created_with_endpoint(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Gzip = "gzip_val"
        mock_module = MagicMock()
        mock_module.OTLPSpanExporter = mock_exporter_cls
        mock_http_module = MagicMock()
        mock_http_module.Compression = mock_compression_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_http=OtlpHttpExporterConfig(
                        endpoint="http://localhost:4318"
                    )
                )
            )
            create_tracer_provider(config)

        mock_exporter_cls.assert_called_once_with(
            endpoint="http://localhost:4318",
            headers=None,
            timeout=None,
            compression=None,
        )

    def test_otlp_http_created_with_deflate_compression(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Deflate = "deflate_val"
        mock_module = MagicMock()
        mock_module.OTLPSpanExporter = mock_exporter_cls
        mock_http_module = MagicMock()
        mock_http_module.Compression = mock_compression_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_http=OtlpHttpExporterConfig(compression="deflate")
                )
            )
            create_tracer_provider(config)

        _, kwargs = mock_exporter_cls.call_args
        self.assertEqual(kwargs["compression"], "deflate_val")

    def test_otlp_http_headers_list(self):
        mock_exporter_cls = MagicMock()
        mock_http_module = MagicMock()
        mock_module = MagicMock()
        mock_module.OTLPSpanExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_http=OtlpHttpExporterConfig(
                        headers_list="x-api-key=secret,env=prod"
                    )
                )
            )
            create_tracer_provider(config)

        _, kwargs = mock_exporter_cls.call_args
        self.assertEqual(
            kwargs["headers"], {"x-api-key": "secret", "env": "prod"}
        )

    def test_otlp_file_development_missing_package_raises(self):
        config = self._make_batch_config(
            SpanExporterConfig(
                otlp_file_development=ExperimentalOtlpFileExporterConfig()
            )
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.trace_exporter": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn(
            "opentelemetry-exporter-otlp-json-file", str(ctx.exception)
        )

    def test_otlp_file_development_default_stdout(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileSpanExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.trace_exporter": mock_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileExporterConfig()
                )
            )
            create_tracer_provider(config)

        mock_exporter_cls.assert_called_once_with()

    def test_otlp_file_development_file_uri(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileSpanExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.trace_exporter": mock_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileExporterConfig(
                        output_stream="file:///tmp/traces.jsonl"
                    )
                )
            )
            create_tracer_provider(config)

        mock_exporter_cls.assert_called_once_with("/tmp/traces.jsonl")

    def test_otlp_file_development_unsupported_output_stream_raises(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileSpanExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.trace_exporter": mock_module,
            },
        ):
            config = self._make_batch_config(
                SpanExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileExporterConfig(
                        output_stream="http://example"
                    )
                )
            )
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn("output_stream", str(ctx.exception))
        mock_exporter_cls.assert_not_called()

    def test_otlp_grpc_missing_package_raises(self):
        config = self._make_batch_config(
            SpanExporterConfig(otlp_grpc=OtlpGrpcExporterConfig())
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
                "grpc": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn("otlp-proto-grpc", str(ctx.exception))

    def test_no_processor_type_raises(self):
        config = TracerProviderConfig(processors=[SpanProcessorConfig()])
        with self.assertRaises(ConfigurationError):
            create_tracer_provider(config)

    def test_no_exporter_type_raises(self):
        config = self._make_batch_config(SpanExporterConfig())
        with self.assertRaises(ConfigurationError):
            create_tracer_provider(config)

    def test_plugin_span_exporter_loaded_via_entry_point(self):
        mock_exporter = MagicMock()
        mock_class = MagicMock(return_value=mock_exporter)
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[MagicMock(**{"load.return_value": mock_class})],
        ):
            config = self._make_batch_config(
                # pylint: disable=unexpected-keyword-arg
                SpanExporterConfig(my_custom_exporter={})
            )
            provider = create_tracer_provider(config)
        self.assertEqual(
            len(provider._active_span_processor._span_processors), 1
        )

    def test_unknown_span_exporter_raises_configuration_error(self):
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[],
        ):
            config = self._make_batch_config(
                # pylint: disable=unexpected-keyword-arg
                SpanExporterConfig(no_such_exporter={})
            )
            with self.assertRaises(ConfigurationError):
                create_tracer_provider(config)


class TestCreateSpanLimits(unittest.TestCase):
    # pylint: disable=no-self-use

    @staticmethod
    def _create_with_limits(limits_config):
        return create_tracer_provider(
            TracerProviderConfig(processors=[], limits=limits_config)
        )

    def test_explicit_attribute_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(attribute_count_limit=10)
        )
        self.assertEqual(provider._span_limits.max_span_attributes, 10)

    def test_explicit_event_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(event_count_limit=5)
        )
        self.assertEqual(provider._span_limits.max_events, 5)

    def test_explicit_link_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(link_count_limit=2)
        )
        self.assertEqual(provider._span_limits.max_links, 2)

    def test_explicit_attribute_value_length_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(attribute_value_length_limit=64)
        )
        self.assertEqual(provider._span_limits.max_attribute_length, 64)

    def test_absent_limits_use_spec_defaults(self):
        provider = self._create_with_limits(SpanLimitsConfig())
        self.assertEqual(provider._span_limits.max_span_attributes, 128)
        self.assertEqual(provider._span_limits.max_events, 128)
        self.assertEqual(provider._span_limits.max_links, 128)

    def test_absent_limits_do_not_read_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "1",
                "OTEL_SPAN_EVENT_COUNT_LIMIT": "2",
            },
        ):
            provider = self._create_with_limits(SpanLimitsConfig())
        self.assertEqual(provider._span_limits.max_span_attributes, 128)
        self.assertEqual(provider._span_limits.max_events, 128)


class TestCreateIdGenerator(unittest.TestCase):
    """Tests for _create_id_generator and id_generator wiring in create_tracer_provider."""

    @staticmethod
    def _make_provider(id_generator_config):
        return create_tracer_provider(
            TracerProviderConfig(
                processors=[], id_generator=id_generator_config
            )
        )

    def test_absent_id_generator_uses_sdk_default(self):
        """When id_generator is omitted, the SDK's default RandomIdGenerator is used."""
        provider = create_tracer_provider(TracerProviderConfig(processors=[]))
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)

    def test_builtin_random_id_generator(self):
        """Built-in 'random' id_generator resolves to RandomIdGenerator."""
        provider = self._make_provider(IdGeneratorConfig(random={}))
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)

    def test_plugin_id_generator_loaded_via_entry_point(self):
        """Unknown id_generator name is loaded from opentelemetry_id_generator entry point group."""
        mock_generator = MagicMock()
        mock_class = MagicMock(return_value=mock_generator)
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[MagicMock(**{"load.return_value": mock_class})],
        ):
            # pylint: disable=unexpected-keyword-arg
            provider = self._make_provider(
                IdGeneratorConfig(my_custom_generator={})
            )
        self.assertIs(provider.id_generator, mock_generator)

    def test_unknown_id_generator_raises_configuration_error(self):
        """Unknown id_generator name with no matching entry point raises ConfigurationError."""
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[],
        ):
            with self.assertRaises(ConfigurationError):
                # pylint: disable=unexpected-keyword-arg
                self._make_provider(IdGeneratorConfig(no_such_generator={}))

    def test_empty_id_generator_raises_configuration_error(self):
        """Empty IdGenerator config (no type specified) raises ConfigurationError."""
        with self.assertRaises(ConfigurationError):
            self._make_provider(IdGeneratorConfig())


class TestCreateTraceContinuationDecider(unittest.TestCase):
    @staticmethod
    def _make_provider(trace_continuation_decider_config):
        return create_tracer_provider(
            TracerProviderConfig(
                processors=[],
                trace_continuation_decider_development=(
                    trace_continuation_decider_config
                ),
            )
        )

    @staticmethod
    def _remote_parent_context():
        remote_parent = SpanContext(
            TRACE_ID,
            SPAN_ID,
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        return remote_parent, trace_api.set_span_in_context(
            trace_api.NonRecordingSpan(remote_parent)
        )

    @staticmethod
    def _rule(**kwargs):
        return TraceContinuationRuleConfig(**kwargs)

    @staticmethod
    def _conditions(**kwargs):
        return TraceContinuationConditionsConfig(**kwargs)

    @staticmethod
    def _attribute_values(key, values):
        return TraceContinuationAttributeValuesConfig(key=key, values=values)

    @staticmethod
    def _attribute_patterns(key, included=None, excluded=None):
        return TraceContinuationAttributePatternsConfig(
            key=key,
            included=included,
            excluded=excluded,
        )

    def test_always_continue(self):
        provider = self._make_provider(
            TraceContinuationDeciderConfig(always_continue_development={})
        )
        self.assertIs(provider._continuation_decider, ALWAYS_CONTINUE)

    def test_always_restart_with_link(self):
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                always_restart_with_link_development={}
            )
        )
        self.assertIs(provider._continuation_decider, ALWAYS_RESTART_WITH_LINK)

    def test_always_restart_without_link(self):
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                always_restart_without_link_development={}
            )
        )
        self.assertIs(
            provider._continuation_decider, ALWAYS_RESTART_WITHOUT_LINK
        )

    def test_absent_decider_uses_sdk_default(self):
        provider = create_tracer_provider(TracerProviderConfig(processors=[]))
        self.assertIsNone(provider._continuation_decider)

    def test_rule_based_first_match_wins(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.restart_with_link,
                            conditions=self._conditions(
                                attribute_patterns=[
                                    self._attribute_patterns(
                                        "http.route", ["/webhooks/*"]
                                    )
                                ]
                            ),
                        ),
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_values=[
                                    self._attribute_values(
                                        "http.route", ["/webhooks/partner"]
                                    )
                                ]
                            ),
                        ),
                    ]
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        root = tracer.start_span(
            "root", context, attributes={"http.route": "/webhooks/partner"}
        )

        self.assertIsNone(root.parent)
        self.assertNotEqual(
            root.get_span_context().trace_id, remote_parent.trace_id
        )
        self.assertEqual(len(root.links), 1)
        self.assertEqual(root.links[0].context, remote_parent)

    def test_rule_based_default_ingress_strategy(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_patterns=[
                                    self._attribute_patterns(
                                        "http.route", ["/internal/*"]
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        root = tracer.start_span(
            "root", context, attributes={"http.route": "/webhooks/partner"}
        )

        self.assertIsNone(root.parent)
        self.assertNotEqual(
            root.get_span_context().trace_id, remote_parent.trace_id
        )
        self.assertEqual(root.links, ())

    def test_rule_based_matches_all_conditions(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            span_kind=SpanKindConfig.server,
                            conditions=self._conditions(
                                attribute_patterns=[
                                    self._attribute_patterns(
                                        "http.route", ["/internal/*"]
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        child = tracer.start_span(
            "child",
            context,
            kind=TraceSpanKind.SERVER,
            attributes={"http.route": "/internal/users"},
        )

        self.assertEqual(child.parent, remote_parent)
        self.assertEqual(
            child.get_span_context().trace_id,
            remote_parent.trace_id,
        )
        self.assertEqual(child.links, ())

    def test_rule_based_egress_action(self):
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.egress,
                            egress_action=(
                                TraceContinuationEgressActionConfig.suppress_trace_context
                            ),
                            span_kind=SpanKindConfig.client,
                        ),
                    ]
                )
            )
        )
        decider = provider._continuation_decider
        self.assertEqual(
            decider.get_description(), "RuleBasedTraceContinuationDecider"
        )
        self.assertEqual(
            decider.should_inject(kind=TraceSpanKind.CLIENT),
            EgressAction.SUPPRESS_TRACE_CONTEXT,
        )

    def test_rule_based_adds_link_attributes(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.restart_with_link,
                            conditions=self._conditions(
                                attribute_patterns=[
                                    self._attribute_patterns(
                                        "http.route", ["/webhooks/*"]
                                    )
                                ]
                            ),
                            link_attributes=[
                                AttributeNameValue(
                                    name="otel.trace_continuation.reason",
                                    value="external_webhook",
                                )
                            ],
                        ),
                    ]
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        root = tracer.start_span(
            "root", context, attributes={"http.route": "/webhooks/partner"}
        )

        self.assertEqual(len(root.links), 1)
        self.assertEqual(
            root.links[0].attributes,
            {"otel.trace_continuation.reason": "external_webhook"},
        )

    def test_rule_based_expands_multiple_attribute_values(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_values=[
                                    self._attribute_values(
                                        "http.route", ["/health", "/ready"]
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        health = tracer.start_span(
            "health", context, attributes={"http.route": "/health"}
        )
        ready = tracer.start_span(
            "ready", context, attributes={"http.route": "/ready"}
        )
        other = tracer.start_span(
            "other", context, attributes={"http.route": "/other"}
        )

        self.assertEqual(health.parent, remote_parent)
        self.assertEqual(ready.parent, remote_parent)
        self.assertIsNone(other.parent)

    def test_no_decider_type_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            self._make_provider(TraceContinuationDeciderConfig())

    def test_rule_based_attribute_values_stringifies_values(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_values=[
                                    self._attribute_values(
                                        "http.response.status_code", ["404"]
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        child = tracer.start_span(
            "child",
            context,
            attributes={"http.response.status_code": 404},
        )

        self.assertEqual(child.parent, remote_parent)

    def test_rule_based_attribute_values_match_exactly(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_values=[
                                    self._attribute_values(
                                        "http.response.status_code", ["4*"]
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        root = tracer.start_span(
            "root",
            context,
            attributes={"http.response.status_code": "404"},
        )

        self.assertIsNone(root.parent)
        self.assertNotEqual(
            root.get_span_context().trace_id, remote_parent.trace_id
        )

    def test_rule_based_duplicate_attribute_conditions_are_anded(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_values=[
                                    self._attribute_values(
                                        "http.route", ["/health", "/ready"]
                                    ),
                                    self._attribute_values(
                                        "http.route", ["/ready", "/live"]
                                    ),
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        ready = tracer.start_span(
            "ready", context, attributes={"http.route": "/ready"}
        )
        health = tracer.start_span(
            "health", context, attributes={"http.route": "/health"}
        )

        self.assertEqual(ready.parent, remote_parent)
        self.assertIsNone(health.parent)

    def test_rule_based_attribute_patterns_exclude_values(self):
        remote_parent, context = self._remote_parent_context()
        provider = self._make_provider(
            TraceContinuationDeciderConfig(
                rule_based_development=RuleBasedTraceContinuationDeciderConfig(
                    rules=[
                        self._rule(
                            direction=TraceContinuationDirectionConfig.ingress,
                            strategy=TraceContinuationStrategyConfig.continue_,
                            conditions=self._conditions(
                                attribute_patterns=[
                                    self._attribute_patterns(
                                        "http.route",
                                        included=["/internal/*"],
                                        excluded=["/internal/health"],
                                    )
                                ]
                            ),
                        ),
                    ],
                    default_ingress_strategy=(
                        TraceContinuationStrategyConfig.restart_without_link
                    ),
                )
            )
        )
        tracer = provider.get_tracer(__name__)
        users = tracer.start_span(
            "users", context, attributes={"http.route": "/internal/users"}
        )
        health = tracer.start_span(
            "health", context, attributes={"http.route": "/internal/health"}
        )

        self.assertEqual(users.parent, remote_parent)
        self.assertIsNone(health.parent)
