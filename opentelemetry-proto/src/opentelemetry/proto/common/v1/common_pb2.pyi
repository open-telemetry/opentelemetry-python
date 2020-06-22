# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    List as typing___List,
    NewType as typing___NewType,
    Optional as typing___Optional,
    Text as typing___Text,
    Tuple as typing___Tuple,
    Union as typing___Union,
    cast as typing___cast,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int
builtin___str = str
if sys.version_info < (3,):
    builtin___buffer = buffer
    builtin___unicode = unicode


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class AttributeKeyValue(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    ValueTypeValue = typing___NewType('ValueTypeValue', builtin___int)
    type___ValueTypeValue = ValueTypeValue
    class ValueType(object):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: builtin___int) -> builtin___str: ...
        @classmethod
        def Value(cls, name: builtin___str) -> AttributeKeyValue.ValueTypeValue: ...
        @classmethod
        def keys(cls) -> typing___List[builtin___str]: ...
        @classmethod
        def values(cls) -> typing___List[AttributeKeyValue.ValueTypeValue]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[builtin___str, AttributeKeyValue.ValueTypeValue]]: ...
        STRING = typing___cast(AttributeKeyValue.ValueTypeValue, 0)
        INT = typing___cast(AttributeKeyValue.ValueTypeValue, 1)
        DOUBLE = typing___cast(AttributeKeyValue.ValueTypeValue, 2)
        BOOL = typing___cast(AttributeKeyValue.ValueTypeValue, 3)
    STRING = typing___cast(AttributeKeyValue.ValueTypeValue, 0)
    INT = typing___cast(AttributeKeyValue.ValueTypeValue, 1)
    DOUBLE = typing___cast(AttributeKeyValue.ValueTypeValue, 2)
    BOOL = typing___cast(AttributeKeyValue.ValueTypeValue, 3)
    type___ValueType = ValueType

    key: typing___Text = ...
    type: type___AttributeKeyValue.ValueTypeValue = ...
    string_value: typing___Text = ...
    int_value: builtin___int = ...
    double_value: builtin___float = ...
    bool_value: builtin___bool = ...

    def __init__(self,
        *,
        key : typing___Optional[typing___Text] = None,
        type : typing___Optional[type___AttributeKeyValue.ValueTypeValue] = None,
        string_value : typing___Optional[typing___Text] = None,
        int_value : typing___Optional[builtin___int] = None,
        double_value : typing___Optional[builtin___float] = None,
        bool_value : typing___Optional[builtin___bool] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> AttributeKeyValue: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> AttributeKeyValue: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"bool_value",b"bool_value",u"double_value",b"double_value",u"int_value",b"int_value",u"key",b"key",u"string_value",b"string_value",u"type",b"type"]) -> None: ...
type___AttributeKeyValue = AttributeKeyValue

class StringKeyValue(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    key: typing___Text = ...
    value: typing___Text = ...

    def __init__(self,
        *,
        key : typing___Optional[typing___Text] = None,
        value : typing___Optional[typing___Text] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> StringKeyValue: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> StringKeyValue: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"key",b"key",u"value",b"value"]) -> None: ...
type___StringKeyValue = StringKeyValue

class InstrumentationLibrary(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    name: typing___Text = ...
    version: typing___Text = ...

    def __init__(self,
        *,
        name : typing___Optional[typing___Text] = None,
        version : typing___Optional[typing___Text] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> InstrumentationLibrary: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> InstrumentationLibrary: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"name",b"name",u"version",b"version"]) -> None: ...
type___InstrumentationLibrary = InstrumentationLibrary
