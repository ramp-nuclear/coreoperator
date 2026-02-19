from operator import itemgetter
from typing import Sequence

from coremaker.protocols.core import Site
from coremaker.transform import identity

from coreoperator.mobilization.grid_action import (
        Position, _ensure_unique, DefinitePosition, GridAction, SiteDict, 
        set_rods, get_transformed_rods
        )


class TransformInPlace(GridAction):
    """
    This class represents a mobilization where all rods remain in the same sites but each rod is transformed
    inside its site.
    """

    ser_identifier = "InplaceTransform"


    def __init__(self, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]

    def apply(self, d: SiteDict) -> None:
        rods = get_transformed_rods(self.sites, d)
        news = dict(zip(map(itemgetter(0), self.sites), rods))
        set_rods(d, news)

    def __eq__(self, other: "TransformInPlace"):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.sites == other.sites

    def __hash__(self):
        return hash(tuple(self.sites))

    def __repr__(self) -> str:
        return (f"Rotation:"
                + ','.join(map(lambda x: f"{x[0]} transformed by {x[1]}", self.sites)))
