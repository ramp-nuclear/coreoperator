import pandas as pd

from coreoperator.example import example_state
from coreoperator.operational_state import _mostly_water


def _get_water_densities_df(state):
    water_nodes = dict(filter(lambda x: _mostly_water(*x),
                       state.core.nodes))
    return pd.DataFrame({path: node.mixture.isotopes
                                for path, node in water_nodes.items()}).T


def test_new_water_density_factor():
    densities_df = _get_water_densities_df(example_state)
    # arbitrarily chosen
    factor = 0.7
    new_state = example_state.new_water_density_factor(factor)
    new_densities_df = _get_water_densities_df(new_state)
    assert new_densities_df.div(densities_df).eq(factor).all().all()