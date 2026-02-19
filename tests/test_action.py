"""Tests for grid actions

"""
from copy import deepcopy
from functools import partial
from itertools import pairwise
from string import ascii_uppercase as letters
from typing import Tuple, Iterable

import hypothesis.strategies as st
import numpy as np
import pytest
from coremaker.transform import Transform
from hypothesis import given, settings
from more_itertools import first

from coreoperator import OperationalState
from coreoperator.example import example_state
from coreoperator.mobilization import CyclicShuffle, LoadChain, Scheme, Remove
from coreoperator.mobilization.grid_action import rotate_left
from coreoperator.mobilization.transform_inplace import TransformInPlace

Position = Tuple[str, str]


def _repeat_site(seq: Iterable) -> bool:
    _sites = [site for site, _ in seq]
    return len(_sites) != len(set(_sites))


rows = st.sampled_from(letters)
columns = st.integers(min_value=1, max_value=10)
sites = st.tuples(rows, columns).map(lambda x: f'{x[0]}{x[1]}')
_directions = 'NWSE'
directions = st.sampled_from(_directions)
positions = st.tuples(sites, directions)
repeat_lists = st.lists(positions, min_size=2).filter(_repeat_site)
_preLoadChain = partial(LoadChain, lambda: XX)
_factories = [CyclicShuffle, _preLoadChain]
factories = st.sampled_from(_factories)


@settings(max_examples=200)
@given(_sites=repeat_lists, factory=factories)
def test_raises_if_sites_repeat_in_chains(_sites, factory):
    with pytest.raises(ValueError):
        factory(_sites)


def test_remove():
    site = 'A1'
    scheme = Scheme(actions=(Remove(sites=[site]),))
    new_state = example_state.new_after_scheme(scheme)
    assert site not in new_state.core.grid.keys()


intlists = (st.lists(st.integers(), min_size=2)
            .filter(lambda x: any(y != x[0] for y in x))
            )


@given(intlists)
def test_rotate_left_rotates_sequence(lst):
    assert lst != rotate_left(lst)


def test_apply_load_chain():
    state = deepcopy(example_state)
    sites = example_state.core.grid.keys()
    transforms = [Transform(np.array([0., 0., z]))
                  for z in np.linspace(0., 100., len(sites))]

    def factory():
        return deepcopy(state.core.grid[first(sites)])

    load_chain = LoadChain(factory, list(zip(sites, transforms)))

    def label_load_chain(load_chain: LoadChain):
        def _factory():
            rod = load_chain.factory()
            rod.label = load_chain.sites[0][0]
            return rod

        new_load_chain = deepcopy(load_chain)
        new_load_chain.factory = _factory
        return new_load_chain

    scheme = Scheme(actions=(label_load_chain(load_chain),))

    def label_state(state):
        new_state = deepcopy(state)
        for site in new_state.core.grid.keys():
            new_state.core.grid[site].label = site
        return new_state

    state = label_state(state)
    state = state.new_after_scheme(scheme)
    assert isinstance(state, OperationalState)
    assert set(state.core.grid.keys()) == set(state.core.grid.sites())
    assert state.core.grid[first(sites)].label == first(sites)
    assert all(node.transform == first(transforms)
               for _, node in state.core.grid[first(sites)].roots())
    for (site, next_site), transform in zip(pairwise(sites), transforms[1:]):
        assert state.core.grid[next_site].label == site
        for _, node in state.core.grid[next_site].roots():
            assert node.transform == transform


def test_apply_transform_in_place():
    state = deepcopy(example_state)
    sites = example_state.core.grid.keys()
    transforms = [Transform(np.array([0., 0., z]))
                  for z in np.linspace(0., 100., len(sites))]
    action = TransformInPlace(list(zip(sites, transforms)))
    scheme = Scheme(actions=(action,))
    state = state.new_after_scheme(scheme)
    assert isinstance(state, OperationalState)
    assert set(state.core.grid.keys()) == set(state.core.grid.sites())
    assert all(node.transform == first(transforms)
               for _, node in state.core.grid[first(sites)].roots())
    for (site, next_site), transform in zip(pairwise(sites), transforms[1:]):
        for _, node in state.core.grid[next_site].roots():
            assert node.transform == transform
