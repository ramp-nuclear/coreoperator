from datetime import timedelta

from coreoperator.history import OperationalPeriod, StateParams, History
from coreoperator.mobilization import Scheme, CyclicShuffle


def test_history_changes_dont_affect_original():
    origin = History([OperationalPeriod(StateParams(power=10.), timedelta(days=1))])
    new_history = origin.timestep(StateParams(power=6.), timedelta(days=3.))
    assert len(new_history) == 2
    assert len(origin) == 1
    assert new_history.current_params["power"] == 6.
    assert origin.current_params["power"] == 10.


def test_history_is_joined_if_parameters_are_the_same():
    period = OperationalPeriod(StateParams(power=10.), timedelta(days=1))
    origin = History([period])
    new_period = period.copy(time=timedelta(days=3))
    new = origin.timestep(new_period.params, new_period.time)
    assert len(new) == len(origin) == 1
    assert new.steps[-1] == new_period.copy(time=timedelta(days=4))


def test_history_is_joined_if_two_schemes_are_applies():
    actions1 = (CyclicShuffle(["A1", "A2"]), CyclicShuffle(["B1", "B2"]))
    actions2 = (CyclicShuffle(["A1", "B1"]),)
    s1, s2 = Scheme(actions1), Scheme(actions2)
    s = s1 @ s2
    origin = History([s1])
    new = origin.new_cycle(s2)
    assert len(origin) == len(new) == 1
    assert new_steps[-1] == s

