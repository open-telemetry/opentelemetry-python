from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec


class InjectorFinder(MetaPathFinder):

    def __init__(self, loader):
        self._loader = loader

    def find_spec(self, fullname, path, target=None):
        if self._loader.provides(fullname):
            return self._gen_spec(fullname)

    def _gen_spec(self, fullname):
        return ModuleSpec(fullname, self._loader)
