from abc import ABC, abstractstaticmethod
from typing import Generic, Sequence, TypeVar

SDKDataT = TypeVar("SDKDataT")
ExportServiceRequestT = TypeVar("ExportServiceRequestT")


class _ProtobufEncoderMixin(ABC, Generic[SDKDataT, ExportServiceRequestT]):
    @classmethod
    def serialize(cls, sdk_data: Sequence[SDKDataT]) -> str:
        return cls.encode(sdk_data).SerializeToString()

    @abstractstaticmethod
    def encode(sdk_data: Sequence[SDKDataT]) -> ExportServiceRequestT:
        pass
