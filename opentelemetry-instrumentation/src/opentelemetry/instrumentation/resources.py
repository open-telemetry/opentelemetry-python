from typing import Optional
from pkg_resources import get_distribution, VersionConflict, DistributionNotFound


class DependencyConflict:
    required: str = None
    found: Optional[str] = None

    def __init__(self, required, found=None):
        self.required = required
        self.found = found

    def __str__(self):
        return 'DependencyConflict: requested: "{0}" but found: "{1}"'.format(self.required, self.found)


def get_target_dependency_conflict(dist) -> Optional[DependencyConflict]:

    # skip the check if the distribution has not specified any target dependencies
    if 'target' not in dist.extras:
        return

    # figure out target dependencies
    target_dependencies = [dep for dep in dist.requires(('target',)) if dep not in dist.requires()]
    for dep in target_dependencies:
        try:
            get_distribution(str(dep))
        except VersionConflict as exc:
            return DependencyConflict(dep, exc.dist)
        except DistributionNotFound as exc:
            return DependencyConflict(dep)
    return
