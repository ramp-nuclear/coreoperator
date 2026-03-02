from typing import Sequence, TypeVar
try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from coremaker.core import Site

from coreoperator.mobilization.grid_action import (
        _ensure_unique, GridAction, SiteDict, set_rods
        )


class Remove(GridAction):
    """remove rod from grid"""

    ser_identifier = "RodRemove"
    
    def __init__(self, sites: Sequence[Site]):
        _ensure_unique(sites)
        self.sites = sites

    def apply(self, d: SiteDict) -> None:
        set_rods(d, {site: None for site in self.sites})

    def __eq__(self: Self, other: Self):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__getstate__() == other.__getstate__()

    def __hash__(self):
        return hash(self.__getstate__())

    def __getstate__(self):
        return frozenset(self.sites)

    def __setstate__(self, state):
        self.sites = tuple(state)

    def __repr__(self) -> str: return 'Remove: ' + ','.join(self.sites)
