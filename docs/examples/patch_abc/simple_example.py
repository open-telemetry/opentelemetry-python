from abc import ABC, abstractmethod

from opentelemetry.util._wrap import patch_abc


class Greeter(ABC):
    @abstractmethod
    def greet(self):
        pass


class EngishGreeter(Greeter):
    def greet(self):
        print("hello")


class SpanishGreeter(Greeter):
    def greet(self):
        print("hola")


if __name__ == '__main__':
    def my_wrapper(orig_fcn):
        def wrapped_fcn(self, *args, **kwargs):
            print("wrapper running")
            result = orig_fcn(self, *args, **kwargs)
            return result

        return wrapped_fcn


    patch_abc(Greeter, "greet", my_wrapper)

    EngishGreeter().greet()
    SpanishGreeter().greet()
