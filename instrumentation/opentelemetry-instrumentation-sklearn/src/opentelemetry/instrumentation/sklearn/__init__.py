import logging
from functools import wraps
from typing import Callable, Dict, List, Sequence, Type

from sklearn.base import BaseEstimator
from sklearn.pipeline import FeatureUnion, Pipeline

from opentelemetry.instrumentation.sklearn.version import __version__
from opentelemetry.trace import get_tracer

logger = logging.getLogger(__name__)


def implement_spans(func: Callable, estimator_name: str):
    """Wrap the method call with a span.

    Args:
        func: A callable to be wrapped in a span
        estimator_name: The name of the estimator class. We pass estimator name
          here because there are some wrapped methods in Pipeline that don't
          have ``__self__`` to access the class name.

    Returns:
        The passed function wrapped in a span.
    """
    logger.debug("Instrumenting: %s.%s", estimator_name, func.__name__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_tracer(__name__, __version__).start_as_current_span(
            name="{cls}.{func}".format(cls=estimator_name, func=func.__name__)
        ):
            return func(*args, **kwargs)

    return wrapper


# Methods on which spans should be applied.
DEFAULT_METHODS = ["fit", "transform", "predict", "predict_proba"]

# Classes and their attributes which contain a list of tupled estimators
# through which we should walk recursively for estimators.
DEFAULT_NAMEDTUPLE_ATTRIBS = {
    Pipeline: ["steps"],
    FeatureUnion: ["transformer_list"],
}

# Classes and their attributes which contain an estimator or sequence of
# estimators through which we should walk recursively for estimators.
DEFAULT_ATTRIBS = {}


class SklearnInstrumentor:
    """Instrument a fitted sklearn model with opentelemetry spans.

    Instrument methods of ``BaseEstimator``-derived components in a sklearn
    model.  The assumption is that a machine learning model ``Pipeline`` (or
    class descendent) is being instrumented with opentelemetry. Within a
    ``Pipeline`` is some hierarchy of estimators and transformers.

    The ``instrument_estimator`` method walks this hierarchy of estimators,
    implementing each of the defined methods with its own span.

    Certain estimators in the sklearn ecosystem contain other estimators as
    instance attributes. Support for walking this embedded sub-hierarchy is
    supported with ``recurse_attribs``. This argument is a dictionary
    with classes as keys, and a list of attributes representing embedded
    estimators. By default, ``recurse_attribs`` is empty.

    Similar to Pipelines, there are also estimators which have class attributes
    as a list of 2-tuples; for instance, the ``FeatureUnion`` and its attribute
    ``transformer_list``. Instrumenting estimators like this is also
    supported through the ``recurse_namedtuple_attribs`` argument. This
    argument is a dictionary with classes as keys, and a list of attribute
    names representing the namedtuple list(s). By default, the
    ``recurse_namedtuple_attribs`` dictionary supports
    ``Pipeline`` with ``steps``, and ``FeatureUnion`` with
    ``transformer_list``.

    Note that spans will not be generated for any child transformer whose
    parent transformer has ``n_jobs`` parameter set to anything besides
    ``None`` or ``1``.

    Example:

    .. code-block:: python

        from opentelemetry.instrumentation.sklearn import SklearnInstrumentor
        from sklearn.datasets import load_iris
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline

        X, y = load_iris(return_X_y=True)
        X_train, X_test, y_train, y_test = train_test_split(X, y)

        model = Pipeline(
            [
                ("class", RandomForestClassifier(n_estimators=10)),
            ]
        )

        model.fit(X_train, y_train)

        SklearnInstrumentor().instrument_estimator(model)

    Args:
        methods (list): A list of method names on which to instrument a span.
          This list of methods will be checked on all estimators in the model
          hierarchy.
        recurse_attribs (dict): A dictionary of ``BaseEstimator``-derived
          sklearn classes as keys, with values being a list of attributes. Each
          attribute represents either an estimator or list of estimators on
          which to also implement spans. An example is
          ``RandomForestClassifier`` and its attribute ``estimators_``
        recurse_namedtuple_attribs (dict): A dictionary of ``BaseEstimator``-
          derived sklearn types as keys, with values being a list of
          attribute names. Each attribute represents a list of 2-tuples in
          which the first element is the estimator name, and the second
          element is the estimator. Defaults include sklearn's ``Pipeline``
          and its attribute ``steps``, and the ``FeatureUnion`` and its
          attribute ``transformer_list``.
    """

    def __init__(
        self,
        methods: List[str] = None,
        recurse_attribs: Dict[Type[BaseEstimator], List[str]] = None,
        recurse_namedtuple_attribs: Dict[
            Type[BaseEstimator], List[str]
        ] = None,
    ):
        self.methods = methods or DEFAULT_METHODS
        self.recurse_attribs = recurse_attribs or DEFAULT_ATTRIBS
        self.recurse_namedtuple_attribs = (
            recurse_namedtuple_attribs or DEFAULT_NAMEDTUPLE_ATTRIBS
        )

    def instrument_estimator(self, estimator: BaseEstimator):
        """Instrument a fitted estimator and its hierarchy where configured.

        Args:
            estimator (BaseEstimator): A fitted ``sklearn`` estimator,
              typically a ``Pipeline`` instance.
        """
        if isinstance(
            estimator, tuple(self.recurse_namedtuple_attribs.keys())
        ):
            self._instrument_estimator_namedtuple(estimator=estimator)

        if isinstance(estimator, tuple(self.recurse_attribs.keys())):
            self._instrument_estimator_attribute(estimator=estimator)

        for method_name in self.methods:
            if hasattr(estimator, method_name):
                setattr(
                    estimator,
                    method_name,
                    implement_spans(
                        getattr(estimator, method_name),
                        estimator.__class__.__name__,
                    ),
                )

    def _instrument_estimator_attribute(self, estimator: BaseEstimator):
        """Instrument instance attributes which also contain estimators.

        Examples include ``RandomForestClassifier`` and
        ``MultiOutputRegressor`` instances which have attributes
        ``estimators_`` attributes.

        Args:
            estimator (BaseEstimator): A fitted ``sklearn`` estimator, with an
              attribute which also contains an estimator or collection of
              estimators.
        """
        for klass, attribs in self.recurse_attribs.items():
            if isinstance(estimator, klass):
                for attrib in attribs:
                    attrib_value = getattr(estimator, attrib)
                    if isinstance(attrib_value, Sequence):
                        for value in attrib_value:
                            self.instrument_estimator(estimator=value)
                    else:
                        self.instrument_estimator(estimator=attrib_value,)
                break

    def _instrument_estimator_namedtuple(self, estimator: BaseEstimator):
        """Instrument attributes with (name, estimator) tupled components.

        Examples include Pipeline and FeatureUnion instances which
        have attributes steps and transformer_list, respectively.

        Args:
            estimator: A fitted sklearn estimator, with an attribute which also
              contains an estimator or collection of estimators.
        """
        for klass, attribs in self.recurse_namedtuple_attribs.items():
            if isinstance(estimator, klass):
                for attrib in attribs:
                    if hasattr(estimator, attrib):
                        for _, est in getattr(estimator, attrib):
                            self.instrument_estimator(estimator=est)
                break
