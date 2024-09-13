# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
from os import listdir
from os.path import isdir, join

# configure django to avoid the following exception:
# django.core.exceptions.ImproperlyConfigured: Requested settings, but settings
# are not configured. You must either define the environment variable
# DJANGO_SETTINGS_MODULE or call settings.configure() before accessing settings.
from django.conf import settings

settings.configure()


source_dirs = [
    os.path.abspath("../opentelemetry-instrumentation/src/"),
]

exp = "../exporter"
exp_dirs = [
    os.path.abspath("/".join(["../exporter", f, "src"]))
    for f in listdir(exp)
    if isdir(join(exp, f))
]

shim = "../shim"
shim_dirs = [
    os.path.abspath("/".join(["../shim", f, "src"]))
    for f in listdir(shim)
    if isdir(join(shim, f))
]

sys.path[:0] = source_dirs + exp_dirs + shim_dirs

# -- Project information -----------------------------------------------------

project = "OpenTelemetry Python"
copyright = "OpenTelemetry Authors"  # pylint: disable=redefined-builtin
author = "OpenTelemetry Authors"


# -- General configuration ---------------------------------------------------

# Easy automatic cross-references for `code in backticks`
default_role = "any"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # API doc generation
    "sphinx.ext.autodoc",
    # Support for google-style docstrings
    "sphinx.ext.napoleon",
    # Infer types from hints instead of docstrings
    "sphinx_autodoc_typehints",
    # Add links to source from generated docs
    "sphinx.ext.viewcode",
    # Link to other sphinx docs
    "sphinx.ext.intersphinx",
    # Add a .nojekyll file to the generated HTML docs
    # https://help.github.com/en/articles/files-that-start-with-an-underscore-are-missing
    "sphinx.ext.githubpages",
    # Support external links to different versions in the Github repo
    "sphinx.ext.extlinks",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "opentracing": (
        "https://opentracing-python.readthedocs.io/en/latest/",
        None,
    ),
    "aiohttp": ("https://aiohttp.readthedocs.io/en/stable/", None),
    "wrapt": ("https://wrapt.readthedocs.io/en/latest/", None),
    "pymongo": ("https://pymongo.readthedocs.io/en/stable/", None),
    "grpc": ("https://grpc.github.io/grpc/python/", None),
}

# http://www.sphinx-doc.org/en/master/config.html#confval-nitpicky
# Sphinx will warn about all references where the target cannot be found.
nitpicky = True
# Sphinx does not recognize generic type TypeVars
# Container supposedly were fixed, but does not work
# https://github.com/sphinx-doc/sphinx/pull/3744
nitpick_ignore = [
    ("py:class", "ValueT"),
    ("py:class", "CarrierT"),
    ("py:obj", "opentelemetry.propagators.textmap.CarrierT"),
    ("py:obj", "Union"),
    (
        "py:class",
        "opentelemetry.sdk.metrics._internal.instrument._Synchronous",
    ),
    (
        "py:class",
        "opentelemetry.sdk.metrics._internal.instrument._Asynchronous",
    ),
    # Even if wrapt is added to intersphinx_mapping, sphinx keeps failing
    # with "class reference target not found: ObjectProxy".
    ("py:class", "ObjectProxy"),
    (
        "py:class",
        "opentelemetry.trace._LinkBase",
    ),
    (
        "py:class",
        "opentelemetry.exporter.otlp.proto.grpc.exporter.OTLPExporterMixin",
    ),
    (
        "py:class",
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2.ExportTraceServiceRequest",
    ),
    (
        "py:class",
        "opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder.OTLPMetricExporterMixin",
    ),
    ("py:class", "opentelemetry.proto.resource.v1.resource_pb2.Resource"),
    (
        "py:class",
        "opentelemetry.proto.collector.metrics.v1.metrics_service_pb2.ExportMetricsServiceRequest",
    ),
    ("py:class", "opentelemetry.sdk._logs._internal.export.LogExporter"),
    ("py:class", "opentelemetry.sdk._logs._internal.export.LogExportResult"),
    (
        "py:class",
        "opentelemetry.proto.collector.logs.v1.logs_service_pb2.ExportLogsServiceRequest",
    ),
    (
        "py:class",
        "opentelemetry.sdk.metrics._internal.exemplar.exemplar_reservoir.FixedSizeExemplarReservoirABC",
    ),
    (
        "py:class",
        "opentelemetry.sdk.metrics._internal.exemplar.exemplar.Exemplar",
    ),
    (
        "py:class",
        "opentelemetry.sdk.metrics._internal.aggregation._Aggregation",
    ),
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "examples/fork-process-model/flask-gunicorn",
    "examples/fork-process-model/flask-uwsgi",
    "examples/error_handler/error_handler_0",
    "examples/error_handler/error_handler_1",
]

_exclude_members = ["_abc_impl"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
    "exclude-members": ",".join(_exclude_members),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# Support external links to specific versions of the files in the Github repo
branch = os.environ.get("READTHEDOCS_VERSION")
if branch is None or branch == "latest":
    branch = "main"

REPO = "open-telemetry/opentelemetry-python/"
scm_raw_web = "https://raw.githubusercontent.com/" + REPO + branch
scm_web = "https://github.com/" + REPO + "blob/" + branch

# Store variables in the epilogue so they are globally available.
rst_epilog = """
.. |SCM_WEB| replace:: {s}
.. |SCM_RAW_WEB| replace:: {sr}
.. |SCM_BRANCH| replace:: {b}
""".format(
    s=scm_web, sr=scm_raw_web, b=branch
)

# used to have links to repo files
extlinks = {
    "scm_raw_web": (scm_raw_web + "/%s", "scm_raw_web"),
    "scm_web": (scm_web + "/%s", "scm_web"),
}


def on_missing_reference(app, env, node, contnode):
    # FIXME Remove when opentelemetry.metrics._Gauge is renamed to
    # opentelemetry.metrics.Gauge
    if node["reftarget"] == "opentelemetry.metrics.Gauge":
        return contnode


def setup(app):
    app.connect("missing-reference", on_missing_reference)
