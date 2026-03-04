from typing import Hashable, MutableMapping, Sequence

from coremaker.protocols.core import Site
from coremaker.protocols.element import Element
from coremaker.transform import Transform

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

