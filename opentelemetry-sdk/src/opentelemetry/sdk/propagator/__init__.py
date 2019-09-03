from opentelemetry.propagator import Propagator as PropagatorAPI


class Propagator(PropagatorAPI):
    def extract(self, get_from_carrier, carrier):
        self.http_format.extract(self.context, get_from_carrier, carrier)

    def inject(self, set_in_carrier, carrier):
        self.http_format.inject(self.context, set_in_carrier, carrier)

    def from_bytes(self, byte_representation):
        self.binary_formatter.from_bytes(self.context, byte_representation)

    def to_bytes(self):
        return self.binary_formatter.to_bytes(self.context)
