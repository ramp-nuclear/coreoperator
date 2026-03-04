"""Tests for serialization and deserialization"""
import json
from collections import Counter
from datetime import timedelta
from string import ascii_lowercase

import hypothesis.strategies as st
from coremaker.core import Core
from coremaker.grids import NullGrid
from coremaker.transform import identity, rotate90, rotate180, rotate270
from coremaker.tree import Tree
from hypothesis import given, settings
from ramp_core import RampJSONDecoder, RampJSONEncoder

from coreoperator import jsonable
from coreoperator.featherstate import FeatherState
from coreoperator.history import History, OperationalPeriod, StateParams
from coreoperator.mobilization import (
    CyclicShuffle,
    LoadChain,
    LoadSite,
    Remove,
    Scheme,
    TransformInPlace,
)
from coreoperator.operational_state import OperationalState

_null_core = Core(grid=NullGrid(), aliases={}, tree=Tree(), outer_geometry=None)


class _MockSer(int):

    ser_identifier = "_MockSer"

    def serialize(self): return self.ser_identifier, {"v": int(self)}

    @classmethod
    def deserialize(cls, d, *_, **__): return cls(d["v"])


sites = st.tuples(st.sampled_from(ascii_lowercase), 
                  st.integers(min_value=1, max_value=99)
                  ).map(lambda t: f"{t[0]}{t[1]}")
site_lists = st.lists(sites, min_size=1, max_size=10, unique=True)
transforms = st.sampled_from([identity, rotate90, rotate180, rotate270])
positions = st.tuples(sites, transforms)
position_lists = st.lists(st.one_of(sites, positions), min_size=1, max_size=10,
                          unique_by=lambda x: x[0] if isinstance(x, tuple) else x)
factories = st.integers(min_value=0, max_value=100).map(lambda x: lambda: _MockSer(x))

removals = st.builds(Remove, sites=site_lists)
shuffles = st.builds(CyclicShuffle, sites=position_lists.filter(lambda x: len(x) > 1))
load_singles = st.builds(LoadSite, factory=factories, site=sites, transform=transforms)
loadchains = st.builds(LoadChain, factory=factories, sites=position_lists)
inplaces = st.builds(TransformInPlace, sites=position_lists)
actions = st.one_of(removals, shuffles, loadchains, load_singles)
action_lists = st.lists(actions, min_size=1, max_size=8)
schemes = st.builds(Scheme, actions=action_lists.map(tuple))

powers = st.floats(min_value=0, max_value=100, allow_subnormal=False)
par_dicts = st.dictionaries(keys=st.text(alphabet=ascii_lowercase, min_size=1, max_size=10).filter(lambda x: x != "power"),
                            values=powers,
                            min_size=0, max_size=10)
_datums = st.tuples(powers, par_dicts)
state_pars = _datums.map(lambda x: StateParams(x[0], **x[1]))
periods = st.builds(OperationalPeriod, 
                    params=state_pars,
                    time=st.timedeltas(min_value=timedelta(seconds=1), max_value=timedelta(days=31))
                    )
histories = st.lists(st.one_of(periods, schemes), min_size=0, max_size=10).map(History)

states = st.builds(OperationalState,
                   params=state_pars,
                   history=histories,
                   tags=st.sets(st.text(alphabet=ascii_lowercase, min_size=1), min_size=0, max_size=4),
                   core=st.just(_null_core)
                   )

compressions = st.sampled_from(range(-1, 10))
feathers = st.tuples(states, compressions).map(lambda x: FeatherState.from_state(x[0], compression_level=x[1]))


strats = {
        StateParams: state_pars,
        OperationalPeriod: periods,
        LoadSite: load_singles,
        LoadChain: loadchains,
        CyclicShuffle: shuffles,
        Remove: removals,
        TransformInPlace: inplaces,
        Scheme: schemes,
        History: histories,
        OperationalState: states,
        FeatherState: feathers
        }


def test_no_two_identifiers_the_same():
    c = dict(Counter([c.ser_identifier for c in jsonable]))
    assert set(c.values()) == {1}, {key: value for key, value in c.items() if value != 1}


def test_strat_for_all_supported():
    assert set(strats) == set(jsonable), (set(jsonable) - set(strats), (set(strats) - set(jsonable)))


def _test_strat_makes_right_type(c, x): assert isinstance(x, c)


RampJSONDecoder.supported = {c.ser_identifier: c for c in jsonable + [Core, NullGrid, _MockSer]}


def _test_ser_deser(x):
    s = json.dumps(x, cls=RampJSONEncoder)
    try:
        v = json.loads(s, cls=RampJSONDecoder)
    except (RuntimeError, TypeError):
        print(s)
        raise
    assert x == v, (x, v, s)


for cls, strat in strats.items():
    globals()[f"test_ser_deser_{cls.__name__}"] = settings(deadline=None)(given(strat)(_test_ser_deser))
    globals()[f"test_strat_type_{cls.__name__}"] = settings(deadline=None)(
            given(st.just(cls), strat)(_test_strat_makes_right_type))

