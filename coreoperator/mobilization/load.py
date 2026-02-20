from copy import deepcopy
from itertools import chain
from operator import itemgetter
from typing import Callable, Sequence, Iterable, Any, Type, TypeVar
try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from coremaker.protocols.core import Site
from coremaker.protocols.element import Element
from coremaker.transform import Transform, identity
from more_itertools import first
from ramp_core.serializable import deserialize_default, Serializable

from coreoperator.mobilization.grid_action import (
        _ensure_unique, Position, DefinitePosition, GridAction, SiteDict,
        set_rods, get_transformed_rods, ser_sites, deser_sites
        )

RodFactory = Callable[[], Element]


class LoadChain(GridAction):
    """Represents a chain of movements of rods, beginning with a load to the first site, and removing the last.

    Parameters
    ----------
    factory: RodFactory
        A callable that returns the inserted element.
    sites: Sequence[Position]
        Either a sequence of sites in the grid, or a sequence of (site, transform) tuples.
        If the latter is given, the transformation is applied to the rod inserted to the corresponding site.

    """

    ser_identifier = "LoadChain"

    def __init__(self, factory: RodFactory, sites: Sequence[Position]):
        _ensure_unique(sites)
        self.sites: list[DefinitePosition] = [
            (site, identity) if isinstance(site, Site) else site
            for site in sites]
        self.factory = factory
        self.factory_name = factory.__name__

    def serialize(self) -> tuple[str, dict[str, Any]]:
        rod = self.factory()
        return self.ser_identifier, {"example": rod.serialize(),
                                     "sites": ser_sites(self.sites),
                                     }

    @staticmethod
    def _deser_factory(example, supported) -> RodFactory:
        rod: Element = deserialize_default(example, supported=supported)

        def _factory() -> Element:
            return deepcopy(rod)
        return _factory

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        _factory = cls._deser_factory(d["example"], supported)
        return cls(factory=_factory, sites=deser_sites(d["sites"]))

    def apply(self, d: SiteDict) -> None:
        sites: Iterable[Site] = list(map(itemgetter(0), self.sites))
        transforms = list(map(itemgetter(1), self.sites))
        new_rod = self.factory()
        new_rod.transform(None, first(transforms))
        rods = get_transformed_rods(list(zip(sites[:-1], transforms[1:])), d)
        set_rods(d, dict(zip(sites, chain((new_rod,), rods))))

    def __eq__(self, other: "LoadChain"):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.factory() == other.factory() and self.sites == other.sites)

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

    ser_identifier = "LoadSite"

    def __init__(self, factory: RodFactory, site: Site, transform: Transform = identity):
        super().__init__(factory, [(site, transform)])

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        _factory = cls._deser_factory(d["example"], supported)
        sites = deser_sites(d["sites"])
        site, t = sites[0]
        return cls(factory=_factory, site=site, transform=t)

    def __repr__(self) -> str:
        return super().__repr__().replace('LoadChain', 'Load', 1)
