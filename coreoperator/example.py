from coremaker.example import example_core
from packaging.version import Version

from coreoperator import History, OperationalState
from coreoperator.history.action_group import ActionGroup

blank_hist = History(ActionGroup(params={'power': 0.0}))
ver = Version('0.0.0')
example_state = OperationalState(design_name='example_state',
                                 history=blank_hist,
                                 release=ver,
                                 core=example_core)
