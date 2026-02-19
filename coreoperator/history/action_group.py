from dataclasses import dataclass, field
from typing import Dict

from coreoperator.mobilization.load import LoadSite
from coreoperator.mobilization.scheme import Scheme


@dataclass
class ActionGroup:
    """
    A Scheme of actions and parameters related to the
    operational history.

    Parameters
    ----------
    params: dict
     parameters about the operational history, like power for example
    scheme: Scheme
     scheme of actions.
    """
    params: Dict = field(default_factory=dict)
    scheme: Scheme = field(default_factory=Scheme)

    def __hash__(self):
        return hash((tuple(self.params.items()), self.scheme))


def check_primary_actiongroup(group: ActionGroup):
    """
    Checks if the group is acceptable as the origin of the history. raises
    an Error otherwise

    Parameters
    ----------
    group: ActionGroup

    Raises
    ------
    ValueError, when a Load is part of the actions of the ActionGroup
    KeyError, when the power isn't part of the parameters

    """
    for gridaction in group.scheme.actions:
        if not isinstance(gridaction, LoadSite):
            raise ValueError(f'primary group action cannot '
                             f'have gridaction of type {type(gridaction)}')
    if 'power' not in group.params:
        raise KeyError(f'primary ActionGroup must track power')
