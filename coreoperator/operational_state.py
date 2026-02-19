from copy import deepcopy
from datetime import timedelta
from pathlib import PurePath
from typing import Optional, Callable

import numpy as np
from coremaker.amounts import parse_amounts
from coremaker.materials.mixture import Mixture as ConcreteMixture
from coremaker.materials.water import _H2O
from coremaker.protocols.core import Core
from coremaker.protocols.mixture import Mixture
from coremaker.protocols.node import NodeLike
from coremaker.transform import Transform
from isotopes import Isotope, H, O, ZAID
from packaging.version import Version

from coreoperator.history.history import History
from coreoperator.mobilization import Scheme
from coreoperator.mobilization.apply import apply_mobilization
from typing import Sequence

days = float
MW = float
degC = float
kg = float
Filter = Callable[[PurePath, NodeLike], bool]


def _mostly_water(_, node: NodeLike) -> bool:
    """Returns true if the component is mostly made out of hydrogen and oxygen
    atoms.
    """
    if not node.mixture:
        return False
    mixture = node.mixture
    total = sum(mixture.values())
    ho = {H.Z, O.Z}
    ho_total = sum(value for iso, value in mixture.items() if iso.Z in ho)
    return ho <= {x.Z for x in mixture.keys()} and ho_total > total / 2


