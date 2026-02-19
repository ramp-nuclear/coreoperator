from itertools import chain
from operator import itemgetter
from typing import Hashable, Iterable, Sequence, MutableMapping

from coremaker.protocols.core import Core, Site
from coremaker.protocols.element import Element
from coremaker.transform import Transform
from more_itertools import first
from multipledispatch import dispatch

from coreoperator.mobilization import CyclicShuffle, GridAction, Remove, \
    LoadChain, Scheme
from coreoperator.mobilization.grid_action import rotate_left
from coreoperator.mobilization.transform_inplace import TransformInPlace

Alias = Hashable
SCRAM = Element

MaybeRod = Element | None
SiteDict = MutableMapping[Site, Element]


def _set_rods(coresites: SiteDict, new_sites: dict[Site, MaybeRod]):
    for site, rod in new_sites.items():
        if rod:
            coresites[site] = rod
        elif site in coresites:
            del coresites[site]
        elif site not in coresites:
            raise ValueError(f"can't remove the contents of the unoccupied "
                             f"site:{site}")


def get_transformed_rods(sites: Sequence[tuple[Site, Transform]],
                         rods_at_sites: SiteDict) -> Sequence[Element]:
    """
    Function that returns the transformed rods at the given sites under the
    given transformation.

    Parameters
    ----------
    sites: Sequence[Tuple[Site, Transform]]
        Sequence of sites and the transforms at each site
    rods_at_sites: SiteDict
        Dict of sites and the rods at those sites.

    Returns
    -------
    Sequence[Element]
        Sequence of the rods at the given sites after the transforms.
    """
    rods = [rods_at_sites[site] for (site, _) in sites]
    for (_, transform), rod in zip(sites, rods):
        rod.transform(None, transform)
    return rods


@dispatch(object, object)
def apply_grid_action(d: SiteDict, action: GridAction):
    raise NotImplementedError(
        f'{apply_grid_action.__name__} is not implemented for {type(action)}.')


@dispatch(object, CyclicShuffle)
def apply_grid_action(d: SiteDict, shuffle: CyclicShuffle):
    sites = rotate_left(shuffle.sites)
    rods = get_transformed_rods(sites, d)
    news = dict(zip(map(itemgetter(0), sites), rods))
    _set_rods(d, news)


@dispatch(object, TransformInPlace)
def apply_grid_action(d: SiteDict, action: TransformInPlace):
    rods = get_transformed_rods(action.sites, d)
    news = dict(zip(map(itemgetter(0), action.sites), rods))
    _set_rods(d, news)


@dispatch(object, LoadChain)
def apply_grid_action(d: SiteDict, loadchain: LoadChain):
    sites: Iterable[Site] = list(map(itemgetter(0), loadchain.sites))
    transforms: Iterable[Transform] = list(map(itemgetter(1), loadchain.sites))
    new_rod = loadchain.factory()
    new_rod.transform(None, first(transforms))
    rods = get_transformed_rods(list(zip(sites[:-1], transforms[1:])), d)
    _set_rods(d, dict(zip(sites, chain((new_rod,), rods))))


@dispatch(object, Remove)
def apply_grid_action(d: SiteDict, remove: Remove):
    _set_rods(d, {site: None for site in remove.sites})


def apply_mobilization(core: Core, mobilization: Scheme):
    for action in mobilization.actions:
        apply_grid_action(core.grid, action)
