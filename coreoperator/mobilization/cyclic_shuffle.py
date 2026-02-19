from typing import Sequence

from coremaker.protocols.core import Site
from coremaker.transform import identity

from coreoperator.mobilization.grid_action import _ensure_unique, Position, \
    DefinitePosition, rotate_left


class CyclicShuffle:
    """represents a single connected permutation of rods"""

    def __init__(self, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]
        self._movement = frozenset(zip(rotate_left(sites), sites))

    def __eq__(self, other):
        return (type(self) == type(other) and
                self._movement == other._movement)

    def __hash__(self):
        return hash(self._movement)

    def __repr__(self):
        return 'Shuffle: ->' + '->'.join(map(repr, self.sites)) + '->'
