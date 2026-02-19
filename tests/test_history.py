from copy import deepcopy
from datetime import timedelta

from coreoperator.history.history import History


def test_history_gets_deepcopied():
    origin = History(dict(power=10.0))
    new_history = deepcopy(origin)
    new_history.append(timedelta(days=3.0))
    new_history.append(dict(power=6.0))
    assert new_history.current_params['power'] == 6.0
    assert origin.current_params['power'] == 10.
