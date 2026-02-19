from copy import deepcopy
from datetime import timedelta
from functools import reduce
from itertools import takewhile
from typing import Union, List, Dict, Generator

from more_itertools import take

from coreoperator.history.action import Action, add_actions, cast_to_action
from coreoperator.history.action_group import check_primary_actiongroup, \
    ActionGroup
from coreoperator.mobilization.scheme import Scheme


def _repr_timedelta(t: timedelta) -> str:
    return f'{t.days} Days and {t.seconds} Seconds'


class History:
    """
    represents history of the actual state

    Parameters
    ----------
    group: Union[ActionGroup, Dict]
     either an Action group or a dictionary of initial parameters.

    """

    def __init__(self, group: Union[ActionGroup, Dict]):
        group = cast_to_action(group)
        check_primary_actiongroup(group)
        self.actions: List[Action] = [group]

    def append(self, x: Union[timedelta, Scheme, Dict, ActionGroup]):
        """Add a change to this history. This can either be absorbed into the
        latest action to modify it in place or add another action on top.

        Parameters
        ----------
        x: Union[timedelta, Scheme, Dict, ActionGroup]
         A change to the history,

        """
        new_action: Action = cast_to_action(x)
        last_action = self.actions.pop()
        self.actions.extend(add_actions(last_action, new_action))

    @property
    def current_params(self) -> Dict:
        params = (action.params for action in self.actions
                  if isinstance(action, ActionGroup))
        return reduce(recursive_update, params, deepcopy(next(params)))

    @property
    def timedelta(self) -> timedelta:
        return sum(filter(lambda x: isinstance(x, timedelta), self.actions),
                   start=timedelta(0))

    @property
    def steps(self) -> int:
        return sum((1 for action in self.actions
                    if isinstance(action, ActionGroup)
                    and action.scheme.actions),
                   start=-1)

    @property
    def time_since_scheme(self) -> timedelta:
        since_boc = takewhile(lambda x: (not isinstance(x, ActionGroup)
                                         or not x.scheme.actions),
                              self.actions[::-1])
        return sum(filter(lambda x: isinstance(x, timedelta), since_boc),
                   start=timedelta(0))

    def __copy__(self) -> 'History':
        actions = iter(self.actions)
        result = type(self)(next(actions))
        result.actions.extend(actions)
        return result

    def __repr__(self) -> str:
        return ', '.join(take(2, self.full_spec))

    @property
    def full_spec(self) -> Generator[str, None, None]:
        yield f'Steps: {self.steps}'
        yield f'Burnup time: {_repr_timedelta(self.time_since_scheme)}'
        yield f'Total burnup time: {_repr_timedelta(self.timedelta)}'
        yield 'Parameters:'
        yield from (f'    - {param}: {value}'
                    for param, value in self.current_params.items())

    def __hash__(self) -> int:
        return hash(tuple(self.actions))

    def __eq__(self, other) -> int:
        if isinstance(other, History):
            return self.actions == other.actions
        raise NotImplementedError


def recursive_update(default: Dict, custom: Dict):
    """
    Return a dict merged from default and custom.
    """
    if not isinstance(default, dict) or not isinstance(custom, dict):
        raise TypeError('params of recursive_update should be dicts.')
    for key, value in custom.items():
        defaultvalue = default.setdefault(key, {})
        if isinstance(value, dict) and isinstance(defaultvalue, dict):
            default[key] = recursive_update(defaultvalue, value)
        else:
            default[key] = custom[key]
    return default
