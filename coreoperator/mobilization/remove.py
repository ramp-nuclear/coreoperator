from typing import Sequence

from coremaker.core import Site

from coreoperator.mobilization.grid_action import _ensure_unique


class Remove:
    """remove rod from grid"""

    def __init__(self, sites: Sequence[Site]):
        _ensure_unique(sites)
        self.sites = sites

    def __eq__(self, other: "Remove"):
        return (type(self) == type(other)
                and self.__getstate__() == other.__getstate__())

    def __hash__(self):
        return hash(self.__getstate__())

    def __getstate__(self):
        return frozenset(self.sites)

    def __setstate__(self, state):
        self.sites = tuple(state)

    def __repr__(self) -> str: return 'Remove: ' + ','.join(self.sites)
