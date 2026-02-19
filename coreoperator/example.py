from coremaker.example import example_core

from coreoperator.operational_state import OperationalState
from coreoperator.history import StateParams, History

blank_hist = History()
example_state = OperationalState(history=blank_hist,
                                 params=StateParams(power=0),
                                 tags={"blank"},
                                 core=example_core,
                                 )
