from itertools import islice, cycle
from typing import Sequence, Protocol, Iterable, TypeVar

from coremaker.core import Site
from coremaker.transform import Transform

DefinitePosition = tuple[Site, Transform]
Position = Site | DefinitePosition


def _ensure_unique(positions: Sequence[Position]):
    sites = [pos if isinstance(pos, Site) else pos[0] for pos in positions]
    if len(sites) != len(set(sites)):
        repeats = {site for site in sites if sites.count(site) > 1}
        raise ValueError("Some sites appear more than once in an action: "
                         f"{repeats}")


class GridAction(Protocol):
    """
    Protocol for an action preformed on sites in a Grid
    """

    sites: Sequence[Position]


T = TypeVar('T')


def rotate_left(it: Iterable[T], n: int = 1) -> tuple[T]:
    """Return a tuple that is a rotated version of a finite iterable.

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