class OperationalState:
    """
    this class represents a loosely defined reactor's core state.
    """

    def __init__(self, *, design_name: str, history: History,
                 release: Version, core: Core):
        self.design_name = design_name
        self.history = history
        self.release = release
        self.core = core

    def copy(self, **kw) -> "OperationalState":
        """Return a copy of current operational state with modifications
        """
        kwargs = dict(design_name=self.design_name, history=self.history,
                      release=self.release, core=self.core)
        kwargs.update(kw)
        return type(self)(**kwargs)

    @property
    def power_nuc(self):
        return self.history.current_params['power']

    def new_core(self) -> Core:
        """Return another core object identical to current core"""
        return deepcopy(self.core)

    def shift_control_height(self, alias: str, height_shift: float) -> "OperationalState":
        """Change the height of the aliased control elements by a given number

        Parameters
        ----------
        alias: str
            Alias to use to get the nodes that should shift.
        height_shift: float
            The amount by which to change the height

        Returns
        -------
        OperationalState
            new OperationalState with the control height changed
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        for path in new_core.aliases[alias][1]:
            shift = Transform(translation=np.array([0, 0, height_shift]))
            new_core[path].transform = shift @ new_core[path].transform
        try:
            current_history_height = self.history.current_params[alias]
        except KeyError:
            current_history_height = 0
        new_history.append({alias: height_shift + current_history_height})
        return self.copy(core=new_core, history=new_history)

    def new_control_height(self, alias: str, height: float) -> "OperationalState":
        """Change the height of the aliased control elements to a given number

        Parameters
        ----------
        alias: str
            The alias of the controls to move.
        height: float
            The new height of the aliased control

        Returns
        -------
        OperationalState
            new OperationalState with the control height changed
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        for path in new_core.aliases[alias][1]:
            current_transform = new_core.transform_of(path)
            z_shift = float(height - current_transform.translation[-1])
            shift = Transform((0., 0., z_shift))
            new_core[path].transform = shift @ new_core[path].transform
        new_history.append({alias: height})
        return self.copy(core=new_core, history=new_history)

    def new_mixture(self, alias: str, mixture: Mixture) -> "OperationalState":
        """Change the mixture in an alias.

        Some control systems are based on changing the materials in some components
        for example dropping a heavy water reflector or injecting absorbing mixture
        to a tank. Such systems are usually second shutdown systems (SSS).
        This method allows to preform such changes in the core configuration.

        Parameters
        ----------
        alias: str
            Alias to change.
        mixture: Mixture
            Mixture to put in the alias paths.

        Returns
        -------
        OperationalState
            A new state, with the changed mixture.

        """
        new_core = self.new_core()
        for path in new_core.aliases[alias][1]:
            new_core[path].mixture = mixture

        new_history = deepcopy(self.history)
        new_history.append({alias: tuple(mixture.isotopes.items())})

        return self.copy(history=new_history, core=new_core)

    def new_temperature(self, temperature: degC,
                        *,
                        to_change: Optional[Filter] = None,
                        change_water_density: bool = True,
                        history_name: str = 'temperature',
                        iswater: Filter = _mostly_water,
                        water_density_strategy: Callable[[float], float] = _H2O) -> "OperationalState":
        """Creates a changed state with all mixtures at a new temperature.
        A changed state where the temperature of all components is set
        to this static value.

        If a change in water density is desired, that is also applied by default,
        but can be turned off with a flag.

        Parameters
        ----------
        temperature: degC
            Temperature for all things to be at.
        to_change: Optional[Filter]
            Filter for the nodes whose mixtures to change
        change_water_density: bool
            Flag for whether water densities should change or not.
        history_name: str
            name given for this state update in the history record
        iswater: Optional[Filter]
            Filter to figure out what components are made out of water.
            Used so water density can change with its temperature.
        water_density_strategy: Callable[[float], float]
            Function used to calculate the water density given temperature.

        Returns
        -------
        OperationalState
         A new state with its temperature changed.

        """

        new_core = self.new_core()
        new_history = deepcopy(self.history)
        _to_change = (lambda x: to_change(*x)) if to_change else None
        for path, node in filter(_to_change, new_core.nodes):
            if node.mixture:
                mixture = node.mixture
                factor = 1.
                if change_water_density and iswater(path, node):
                    factor = water_density_strategy(temperature) / water_density_strategy(mixture.temperature)
                node.mixture = ConcreteMixture(
                    {iso: nd * factor for iso, nd in mixture.items()},
                    temperature, mixture.sab)
        new_history.append({history_name: temperature})
        return self.copy(core=new_core, history=new_history)

    def new_water_temperature(self,
                              temperature: degC, *,
                              history_name: str = 'water_temperature',
                              iswater: Filter = _mostly_water,
                              water_density_strategy: Callable[[float], float] = _H2O) -> "OperationalState":
        """Create a changed state where the water temperature is changed.

        A changed state where the temperature of all water components is set
        to this static value.

        If a change in water density is desired, that is also applied by default,
        but can be turned off with a flag.

        Parameters
        ----------
        temperature: degC
         Temperature for all things to be at.
        history_name: str
         name given for this state update in the history record
        iswater: Filter
         The filter to figure out what components are made out of water.
         Used so water density can change with its temperature.
        water_density_strategy: Callable[[float], float]
            Function used to calculate the water density given temperature.

        Returns
        -------
        OperationalState
         A new state with the temperature of the water components changed.

        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        for _, node in new_core.nodes:
            if iswater(_, node):
                mixture = node.mixture
                factor = water_density_strategy(temperature) / water_density_strategy(mixture.temperature)
                node.mixture = ConcreteMixture(
                    {iso: nd * factor for iso, nd in mixture.items()},
                    temperature, mixture.sab)
        new_history.append({history_name: temperature})
        return self.copy(core=new_core, history=new_history)

    def new_water_density_factor(self, factor: float,
                                 history_name: str = 'water_density_factor',
                                 iswater: Filter = _mostly_water
                                 ) -> "OperationalState":
        """Give a new state with the density of water changed by a factor.

        Parameters
        ----------
        factor: float
         Factor of density to multiply water mixtures by.
        history_name: str
         Name to put in history for this change.
        iswater: Filter
         The Filter to figure out what components are made out of water.

        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)

        for _, node in new_core.nodes:
            if iswater(_, node):
                mixture = node.mixture
                node.mixture = ConcreteMixture(
                    {iso: nd * factor for iso, nd in mixture.items()},
                    mixture.temperature, mixture.sab)

        new_history.append({history_name: factor})
        return self.copy(core=new_core, history=new_history)

    def new_isotope_density(self, densities: dict[ZAID, float],
                            to_change: Filter | None = None
                            ) -> "OperationalState":
        """Give a new state where the density changes.
        Change the density of an isotopes, used for example for boron updates in PWR cores.

        Parameters
        ----------
        densities: dict[ZAID, float]
            dict of the new densities of the isotopes.
        to_change: Filter
            The filter that defines which nodes to change.


        Returns
        -------
        OperationalState
         The state after the change
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        _to_change = (lambda x: to_change(*x)) if to_change else None
        for _, node in filter(_to_change, new_core.nodes):
            if node.mixture:
                mixture = node.mixture
                old = mixture.isotopes
                node.mixture = ConcreteMixture(old | densities,
                                               mixture.temperature, mixture.sab)
        new_history.append(densities)
        return self.copy(history=new_history, core=new_core)

    def new_power(self, power: MW) -> "OperationalState":
        """
        method to change the power of the core

        Parameters
        ----------
        power: Mw
         The new power in Mw

        Returns
        -------
        OperationalState
         The new state with the new power.
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        new_history.append(dict(power=power))
        return self.copy(core=new_core, history=new_history)

    def new_after_scheme(self, scheme: Scheme) -> "OperationalState":
        """
        Apply a mobilization scheme to the core.

        Parameters
        ----------
        scheme: Scheme
         The mobilization scheme

        Returns
        -------
        OperationalState
         The state after the mobilization
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        new_history.append(scheme)
        apply_mobilization(new_core, scheme)
        return self.copy(core=new_core, history=new_history)

    def burnup(self, *,
               mixtures: dict[PurePath, Mixture],
               time: timedelta) -> "OperationalState":
        """Perform a density update after a burnup step.

        Parameters
        ----------
        mixtures: dict[str, Mixture]
            Dict of the new mixtures for each updated node, given by the path of the node.
        time: timedelta
            The duration of the burnup step

        Returns
        -------
        OperationalState
            The updated state.
        """
        new_core = self.new_core()
        new_history = deepcopy(self.history)
        new_history.append(time)
        for path, mixture in mixtures.items():
            new_core[path].mixture = mixture
        return self.copy(history=new_history, core=new_core)

    @property
    def amounts(self) -> dict[Isotope, kg]:
        return parse_amounts(self.core)

    def __repr__(self) -> str:
        return f'Design: {self.design_name}, History={self.history}'

    def __hash__(self) -> int:
        return hash((self.design_name, self.history, self.release))
