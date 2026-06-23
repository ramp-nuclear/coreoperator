from dataclasses import dataclass, field, replace
from datetime import timedelta
from itertools import takewhile
from typing import Any, ClassVar, Generator, Hashable, Type, TypeVar

try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from ramp_core.serializable import Serializable, deserialize_default
from scipy.constants import day

from coreoperator.mobilization import Scheme

MW = MWD = float


class StateParams(Serializable):
    """A container of operational parameters. Some are required, many are allowed.

    Please use hashable values

    """

    ser_identifier = "StateParams"

    def __init__(self, power: MW, **kwargs: dict[str, Hashable]):
        self.power = power
        self._attrs = kwargs

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, self.todict()

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *_, **__) -> Self:
        return cls(**d)

    def copy(self: Self, **kwargs: dict[str, Hashable]) -> Self:
        """Creates a copy of these parameters, but allows changes.
        Kind of like a dataclass' replace, but with arbitrary keywords.

        """
        kw = self.todict() | kwargs
        return type(self)(**kw)

    def __getitem__(self, item: str):
        return self.power if item == "power" else self._attrs[item]

    def __delitem__(self, key: str):
        if key == "power":
            raise KeyError("Not allowed to delete the power parameter from StateParams")
        del self._attrs[key]

    def __setitem__(self, key: str, value: Hashable):
        if key == "power":
            self.power = value
        else:
            self._attrs[key] = value

    def __iter__(self) -> Generator[tuple[str, Hashable], None, None]:
        yield "power", self.power
        yield from self._attrs.items()

    def __hash__(self):
        return hash(frozenset((key, value) for key, value in self))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.todict() == other.todict()

    def __repr__(self): return str(self.todict())

    def todict(self) -> dict[str, Hashable]:
        return dict(iter(self))


@dataclass(frozen=True)
class OperationalPeriod(Serializable):
    """A segment of time with given operational parameters

    Parameters
    ----------
    params: StateParams
        The operational parameters during this period.
    time: timedelta
        Period length

    """
    params: StateParams
    time: timedelta

    ser_identifier: ClassVar[str] = "OpPeriod"

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, {"params": self.params.serialize(), "time": self.time.total_seconds()}

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        params: StateParams = deserialize_default(d["params"], supported=supported, default=StateParams)
        time = timedelta(seconds=d["time"])
        return cls(params, time)

    def copy(self: Self, 
             params: StateParams | None = None, 
             time: timedelta | None = None
             ) -> Self:
        """Creates a copy of this period with some changes.

        Parameters
        ----------
        params: StateParams
            Parameters to change from the original
        time: timedelta
            Period of time, if period changes.
        """
        pars = self.params.copy(**params.todict()) if params is not None else self.params
        time = time if time is not None else self.time
        return replace(self, params=pars, time=time)

    @property
    def burnup(self) -> MWD:
        return self.params.power * self.time.total_seconds() / day


@dataclass(frozen=True)
class History(Serializable):
    """Historical information about the core.

    Basically a sequentially growing list of steps at piecewise constant parameters.

    """

    steps: list[OperationalPeriod | Scheme] = field(default_factory=list)

    ser_identifier: ClassVar[str] = "OpHistory"

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, {"steps": [step.serialize() for step in self.steps]}

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        steps = [deserialize_default(step, supported=supported) for step in d["steps"]]
        return cls(steps)

    def new_cycle(self: Self, scheme: Scheme) -> Self:
        """Adds a new scheme to the history, marking the beginning of a new cycle.

        Parameters
        ----------
        scheme: Scheme
            The scheme to perform on the core between cycles.

        Returns
        -------
        History
            The new History created by adding the scheme to this history.
            Steps are joined if the last step was a scheme, so we combine them into one bigger scheme.

        """
        cls = type(self)
        if len(self) == 0:
            return cls([scheme])
        last = self.steps[-1]
        if isinstance(last, Scheme):
            return cls(self.steps[:-1] + [last @ scheme])
        return cls(self.steps + [scheme])

    def __len__(self) -> int: return len(self.steps)

    def timestep(self: Self, params: StateParams, time: timedelta) -> Self:
        """Adds a time step to the history, where the core worked with some parameters for some time.

        Parameters
        ----------
        params: StateParams
            The parameters the core worked under during this step
        time: timedelta
            Period of time the core worked under these parameters.

        Returns
        -------
        History
            The new history with the added step. Steps are joined if the last step matched this one's parameters.

        """
        cls = type(self)
        if len(self) == 0:
            return cls([OperationalPeriod(params, time)])
        last = self.steps[-1]
        if isinstance(last, OperationalPeriod) and last.params == params:
            return cls(self.steps[:-1] + [last.copy(time=last.time + time)])
        return cls(self.steps + [OperationalPeriod(params, time)])

    @property
    def current_params(self) -> StateParams | None:
        """Returns the last known parameters, or None if there are none.

        """
        for step in self.steps[::-1]:
            if isinstance(step, OperationalPeriod):
                return step.params
        else:
            return None

    @property
    def cycles(self) -> int:
        """The number of cycles in the history"""
        return sum((1 for step in self.steps if isinstance(step, Scheme)))

    @property
    def cycle_burnup(self) -> MWD:
        """The amount of burnup since the start of this cycle"""
        cycle = takewhile(lambda x: isinstance(x, OperationalPeriod), self.steps[::-1])
        return sum((step.burnup for step in cycle))

    @property
    def cycle_time(self) -> timedelta:
        cycle = takewhile(lambda x: isinstance(x, OperationalPeriod), self.steps[::-1])
        return sum((step.time for step in cycle), timedelta(0))

    def __repr__(self) -> str:
        return f"Cycles: {self.cycles}, Burnup: {self.cycle_burnup:.3f} MWD"

    def __hash__(self) -> int:
        return hash(tuple(self.steps))

