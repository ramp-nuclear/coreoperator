from typing import Sequence

from coremaker.protocols.core import Site
from coremaker.transform import identity

from coreoperator.mobilization.grid_action import Position, _ensure_unique, DefinitePosition


class TransformInPlace:
    """
    This class represents a mobilization where all rods remain in the same sites but each rod is transformed
    inside its site.
    """

    def __init__(self, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]

    def __eq__(self, other: "TransformInPlace"):
        return (type(self) == type(other) and
                self.sites == other.sites)

    def __hash__(self):
        return hash(tuple(self.sites))

    def __repr__(self) -> str:
        return (f"Rotation:"
                + ','.join(map(lambda x: f"{x[0]} transformed by {x[1]}", self.sites)))
