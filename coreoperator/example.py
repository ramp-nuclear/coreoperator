from coremaker.example import example_core

from coreoperator.history import History, StateParams
from coreoperator.operational_state import OperationalState

blank_hist = History()
example_state = OperationalState(history=blank_hist,
                                 params=StateParams(power=0),
                                 tags={"blank"},
                                 core=example_core,
                                 )
