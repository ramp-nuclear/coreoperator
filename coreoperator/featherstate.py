import pickle
import zlib
from typing import Type, TypeVar, Literal, Any
try:
    from typing import Self
except ImportError:
    Self = TypeVar("Self")

from coremaker.core import Core
from .operational_state import OperationalState

Zlib_Compression = Literal[-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
DEFAULT_COMPRESSION = 2 # A sensible default, fast and still has an effect for us


class FeatherState(OperationalState):
    """An OperationalState that takes less space in memory and is much easier to
    transmit over the wire.

    This comes at the cost of slightly less comfortable ergonomics, because one
    cannot directly edit `state.core` and has to explicitly reset the core with
    a setter method to make changes stick.
    To make the ergonomics similar, we made OperationalState similarly complex,
    but deem the tradeoff to be worth the trouble.

    """

    ser_identifier = "FeatherState"
    __zcore: bytes

    def __init__(self, *, compression_level: Zlib_Compression = DEFAULT_COMPRESSION, **kw):
        """
        
        Parameters
        ----------
        compression_level: Zlib_Compression
            The compression level to use. See the `zlib` standard library documentation for details.
            Defaults to a fast compression that still has a significant impact. Subject to change.
        kw:
            Keywords used to make an OperationalState. See that class for details.

        """
        self.compression_level = compression_level
        super().__init__(**kw)

    def serialize(self) -> tuple[str, dict[str, Any]]:
        parent_serialized_data = super().serialize()[1]
        parent_serialized_data["compression"] = self.compression_level
        return self.ser_identifier, parent_serialized_data

    @classmethod
    def deserialize(cls: Type[Self], d: dict[str, Any], *args, **kwargs) -> Self:
        compression = d.pop("compression")
        return cls.from_state(super().deserialize(d=d, *args, **kwargs), compression_level=compression)

    @classmethod
    def from_state(cls: Type[Self], 
                   state: OperationalState,
                   compression_level: Zlib_Compression = DEFAULT_COMPRESSION,
                   ) -> Self:
        """Creates a FeatherState from an OperationalState

        Parameters
        ----------
        state: OperationalState
            The OperationalState to compress
        compression_level: Zlib_Compression
            The compression level to use. See the `zlib` standard library documentation for details.

        """
        if isinstance(state, FeatherState):
            state.compression_level = compression_level
            return state
        return cls(**state.as_dict(), compression_level=compression_level)

    @property
    def core(self) -> Core:
        return pickle.loads(zlib.decompress(self.__zcore))

    @core.setter
    def core(self, core):
        self.__zcore = zlib.compress(pickle.dumps(core), self.compression_level)

    @property
    def _core(self) -> Core:
        return self.core

