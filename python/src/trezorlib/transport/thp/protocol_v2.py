from __future__ import annotations

import logging
import os
import typing as t
from binascii import hexlify
from enum import IntEnum

from noise.connection import Keypair, NoiseConnection

from ... import exceptions, messages, protobuf
from ...mapping import ProtobufMapping
from .. import Transport
from ..thp import checksum, thp_io
from ..thp.checksum import CHECKSUM_LENGTH
from ..thp.message_header import MessageHeader
from . import control_byte
from .channel import Channel

LOG = logging.getLogger(__name__)

DEFAULT_SESSION_ID: int = 0

if t.TYPE_CHECKING:
    pass
MT = t.TypeVar("MT", bound=protobuf.MessageType)


class TrezorState(IntEnum):
    UNPAIRED = 0x00
    PAIRED = 0x01


class ProtocolV2Channel(Channel):
    channel_id: int
    sync_bit_send: int
    sync_bit_receive: int
    handshake_hash: bytes
    device_properties: bytes

    _has_valid_channel: bool = False
    _features: messages.Features | None = None
    trezor_state: int = TrezorState.UNPAIRED

    def __init__(
        self,
        transport: Transport,
        mapping: ProtobufMapping,
        credential: bytes | None = None,
        prepare_channel_without_pairing: bool = True,
    ) -> None:
        super().__init__(transport, mapping)
        if prepare_channel_without_pairing:
            self.trezor_state = self.prepare_channel_without_pairing(
                credential=credential
            )

    def get_channel(self) -> ProtocolV2Channel:
        if not self._has_valid_channel:
            raise RuntimeError("Channel is invalidated")
        return self

    def read(self, session_id: int, timeout: float | None = None) -> t.Any:
        sid, msg_type, msg_data = self.read_and_decrypt(timeout)
        if sid != session_id:
            raise Exception(
                f"Received messsage on a different session (expected/received): ({session_id}/{sid}) "
            )
        return self.mapping.decode(msg_type, msg_data)

    def write(self, session_id: int, msg: t.Any) -> None:
        msg_type, msg_data = self.mapping.encode(msg)
        self._encrypt_and_write(session_id, msg_type, msg_data)

    def get_features(self) -> messages.Features:
        if not self._has_valid_channel:
            raise RuntimeError("Channel is invalidated")
        if self._features is None:
            self.update_features()
        assert self._features is not None
        return self._features

    def update_features(self, timeout: float | None = None) -> None:
        message = messages.GetFeatures()
        message_type, message_data = self.mapping.encode(message)
        self.session_id: int = DEFAULT_SESSION_ID
        self._encrypt_and_write(DEFAULT_SESSION_ID, message_type, message_data)
        header, _payload = self._read_until_valid_crc_check()
        if not header.is_ack():
            raise exceptions.TrezorException("ACK expected")
        _, msg_type, msg_data = self.read_and_decrypt(timeout)
        features = self.mapping.decode(msg_type, msg_data)
        if not isinstance(features, messages.Features):
            raise exceptions.TrezorException("Unexpected response to GetFeatures")
        self._features = features

    def _send_message(
        self,
        message: protobuf.MessageType,
        session_id: int = DEFAULT_SESSION_ID,
    ):
        message_type, message_data = self.mapping.encode(message)
        self._encrypt_and_write(session_id, message_type, message_data)
        self._read_ack()

    def _read_message(self, message_type: type[MT], timeout: float | None = None) -> MT:
        _, msg_type, msg_data = self.read_and_decrypt(timeout)
        msg = self.mapping.decode(msg_type, msg_data)
        assert isinstance(msg, message_type)
        return msg

    def prepare_channel_without_pairing(self, credential: bytes | None = None) -> int:
        self._reset_sync_bits()
        self._do_channel_allocation()
        return self._do_handshake(credential=credential)

    def _reset_sync_bits(self) -> None:
        self.sync_bit_send = 0
        self.sync_bit_receive = 0

    def _do_channel_allocation(self) -> None:
        channel_allocation_nonce = os.urandom(8)
        self._send_channel_allocation_request(channel_allocation_nonce)
        cid, dp = self._read_channel_allocation_response(channel_allocation_nonce)
        self.channel_id = cid
        self.device_properties = dp

    def _send_channel_allocation_request(self, nonce: bytes):
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            MessageHeader.get_channel_allocation_request_header(12),
            nonce,
        )

    def _read_channel_allocation_response(
        self,
        expected_nonce: bytes,
    ) -> tuple[int, bytes]:
        header, payload = self._read_until_valid_crc_check()
        if not self._is_valid_channel_allocation_response(
            header, payload, expected_nonce
        ):
            raise Exception("Invalid channel allocation response.")

        channel_id = int.from_bytes(payload[8:10], "big")
        device_properties = payload[10:]
        return (channel_id, device_properties)

    def _init_noise(
        self,
        randomness_static: bytes | None = None,
        randomness_ephemeral: bytes | None = None,
    ) -> None:
        randomness_static = randomness_static or os.urandom(32)
        self._noise = NoiseConnection.from_name(b"Noise_XX_25519_AESGCM_SHA256")
        self._noise.set_as_initiator()
        self._noise.set_keypair_from_private_bytes(Keypair.STATIC, randomness_static)
        if randomness_ephemeral is not None:
            self._noise.set_keypair_from_private_bytes(
                Keypair.EPHEMERAL, randomness_ephemeral
            )
        prologue = bytes(self.device_properties)
        self._noise.set_prologue(prologue)
        self._noise.start_handshake()

    def _do_handshake(
        self,
        credential: bytes | None = None,
        host_static_randomness: bytes | None = None,
        host_ephemeral_randomness: bytes | None = None,
    ) -> int:

        randomness_static = host_static_randomness or os.urandom(32)
        if host_ephemeral_randomness is not None:
            self._init_noise(randomness_static, host_ephemeral_randomness)
        else:
            self._init_noise(randomness_static)
        self._send_handshake_init_request()
        self._read_ack()
        self._read_handshake_init_response()
        self._send_handshake_completion_request(
            credential,
        )
        self._read_ack()
        return self._read_handshake_completion_response()

    def _send_handshake_init_request(self) -> None:
        ha_init_req_header = MessageHeader(0, self.channel_id, 36)
        host_ephemeral_pubkey = self._noise.write_message()

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, ha_init_req_header, host_ephemeral_pubkey
        )

    def _read_handshake_init_response(self) -> bytes:
        header, payload = self._read_until_valid_crc_check()
        self._send_ack_bit(bit=0)

        if control_byte.is_error(header.ctrl_byte):
            if payload == b"\x05":
                raise exceptions.DeviceLockedException()
            else:
                raise exceptions.ThpError(_get_error_from_int(payload[0]))

        if not header.is_handshake_init_response():
            LOG.error("Received message is not a valid handshake init response message")
        self._noise.read_message(payload)
        return payload

    def _send_handshake_completion_request(
        self,
        credential: bytes | None = None,
    ) -> None:
        # TODO implement key recognition
        # print(
        #     "TREZOR's static pubkey:\n",
        #     self.noise.noise_protocol.handshake_state.rs.public.public_bytes_raw(),
        # )

        msg_data = self.mapping.encode_without_wire_type(
            messages.ThpHandshakeCompletionReqNoisePayload(
                host_pairing_credential=credential,
            )
        )
        message2 = self._noise.write_message(payload=msg_data)

        ha_completion_req_header = MessageHeader(
            0x12,
            self.channel_id,
            len(message2) + CHECKSUM_LENGTH,
        )
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            ha_completion_req_header,
            message2,  # encrypted_host_static_pubkey + encrypted_payload,
        )
        self.handshake_hash = self._noise.get_handshake_hash()

    def _read_handshake_completion_response(self) -> int:
        # Read handshake completion response, ignore payload as we do not care about the state
        header, data = self._read_until_valid_crc_check()
        if not header.is_handshake_comp_response():
            LOG.error("Received message is not a valid handshake completion response")
            if control_byte.is_error(header.ctrl_byte):
                raise exceptions.ThpError(_get_error_from_int(data[0]))
        trezor_state = self._noise.decrypt(bytes(data))
        assert trezor_state == b"\x00" or trezor_state == b"\x01"
        self._send_ack_bit(bit=1)
        return int.from_bytes(trezor_state, "big")

    def _read_ack(self):
        header, payload = self._read_until_valid_crc_check()
        if not header.is_ack() or len(payload) > 0:
            LOG.error("Received message is not a valid ACK")
            if control_byte.is_error(header.ctrl_byte):
                raise exceptions.ThpError(_get_error_from_int(payload[0]))

    def _send_ack_bit(self, bit: int):
        if bit not in (0, 1):
            raise ValueError("Invalid ACK bit")
        LOG.debug(f"sending ack {bit}")
        ctrl_byte = 0x20 if bit == 0 else 0x28
        header = MessageHeader(ctrl_byte, self.channel_id, 4)
        thp_io.write_payload_to_wire_and_add_checksum(self.transport, header, b"")

    def _encrypt_and_write(
        self,
        session_id: int,
        message_type: int,
        message_data: bytes,
        ctrl_byte: int | None = None,
    ) -> None:

        if ctrl_byte is None:
            ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(0x04, self.sync_bit_send)
            self.sync_bit_send = 1 - self.sync_bit_send

        sid = session_id.to_bytes(1, "big")
        msg_type = message_type.to_bytes(2, "big")
        data = sid + msg_type + message_data

        encrypted_message = self._noise.encrypt(data)

        header = MessageHeader(
            ctrl_byte, self.channel_id, len(encrypted_message) + CHECKSUM_LENGTH
        )

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, header, encrypted_message
        )

    def read_and_decrypt(
        self, timeout: float | None = None
    ) -> t.Tuple[int, int, bytes]:
        while True:
            header, raw_payload = self._read_until_valid_crc_check(timeout)
            if header.cid != self.channel_id:
                # Received message from different channel - discard
                continue
            if control_byte.is_ack(header.ctrl_byte):
                continue
            if control_byte.is_error(header.ctrl_byte):
                raise exceptions.ThpError(_get_error_from_int(raw_payload[0]))
            if not header.is_encrypted_transport():
                LOG.error(
                    "Trying to decrypt not encrypted message! ("
                    + hexlify(header.to_bytes_init() + raw_payload).decode()
                    + ")"
                )

            LOG.debug(
                "--> Get sequence bit %d %s %s",
                control_byte.get_seq_bit(header.ctrl_byte),
                "from control byte",
                hexlify(header.ctrl_byte.to_bytes(1, "big")).decode(),
            )
            self._send_ack_bit(bit=control_byte.get_seq_bit(header.ctrl_byte))

            message = self._noise.decrypt(bytes(raw_payload))
            session_id = message[0]
            message_type = message[1:3]
            message_data = message[3:]
            return (
                session_id,
                int.from_bytes(message_type, "big"),
                message_data,
            )

    def _read_until_valid_crc_check(
        self, timeout: float | None = None
    ) -> t.Tuple[MessageHeader, bytes]:
        if timeout is None:
            timeout = self._DEFAULT_READ_TIMEOUT

        is_valid = False
        header, payload, chksum = thp_io.read(self.transport, timeout)
        while not is_valid:
            is_valid = checksum.is_valid(chksum, header.to_bytes_init() + payload)
            if not is_valid:
                LOG.error(
                    "Received a message with an invalid checksum:"
                    + hexlify(header.to_bytes_init() + payload + chksum).decode()
                )
                header, payload, chksum = thp_io.read(self.transport, timeout)

        return header, payload

    def _is_valid_channel_allocation_response(
        self, header: MessageHeader, payload: bytes, original_nonce: bytes
    ) -> bool:
        if not header.is_channel_allocation_response():
            LOG.error("Received message is not a channel allocation response")
            return False
        if len(payload) < 10:
            LOG.error("Invalid channel allocation response payload")
            return False
        if payload[:8] != original_nonce:
            LOG.error("Invalid channel allocation response payload (nonce mismatch)")
            return False
        return True


def _get_error_from_int(error_code: int) -> str:
    # TODO FIXME improve this (ThpErrorType)
    if error_code == 1:
        return "TRANSPORT BUSY"
    if error_code == 2:
        return "UNALLOCATED CHANNEL"
    if error_code == 3:
        return "DECRYPTION FAILED"
    if error_code == 4:
        return "INVALID DATA"
    if error_code == 5:
        return "DEVICE LOCKED"
    raise Exception("Not Implemented error case")
