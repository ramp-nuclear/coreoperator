from functools import partial
from pathlib import PurePath
from typing import Callable, Any

import pandas as pd
from coremaker.protocols.node import NodeLike

from coreoperator.example import example_state
from coreoperator.operational_state import _mostly_water, OperationalState


def _make_df(state: OperationalState,
             dict_from_node: Callable[[NodeLike], dict[str, Any]],
             filt: Callable[[PurePath, NodeLike], bool] = lambda _, __: True,
             ) -> pd.DataFrame:
    filtered_nodes = dict(filter(lambda x: filt(*x), state._core.nodes))
    return pd.DataFrame({path: dict_from_node(node) for path, node in filtered_nodes.items()}).T


_get_densities_df = partial(_make_df, dict_from_node=lambda node: node.mixture.isotopes)
_get_temperatures_df = partial(
        _make_df, dict_from_node=lambda node: {"temperature": node.mixture.temperature}
        )


def test_new_water_density_factor():
    densities_df = _get_densities_df(example_state, filt=_mostly_water)
    # arbitrarily chosen
    factor = 0.7
    new_state = example_state.new_water_density_factor(factor)
    new_densities_df = _get_densities_df(new_state, _mostly_water)
    assert new_densities_df.div(densities_df).eq(factor).all().all()


def test_new_temperature_new_water_temperature_do_same_thing_on_water():
    new_t = example_state.new_temperature(70., to_change=_mostly_water)
    new_wt = example_state.new_water_temperature(70.)
    ndft, ndfw = [_get_densities_df(s) for s in (new_t, new_wt)]
    assert ndfw.div(ndft).fillna(1).eq(1).all().all(), ndfw
    ndft, ndfw = [_get_temperatures_df(s) for s in (new_t, new_wt)]
    assert ndfw.div(ndft).eq(1).all().all(), ndfw

