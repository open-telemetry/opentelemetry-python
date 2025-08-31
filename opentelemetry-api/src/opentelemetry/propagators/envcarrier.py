import os
import typing
from opentelemetry.propagators.textmap import Getter, Setter

class EnvironmentGetter(Getter[dict]):
    """This class decorates Getter to enable extracting from context and baggage
    from environment variables.
    """
    
    def __init__(self):
        self.env_copy = dict(os.environ)
        self.carrier = {}
        
        for env_key, env_value in self.env_copy.items():
            self.carrier[env_key.lower()] = env_value
    
    def get(self, carrier: dict, key: str) -> typing.Optional[typing.List[str]]:
        """Get a value from the carrier for the given key"""
        val = self.carrier.get(key, None)
        if val is None:
            return None
        if isinstance(val, typing.Iterable) and not isinstance(val, str):
            return list(val)
        return [val]
    
    def keys(self, carrier: dict) -> typing.List[str]:
        """Get all keys from the carrier"""
        return list(self.carrier.keys())

class EnvironmentSetter(Setter[dict]):
    """This class decorates Setter to enable setting context and baggage
    to environment variables.
    """

    def set(self, carrier: typing.Optional[dict], key: str, value: str) -> None:
        """Set a value in the environment for the given key.
        
        Args:
            carrier: Not used for environment setter, but kept for interface compatibility
            key: The key to set
            value: The value to set
        """
        env_key = key.upper()
        
        os.environ[env_key] = value
