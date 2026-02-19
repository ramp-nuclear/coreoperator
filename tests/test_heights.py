"""Tests for height changes.

"""
from math import isclose
from pathlib import PurePath

import hypothesis.strategies as st
import pytest
from coremaker.core import Core
from coremaker.elements.box import ExcludeFrame
from coremaker.grids import CartesianGrid
from coremaker.materials.aluminium import al1050
from coremaker.materials.steel import steel_304L
from coremaker.materials.water import make_light_water
from coremaker.transform import Transform
from hypothesis import given
from packaging.version import Version

from coreoperator import OperationalState, History
from coreoperator.history.action_group import ActionGroup


@pytest.fixture(scope='module')
def _example_state() -> OperationalState:
    simple_rod = ExcludeFrame(frame_dimensions=(11., 11., 150.),
                              picture_dimensions=(8., 8., 70.),
                              frame_name=PurePath('baz'),
                              picture_name=PurePath('moo'),
                              frame_mixture=al1050,
                              picture_mixture=steel_304L,
                              picture_translation=(0, 0, 40.)
                              )
    grid = CartesianGrid((0., 0., 0.),
                         (5, 5),
                         (10., 10.),
                         150.,
                         make_light_water(40.),
                         rod_contents={'A2': simple_rod})
    coretree = ExcludeFrame(frame_dimensions=(50., 50., 150.),
                            picture_dimensions=(10., 10., 100.),
                            frame_name=PurePath('foo'),
                            picture_name=PurePath('bar'),
                            frame_mixture=al1050,
                            picture_mixture=steel_304L,
                            picture_translation=(0, 0, 25.)
                            )
    lat = grid.lattice
    lat.transform = Transform((10., 10., 20.))
    coretree.nodes[PurePath('Lat')] = lat
    c = Core(grid,
             {'TreeNode': ('A node in the tree, not top',
                           (PurePath('CoreTree/foo/bar'),)),
              'SiteNode': ('A node in the grid, not top', (PurePath('A2/baz/moo'),)),
              'TreeTop': ('A node in the tree, top', (PurePath('CoreTree/foo'),)),
              'SiteTop': ('A node in the grid, top', (PurePath('A2/baz'),)),
              },
             coretree
             )
    state = OperationalState(design_name='fake',
                             history=History(ActionGroup(params={'power': 1.})),
                             release=Version('0.0.0'),
                             core=c)
    return state


aliases = st.sampled_from(['TreeNode', 'SiteNode'])
height_shifts = st.floats(min_value=-50, max_value=0.)


@given(dh=height_shifts, alias=aliases)
def test_translation_forward_and_back_gives_same_transform_on_tree(
        _example_state: OperationalState, dh: float, alias: str):
    z1 = _example_state.core.transform_of(_example_state.core.aliases[alias][1][0])
    s2 = _example_state.shift_control_height(alias, dh)
    s3 = s2.shift_control_height(alias, -dh)
    z2 = s3.core.transform_of(s3.core.aliases[alias][1][0])
    assert z1 == z2


@given(h=st.floats(min_value=-25., max_value=25.), alias=aliases)
def test_translation_absolute_has_absolute_h(_example_state: OperationalState,
                                             h: float, alias: str):
    s2 = _example_state.new_control_height(alias, h)
    z = s2.core.transform_of(s2.core.aliases[alias][1][0])
    assert isclose(z.translation[-1].item(), h, rel_tol=1e-10, abs_tol=1e-4)


@given(dh=height_shifts, alias=aliases)
def test_translation_of_sub_does_not_move_anything_else(_example_state: OperationalState,
                                                        dh: float, alias: str):
    zs = {path: node.transform for path, node in _example_state.core.nodes}
    change_paths = {path for path in _example_state.core.aliases[alias][1]}
    s2 = _example_state.shift_control_height(alias, dh)
    new_zs = {path: node.transform for path, node in s2.core.nodes}
    for path, t in new_zs.items():
        if path not in change_paths:
            assert t == zs[path]
    for path in change_paths:
        assert isclose(new_zs[path].translation[-1].item(), zs[path].translation[-1].item() + dh,
                       rel_tol=1e-10, abs_tol=1e-4)


@pytest.mark.parametrize(
    ('alias', 'sub'),
    [('TreeTop', PurePath('CoreTree/foo/bar')),
     ('SiteTop', PurePath('A2/baz/moo'))
     ])
@given(dh=height_shifts)
def test_translation_of_top_does_move_bottom_the_same_way(
        _example_state: OperationalState, dh: float, alias: str, sub: PurePath):
    zs = {path: _example_state.core.transform_of(path)
          for path, _ in _example_state.core.nodes}
    s2 = _example_state.shift_control_height(alias, dh)
    new_zs = {path: s2.core.transform_of(path) for path, _ in s2.core.nodes}
    assert isclose(new_zs[sub].translation[-1].item(), zs[sub].translation[-1].item() + dh,
                   rel_tol=1e-10, abs_tol=1e-4)
