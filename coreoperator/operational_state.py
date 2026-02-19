from copy import deepcopy
from datetime import timedelta
from pathlib import PurePath
from typing import Optional, Callable, TypeVar, Any, Type
try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

import numpy as np
from coremaker.amounts import parse_amounts
from coremaker.materials.mixture import Mixture as ConcreteMixture
from coremaker.materials.water import _H2O
from coremaker.protocols.core import Core
from coremaker.protocols.mixture import Mixture
from coremaker.protocols.node import NodeLike
from coremaker.transform import Transform
from isotopes import Isotope, H, O, ZAID
from ramp_core.serializable import Serializable, deserialize_default

from coreoperator.history import History, StateParams
from coreoperator.mobilization import Scheme

days = float
MW = MWD = float
degC = float
kg = float
Filter = Callable[[PurePath, NodeLike], bool]


def _mostly_water(_, node: NodeLike, fraction: float = 0.5) -> bool:
    """Returns true if the water's atom fraction in the material is bigger 
    than some threshold.

    """
    if not node.mixture:
        return False
    mixture = node.mixture
    total = sum(mixture.isotopes.values())
    ho = {H.Z, O.Z}
    ho_total = sum(value for iso, value in mixture.items() if iso.Z in ho)
    return ho <= {x.Z for x in mixture.keys()} and ho_total > fraction * total


