from dataclasses import dataclass
from itertools import chain

from coreoperator.mobilization.grid_action import GridAction


@dataclass(frozen=True)
class Scheme:
    """
    A scheme for how to change the placement of rods in a core.
    The actions of the scheme are preformed one after the other.

    """
    actions: tuple[GridAction, ...] = ()

    def __matmul__(self, other: "Scheme"):
        if isinstance(other, Scheme):
            # Safe because this is a dataclass, so it accepts a tuple.
            return type(self)(tuple(chain(self.actions,  # type: ignore
                                          other.actions)))
        return NotImplemented

    def __repr__(self) -> str: return '\n'.join(map(repr, self.actions))
