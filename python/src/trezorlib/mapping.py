# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import io
import typing as t
from types import ModuleType

from typing_extensions import Self

from . import messages, protobuf

T = t.TypeVar("T")
MT = t.TypeVar("MT", bound=protobuf.MessageType)


class ProtobufMapping:
    """Mapping of protobuf classes to Python classes"""

    def __init__(self) -> None:
        self.type_to_class: t.Dict[int, t.Type[protobuf.MessageType]] = {}
        self.class_to_type_override: t.Dict[t.Type[protobuf.MessageType], int] = {}

    def register(
        self,
        msg_class: t.Type[protobuf.MessageType],
        msg_wire_type: int | None = None,
    ) -> None:
        """Register a Python class as a protobuf type.

        If `msg_wire_type` is specified, it is used instead of the internal value in
        `msg_class`.

        Any existing registrations are overwritten.
        """
        if msg_wire_type is not None:
            self.class_to_type_override[msg_class] = msg_wire_type
        elif msg_class.MESSAGE_WIRE_TYPE is None:
            raise ValueError("Cannot register class without wire type")
        else:
            msg_wire_type = msg_class.MESSAGE_WIRE_TYPE

        self.type_to_class[msg_wire_type] = msg_class

    def encode(self, msg: protobuf.MessageType) -> tuple[int, bytes]:
        """Serialize a Python protobuf class.

        Returns the message wire type and a byte representation of the protobuf message.
        """
        wire_type = self.class_to_type_override.get(type(msg), msg.MESSAGE_WIRE_TYPE)
        if wire_type is None:
            raise ValueError(
                f'Cannot encode class "{type(msg).__name__}" without wire type'
            )

        buf = io.BytesIO()
        protobuf.dump_message(buf, msg)
        return wire_type, buf.getvalue()

    def encode_without_wire_type(self, msg: protobuf.MessageType) -> bytes:
        """Serialize a Python protobuf class.

        Returns the byte representation of the protobuf message.
        """

        buf = io.BytesIO()
        protobuf.dump_message(buf, msg)
        return buf.getvalue()

    def decode(self, msg_wire_type: int, msg_bytes: bytes) -> protobuf.MessageType:
        """Deserialize a protobuf message into a Python class."""
        cls = self.type_to_class[msg_wire_type]
        buf = io.BytesIO(msg_bytes)
        return protobuf.load_message(buf, cls)

    def decode_without_wire_type(
        self, message_type: type[MT], msg_bytes: bytes
    ) -> protobuf.MessageType:
        """Deserialize a protobuf message into a Python class."""
        cls = message_type
        buf = io.BytesIO(msg_bytes)
        return protobuf.load_message(buf, cls)

    @classmethod
    def from_module(cls, module: ModuleType) -> Self:
        """Generate a mapping from a module.

        The module must have a `MessageType` enum that specifies individual wire types.
        """
        mapping = cls()

        message_types = getattr(module, "MessageType")
        thp_message_types = getattr(module, "ThpMessageType")

        for entry in (*message_types, *thp_message_types):
            msg_class = getattr(module, entry.name, None)
            if msg_class is None:
                raise ValueError(
                    f"Implementation of protobuf message '{entry.name}' is missing"
                )

            if msg_class.MESSAGE_WIRE_TYPE != entry.value:
                raise ValueError(
                    f"Inconsistent wire type and MessageType record for '{entry.name}'"
                )

            mapping.register(msg_class)

        return mapping


DEFAULT_MAPPING = ProtobufMapping.from_module(messages)
