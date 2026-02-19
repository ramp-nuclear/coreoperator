"""Tests for the FeatherState subclass"""
import hypothesis.strategies as st
from coremaker.example import hafnium_block_aliases
from hypothesis import given

from coreoperator.example import example_state
from coreoperator.featherstate import FeatherState


@given(st.sampled_from(range(-1, 10)))
def test_roundabout_compression_for_example_core_gives_the_same_core(clevel):
    state = FeatherState.from_state(example_state, compression_level=clevel)
    assert state == example_state


def test_new_control_height_returns_a_similar_featherstate_for_one_height_and_one_alias():
    fstate = FeatherState.from_state(example_state)
    alias = list(hafnium_block_aliases.keys())[0]
    hup = example_state.new_control_height(alias=alias, height=13)
    fhup = fstate.new_control_height(alias=alias, height=13)
    assert hup == fhup
    assert type(fhup) == FeatherState


def test_new_temperature_returns_a_similar_featherstate_for_one_temperature():
    fstate = FeatherState.from_state(example_state)
    hup = example_state.new_temperature(37)
    fhup = fstate.new_temperature(37)
    assert hup == fhup
    assert type(fhup) == FeatherState

