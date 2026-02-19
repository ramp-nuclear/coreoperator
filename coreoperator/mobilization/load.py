from typing import Callable, Sequence
from coremaker.protocols.core import Site
from coremaker.protocols.element import Element
from coremaker.transform import Transform, identity
from coreoperator.mobilization.grid_action import _ensure_unique, Position, \
    DefinitePosition

RodFactory = Callable[[], Element]


class LoadChain:
    """Represents a chain of movements of rods, beginning with a load to the first site, and removing the last.

    Parameters
    ----------
    factory: RodFactory
        A callable that returns the inserted element.
    sites: Sequence[Position]
        Either a sequence of sites in the grid, or a sequence of (site, transform) tuples.
        If the latter is given, the transformation is applied to the rod inserted to the corresponding site.
    """

    def __init__(self, factory: RodFactory, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]
        self.factory = factory
        self.factory_name = factory.__name__

    def __eq__(self, other: "LoadChain"):
        return (type(self) == type(other) and
                self.factory_name == other.factory_name and
                self.sites == other.sites)

    def __hash__(self):
        return hash((self.factory_name, tuple(self.sites)))

    @property
    def _factory_name(self) -> str:
        return self.factory_name

    def __repr__(self) -> str:
        try:
            factory = self._factory_name
        except AttributeError:
            return super().__repr__()
        else:
            return (f"LoadChain: {factory}->"
                    + '->'.join(map(lambda x: f"{x[1]} applied at {x[0]}", self.sites)))


class LoadSite(LoadChain):
    """represents loading a rod to a core."""

    def __init__(self, factory: RodFactory, site: Position, transform: Transform = identity):
        super().__init__(factory, [(site, transform)])

    def __repr__(self) -> str:
        return super().__repr__().replace('LoadChain', 'Load', 1)
