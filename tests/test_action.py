"""Tests for grid actions

"""
from copy import deepcopy
from functools import partial
from itertools import pairwise
from string import ascii_uppercase as letters

import hypothesis.strategies as st
import numpy as np
import pytest
from coremaker.transform import Transform
from hypothesis import given
from more_itertools import first

from coreoperator import OperationalState
from coreoperator.example import example_state
from coreoperator.mobilization import CyclicShuffle, LoadChain, Scheme, Remove
from coreoperator.mobilization.grid_action import rotate_left, IllegalActionError
from coreoperator.mobilization.transform_inplace import TransformInPlace

Position = tuple[str, str]

rows = st.sampled_from(letters)
columns = st.integers(min_value=1, max_value=10)
sites = st.tuples(rows, columns).map(lambda x: f'{x[0]}{x[1]}')
_directions = 'NWSE'
directions = st.sampled_from(_directions)
positions = st.tuples(sites, directions)
repeat_lists = (st.lists(positions, min_size=2)
                .flatmap(lambda seq: st.lists(st.sampled_from(seq), 
                                              min_size=1, max_size=10
                                              ).map(lambda x: seq + x))
                )
_preLoadChain = partial(LoadChain, lambda: 15)
_factories = [CyclicShuffle, _preLoadChain, Remove, TransformInPlace]
factories = st.sampled_from(_factories)


@given(_sites=repeat_lists, factory=factories)
def test_raises_correctly_if_sites_repeat_in_chains(_sites, factory):
    with pytest.raises(IllegalActionError, match="more than once"):
        factory(_sites)


@given(factories)
def test_action_on_no_sites_raises_correctly(factory):
    with pytest.raises(IllegalActionError, match="with no sites"):
        factory([])


def test_remove_causes_a_site_to_not_appear_in_core():
    site = 'A1'
    scheme = Scheme(actions=(Remove(sites=[site]),))
    new_state = example_state.new_after_scheme(scheme)
    assert site not in new_state._core.grid.keys()


intlists = (st.lists(st.integers(), min_size=2)
            .filter(lambda x: any(y != x[0] for y in x))
            )


@given(intlists)
def test_rotate_left_rotates_sequence(lst):
    assert lst != rotate_left(lst)


def _label_state(s: OperationalState) -> OperationalState:
    core = s.core
    for site in core.grid.keys():
        core.grid[site].label = site
    return s.copy(core=core)


def test_apply_load_chain_on_example_state_is_as_expected():
    core_sites = example_state._core.grid.keys()
    transforms = [Transform(np.array([0., 0., z]))
                  for z in np.linspace(0., 100., len(core_sites))]

    def _unlabeled_factory():
        return example_state.core.grid[first(core_sites)]

    load_chain = LoadChain(_unlabeled_factory, list(zip(core_sites, transforms)))

    def _label_load_chain(load: LoadChain):
        def _factory():
            rod = load.factory()
            rod.label = load.sites[0][0]
            return rod

        new_load_chain = deepcopy(load)
        new_load_chain.factory = _factory
        return new_load_chain

    scheme = Scheme(actions=(_label_load_chain(load_chain),))

    state = _label_state(example_state)
    state = state.new_after_scheme(scheme)
    assert isinstance(state, OperationalState)
    assert set(state._core.grid.keys()) == set(state._core.grid.sites())
    assert state._core.grid[first(core_sites)].label == first(core_sites)
    assert all(node.transform == first(transforms)
               for _, node in state._core.grid[first(core_sites)].roots())
    for (site, next_site), transform in zip(pairwise(core_sites), transforms[1:]):
        assert state._core.grid[next_site].label == site
        for _, node in state._core.grid[next_site].roots():
            assert node.transform == transform


def test_apply_transform_in_place_on_example_core():
    core_sites = example_state._core.grid.keys()
    transforms = [Transform(np.array([0., 0., z]))
                  for z in np.linspace(0., 100., len(core_sites))]
    action = TransformInPlace(list(zip(core_sites, transforms)))
    scheme = Scheme(actions=(action,))
    state = example_state.new_after_scheme(scheme)
    assert isinstance(state, OperationalState)
    assert set(state._core.grid.keys()) == set(state._core.grid.sites())
    assert all(node.transform == first(transforms)
               for _, node in state._core.grid[first(core_sites)].roots())
    for (site, next_site), transform in zip(pairwise(core_sites), transforms[1:]):
        for _, node in state._core.grid[next_site].roots():
            assert node.transform == transform

def test_apply_cyclic_shuffle_on_example_core():
    core_sites = example_state._core.grid.keys()
    transforms = [Transform(np.array([0., 0., z]))
                  for z in np.linspace(0., 100., len(core_sites))]
    cyclic_chain = CyclicShuffle(list(zip(core_sites, transforms)))
    state = _label_state(example_state)
    scheme = Scheme(actions=(cyclic_chain,))
    state = state.new_after_scheme(scheme)
    shifted_sites = [state._core.grid[site].label for site in core_sites]
    assert isinstance(state, OperationalState)
    assert set(state._core.grid.keys()) == set(state._core.grid.sites())
    assert shifted_sites[1:] + shifted_sites[:1] == list(core_sites)