class OperationalState(Serializable):
    """This class represents a loosely defined reactor's core state.
    """

    ser_identifier = "State"
    __core: Core

    def __init__(self, *, 
                 params: StateParams,
                 history: History | None = None,
                 tags: set[str],
                 core: Core):
        self.params = params
        self.history = history or History()
        self.tags = tags
        self.core = core

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, {"params": self.params.serialize(),
                                     "history": self.history.serialize(),
                                     "tags": list(self.tags),
                                     "core": self._core.serialize(),
                                     }

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        params = deserialize_default(d["params"], supported=supported, default=StateParams)
        history = deserialize_default(d["history"], supported=supported, default=History)
        tags = set(d["tags"])
        core = deserialize_default(d["core"], supported=supported)
        return cls(params=params, history=history, tags=tags, core=core)

    @property
    def core(self) -> Core:
        """Returns a copy of the saved core, because we want people to not
        edit the core directly. 

        This ensures that something like FeatherState can have the same API,
        because any changes to the core has to follow the pattern:
        .. code-block:: python
            core = state.core
            ...
            state.core = core

        We can still do faster operations by calling self._core, but outside
        users who should not know of these implementation details don't know
        that they can do that, and will likely not shoot themselves in the foot
        by assuming different APIs for OperationalState and FeatherState.

        """
        return deepcopy(self._core)

    @core.setter
    def core(self, core: Core):
        self.__core = core

    @property
    def _core(self) -> Core:
        """Gets the core in the fastest way possible, but read-only.

        One should not expect that changing this object would affect the original
        state, even if it does under some temporary implementation.

        """
        return self.__core

    def as_dict(self, skip: frozenset[str] = frozenset()) -> dict:
        """Returns the data stores in this object as a dict.

        This dict can then be used to recreate the object using 
        `state = OperationalState(**d)`.

        """
        attrs = dict(params="params", history="history", tags="tags", core="_core")
        return {key: getattr(self, attr) for key, attr in attrs.items() 
                if key not in skip}

    def copy(self, **kw) -> Self:
        """Return a copy of current operational state with modifications
        """
        kwargs = self.as_dict(skip=frozenset(kw.keys())) | kw
        return type(self)(**kwargs)

    @property
    def power_nuc(self) -> MW:
        """Return the nuclear power of the core at its operational state"""
        return self.params.power

    def shift_control_height(self: Self, alias: str, height_shift: float) -> Self:
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
        new_core = self.core
        for path in new_core.aliases[alias][1]:
            shift = Transform(translation=np.array([0, 0, height_shift]))
            new_core[path].transform = shift @ new_core[path].transform
        try:
            current_history_height = self.params[alias]
        except KeyError:
            current_history_height = 0
        return self.copy(core=new_core, params=self.params.copy(**{alias: height_shift + current_history_height}))

    def new_control_height(self: Self, alias: str, height: float) -> Self:
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
        new_core = self.core
        for path in new_core.aliases[alias][1]:
            current_transform = new_core.transform_of(path)
            z_shift = height - current_transform.translation.item(-1)
            shift = Transform((0., 0., z_shift))
            new_core[path].transform = shift @ new_core[path].transform
        return self.copy(core=new_core, params=self.params.copy(**{alias: height}))

    def new_mixture(self: Self, alias: str, mixture: Mixture) -> Self:
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
            The mixture to put in the alias paths.

        Returns
        -------
        OperationalState
            A new state, with the changed mixture.

        """
        new_core = self.core
        for path in new_core.aliases[alias][1]:
            new_core[path].mixture = mixture
        return self.copy(core=new_core)

    def new_temperature(self: Self, 
                        temperature: degC,
                        *,
                        to_change: Optional[Filter] = None,
                        change_water_density: bool = True,
                        iswater: Filter = _mostly_water,
                        water_density_strategy: Callable[[float], float] = _H2O) -> Self:
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
            Flag for whether water densities should change.
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

        new_core = self.core
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
        return self.copy(core=new_core)

    def new_water_temperature(self: Self,
                              temperature: degC, *,
                              iswater: Filter = _mostly_water,
                              water_density_strategy: Callable[[float], float] = _H2O) -> Self:
        """Create a changed state where the water temperature is changed.

        A changed state where the temperature of all water components is set
        to this static value.

        Parameters
        ----------
        temperature: degC
            Temperature for all things to be at.
        iswater: Filter
            The filter to figure out what components are made out of water.
        water_density_strategy: Callable[[float], float]
            Function used to calculate the water density given temperature.

        Returns
        -------
        OperationalState
            A new state with the temperature of the water components changed.

        """
        return self.new_temperature(temperature=temperature,
                                    to_change=iswater,
                                    iswater=iswater,
                                    water_density_strategy=water_density_strategy
                                    )

    def new_water_density_factor(self: Self, 
                                 factor: float,
                                 iswater: Filter = _mostly_water
                                 ) -> Self:
        """Give a new state with the density of water changed by a factor.

        Parameters
        ----------
        factor: float
            Factor of density to multiply water mixtures by.
        iswater: Filter
            The Filter to figure out what components are made out of water.

        """
        new_core = self.core

        for _, node in new_core.nodes:
            if iswater(_, node):
                mixture = node.mixture
                node.mixture = ConcreteMixture(
                    {iso: nd * factor for iso, nd in mixture.items()},
                    mixture.temperature, mixture.sab)
        return self.copy(core=new_core)

    def new_isotope_density(self: Self, 
                            densities: dict[ZAID, float],
                            to_change: Filter | None = None
                            ) -> Self:
        """Give a new state where the density changes.
        Change the density of an isotopes, used for example for boron updates 
        in PWR cores.

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
        new_core = self.core
        _to_change = (lambda x: to_change(*x)) if to_change else None
        for _, node in filter(_to_change, new_core.nodes):
            if node.mixture:
                mixture = node.mixture
                old = mixture.isotopes
                node.mixture = ConcreteMixture(old | densities,
                                               mixture.temperature, mixture.sab)
        return self.copy(core=new_core)

    def new_power(self: Self, power: MW) -> Self:
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
        return self.copy(core=self.core, params=self.params.copy(power=power))

    def new_after_scheme(self: Self, scheme: Scheme) -> Self:
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
        new_core = self.core
        scheme.apply(new_core)
        return self.copy(core=new_core, history=self.history.new_cycle(scheme))

    def burnup(self: Self, *,
               mixtures: dict[PurePath, Mixture],
               time: timedelta) -> Self:
        """Perform a density update after a burnup step.

        Parameters
        ----------
        mixtures: dict[str, Mixture]
            Dict of the new mixtures for each updated node, given by the path 
            of the node.
        time: timedelta
            The duration of the burnup step

        Returns
        -------
        OperationalState
            The updated state.
        """
        new_core = self.core
        for path, mixture in mixtures.items():
            new_core[path].mixture = mixture
        return self.copy(history=self.history.timestep(self.params, time), 
                         core=new_core)

    @property
    def amounts(self) -> dict[Isotope, kg]:
        """Return the total mass of each isotope in the state's core."""
        return parse_amounts(self._core)

    def __repr__(self) -> str:
        return f"Tags: {self.tags}, History={self.history}" 

    def __hash__(self) -> int:
        return hash((self._core, self.params, self.history))

    def __eq__(self: Self, other: Self) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        if (self.history != other.history) or (self.params != other.params):
            return False
        return self._core == other._core

