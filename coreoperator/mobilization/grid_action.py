from collections import Counter
from itertools import islice, cycle
from typing import Sequence, Protocol, Iterable, TypeVar, Mapping, Hashable, Any, Type
try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from coremaker.protocols.core import Site
from coremaker.protocols.element import Element
from coremaker.transform import Transform
from ramp_core.serializable import Serializable

DefinitePosition = tuple[Site, Transform]
Position = Site | DefinitePosition
T = TypeVar("T")


class SiteDict(Protocol):
    """Partial requirements from a mutable mapping of Site -> Element

    """

    def __getitem__(self, item: Site) -> Element:
        ...

    def __setitem__(self, key: Site, value: Element) -> None:
        ...

    def __delitem__(self, key: Site) -> None:
        ...


class IllegalActionError(ValueError):
    """Error class for illegal grid actions"""


def _ensure_unique(positions: Sequence[Position]):
    if not positions:
        raise IllegalActionError("Cannot create an action with no sites")
    sites = [pos if isinstance(pos, Site) else pos[0] for pos in positions]
    counter = Counter(sites)
    if set(counter.values()) != {1}:
        repeats = {site for site, v in counter.items() if v > 1}
        raise IllegalActionError(f"Some sites appear more than once in an action: {repeats}")


class GridAction(Hashable, Serializable, Protocol):
    """
    Protocol for an action preformed on sites in a Grid
    """

    sites: Sequence[Position]

    def apply(self, d: SiteDict) -> None:
        """Applies the action to the mapping.

        Parameters
        ----------
        d: SiteDict
            Mapping of sites to contents that will be edited

        """
        ...

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, {"sites": ser_sites(self.sites)}

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *_, **__) -> Self:
        return cls(deser_sites(d["sites"]))


def rotate_left(it: Iterable[T], n: int = 1) -> tuple[T, ...]:
    """Return a tuple sequence that is a left-rotated version of a finite iterable.

    Parameters
    ----------
    it: Iterable
        Iterable of finite size to rotate.

    n: int
        The number of left rotations to perform.

    Returns
    -------
    Tuple of the same items in the iterable but with a different order.

    """
    seq = tuple(it)
    return tuple(islice(cycle(seq), n, n + len(seq)))


def rotate_right(it: Iterable[T], n: int = 1) -> tuple[T, ...]:
    """Return a tuple sequence that is the right-rotated version of a finite iterable.

    Parameters
    ----------
    it: Iterable
        Iterable of finite size to rotate
    n: int
        The number of right rotations to perform.

    Returns
    -------
    Tuple of the same items in the iterable but with a different order.

    """
    seq = tuple(it)
    pos0 = (-1 * n) % len(seq)
    return rotate_left(it, n=(-n) % len(seq))


def set_rods(coresites: SiteDict, new_sites: Mapping[Site, Element | None]) -> None:
    """Update rods in the mapping according to the new mapping

    Parameters
    ----------
    coresites: SiteDict
        Original mapping
    new_sites: Mapping[Site, Element | None]
        New information mapping.
        Where a site points to an element, we set that in the new mapping.
        Where it points to None, we eject the rod from that site.

    Raises
    ------
    IllegalActionError
        Raises if a site in new_sites points to None but that site isn't occupied 
        in the original mapping.

    """
    for site, rod in new_sites.items():
        if rod:
            coresites[site] = rod
        elif site in coresites:
            del coresites[site]
        else:
            raise IllegalActionError(f"Can't remove the contents of the unoccupied site: {site}")


def get_transformed_rods(sites: Sequence[tuple[Site, Transform]],
                         rods_at_sites: SiteDict) -> Sequence[Element]:
    """Function that returns the transformed rods at the given sites under the given transformation.

    Parameters
    ----------
    sites: Sequence[tuple[Site, Transform]]
        Sequence of sites and the transforms at each site.
    rods_at_sites: SiteDict
        Mapping of sites and the rods therein.

    Returns
    -------
    Sequence[Element]
        Sequence of the rods at the given sites after the transforms.

    """
    rods = [rods_at_sites[site] for site, _ in sites]
    for (_, transform), rod in zip(sites, rods):
        rod.transform(None, transform)
    return rods


def ser_sites(sites: Iterable[Position]) -> list:
    """Serialize sites as they are written in grid actions

    Parameters
    ----------
    sites: Iterable[Position]
        Sites to serialize

    Returns
    -------
    Serialized form of the sites

    """
    return [[ptup[0], ptup[1].serialize()] if isinstance(ptup, tuple) else ptup
             for ptup in sites]


def deser_sites(slist: list[tuple[str, dict]]) -> list[Position]:
    """Deserialize sites from the common format made by ser_sites

    Parameters
    ----------
    slist: list[tuple[str, dict]]
        Actually a list of 2-lists of this form.

    Returns
    -------
    list[Position]
        The list of positions we started with.

    """
    return [(ptup[0], Transform.deserialize(ptup[1])) if isinstance(ptup, list) else ptup
            for ptup in slist]

