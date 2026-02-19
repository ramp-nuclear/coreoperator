from datetime import timedelta
from typing import Union

from multipledispatch import dispatch

from coreoperator.history.action_group import ActionGroup
from coreoperator.mobilization.scheme import Scheme

Action = Union[timedelta, ActionGroup]


def get_param(x: Action, param: str):
    if isinstance(x, ActionGroup):
        return x.params.get(param)
    else:
        return None


@dispatch(object)
def cast_to_action(obj: object):
    raise TypeError(f'cannot cast an object of type {type(obj)} to action.')


@dispatch(dict)
def cast_to_action(params: dict):
    return ActionGroup(params=params)


@dispatch(timedelta)
def cast_to_action(x: timedelta):
    return x


@dispatch(Scheme)
def cast_to_action(scheme: Scheme):
    return ActionGroup(scheme=scheme)


@dispatch(ActionGroup)
def cast_to_action(group: ActionGroup):
    return group


@dispatch(object, object)
def add_actions(x, y):
    return cast_to_action(x), cast_to_action(y)


@dispatch(timedelta, timedelta)
def add_actions(x: timedelta, y: timedelta):
    return x + y,


@dispatch(ActionGroup, ActionGroup)
def add_actions(x: ActionGroup, y: ActionGroup):
    params = {**x.params, **y.params}
    scheme = x.scheme @ y.scheme
    return ActionGroup(params=params, scheme=scheme),
