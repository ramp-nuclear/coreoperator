from operator import itemgetter
from typing import Sequence, TypeVar

from coremaker.protocols.core import Site
from coremaker.transform import identity

from coreoperator.mobilization.grid_action import (
        _ensure_unique, Position, DefinitePosition, rotate_left, rotate_right, 
        GridAction, SiteDict, set_rods, get_transformed_rods,
        )


class CyclicShuffle(GridAction):
    """represents a single connected right permutation of rods"""

    ser_identifier = "CycShuffle"

    def __init__(self, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]
        self._movement = frozenset(zip(rotate_left(self.sites), self.sites))

    def apply(self, d: SiteDict) -> None:
        sites = rotate_right(self.sites)
        rods = get_transformed_rods(sites, d)
        news = dict(zip(map(itemgetter(0), self.sites), rods))
        set_rods(d, news)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._movement == other._movement

    def __hash__(self):
        return hash(self._movement)

    def __repr__(self):
        return 'Shuffle: ->' + '->'.join(map(repr, self.sites)) + '->'
