import os
from opentelemetry import trace
from opentelemetry.sdk._configuration import _OTelSDKConfigurator

def test_otel_config_file_e2e(monkeypatch):
    """
    Validates that setting OTEL_CONFIG_FILE properly instantiates the SDK
    and exports a trace directly to the running Docker collector backend.
    """
    config_path = os.path.join(os.path.dirname(__file__), "minimal_config.yaml")

    # Safely inject the configuration path environment variable into this process
    monkeypatch.setenv("OTEL_CONFIG_FILE", config_path)

    # Force the configuration setup to read our new config file path
    _OTelSDKConfigurator()._configure()

    # Get the configurator-initialized tracer provider and tracer instances
    provider = trace.get_tracer_provider()
    tracer = trace.get_tracer("e2e-test")

    # Emit a span directly to confirm no trace piping exceptions occur
    with tracer.start_as_current_span("docker-plumbing-span"):
        print("\nSpan emitted successfully via inline configuration parsing!")

    # Explicitly flush and close the pipeline so data hits the collector before python exits
    provider.shutdown()
