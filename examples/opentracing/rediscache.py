"""
This is an example of a library written to work with opentracing-python. It
provides a simple caching decorator backed by Redis, and uses the OpenTracing
Redis integartion to automatically generate spans for each call to Redis.
"""

import json
import pickle
from functools import wraps

import redis
import redis_opentracing


class RedisCache:
    """Redis-backed caching decorator, using OpenTracing!

    Args:
        tracer: an opentracing.tracer.Tracer
    """

    def __init__(self, tracer):
        redis_opentracing.init_tracing(tracer)
        self.tracer = tracer
        self.client = redis.StrictRedis()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self.tracer.start_active_span("Caching decorator") as scope1:

                # Pickle the call args to get a canonical key. Don't do this in
                # prod!
                key = pickle.dumps((func.__qualname__, args, kwargs))

                pval = self.client.get(key)
                if pval is not None:
                    val = pickle.loads(pval)
                    scope1.span.log_kv(
                        {"msg": "Found cached value", "val": val}
                    )
                    return val

                scope1.span.log_kv({"msg": "Cache miss, calling function"})
                with self.tracer.start_active_span(
                    'Call "{}"'.format(func.__name__)
                ) as scope2:
                    scope2.span.set_tag("func", func.__name__)
                    scope2.span.set_tag("args", str(args))
                    scope2.span.set_tag("kwargs", str(kwargs))

                    val = func(*args, **kwargs)
                    scope2.span.set_tag("val", str(val))

                # Let keys expire after 10 seconds
                self.client.setex(key, 10, pickle.dumps(val))
                return val

        return inner
