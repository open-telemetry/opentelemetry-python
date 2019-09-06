from opentelemetry.propagator import Propagator as PropagatorAPI


class Propagator(PropagatorAPI):
    def extract(self, get_from_carrier, carrier):
        self._httptextformat.extract(self._context, get_from_carrier, carrier)

    def inject(self, set_in_carrier, carrier):
        self._httptextformat.inject(self._context, set_in_carrier, carrier)

    def from_bytes(self, byte_representation):
        self._binaryformat.from_bytes(self._context, byte_representation)

    def to_bytes(self):
        return self._binaryformat.to_bytes(self._context)
