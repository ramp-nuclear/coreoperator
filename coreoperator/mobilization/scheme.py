from dataclasses import dataclass
from itertools import chain
from typing import Any, ClassVar, Type, TypeVar

try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from coremaker.protocols.core import Core
from ramp_core.serializable import Serializable, deserialize_default

from coreoperator.mobilization.grid_action import GridAction


@dataclass(frozen=True)
class Scheme(Serializable):
    """
    A scheme for how to change the placement of rods in a core.
    The actions of the scheme are preformed one after the other.

    """

    actions: tuple[GridAction, ...] = ()

    ser_identifier: ClassVar[str] = "Scheme"

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return self.ser_identifier, {"actions": [act.serialize() for act in self.actions]}

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *, supported: dict[str, Type[Serializable]]) -> Self:
        actions: tuple[GridAction, ...] = tuple(deserialize_default(act, supported=supported)
                                                for act in d["actions"])
        return cls(actions)

    def apply(self, core: Core) -> None:
        for action in self.actions:
            action.apply(core.grid)

    def __matmul__(self, other: "Scheme"):
        if isinstance(other, Scheme):
            # Safe because this is a dataclass, so it accepts a tuple.
            return type(self)(tuple(chain(self.actions,  # type: ignore
                                          other.actions)))
        return NotImplemented

    def __repr__(self) -> str: return '\n'.join(map(repr, self.actions))
