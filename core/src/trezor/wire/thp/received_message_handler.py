import ustruct
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from storage.cache_thp import (
    KEY_LENGTH,
    SESSION_ID_LENGTH,
    TAG_LENGTH,
    update_channel_last_used,
    update_session_last_used,
)
from trezor import config, loop, protobuf, utils
from trezor.enums import FailureType
from trezor.messages import Failure
from trezor.wire.thp import memory_manager

from .. import message_handler
from ..errors import DataError
from ..protocol_common import Message
from . import (
    ACK_MESSAGE,
    HANDSHAKE_COMP_RES,
    HANDSHAKE_INIT_RES,
    ChannelState,
    PacketHeader,
    SessionState,
    ThpDecryptionError,
    ThpDeviceLockedError,
    ThpError,
    ThpErrorType,
    ThpInvalidDataError,
    ThpUnallocatedChannelError,
    ThpUnallocatedSessionError,
)
from . import alternating_bit_protocol as ABP
from . import checksum, control_byte, get_encoded_device_properties, session_manager
from .checksum import CHECKSUM_LENGTH
from .crypto import PUBKEY_LENGTH, Handshake
from .session_context import SeedlessSessionContext
from .writer import (
    INIT_HEADER_LENGTH,
    MESSAGE_TYPE_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ThpHandshakeCompletionReqNoisePayload

    from .channel import Channel

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

_TREZOR_STATE_UNPAIRED = b"\x00"
_TREZOR_STATE_PAIRED = b"\x01"
_TREZOR_STATE_PAIRED_AUTOCONNECT = b"\x02"


async def handle_received_message(
    ctx: Channel, message_buffer: utils.BufferType
) -> None:
    """Handle a message received from the channel."""

    if __debug__:
        log.debug(__name__, "handle_received_message", iface=ctx.iface)
        # TODO remove after performance tests are done
        # try:
        #     import micropython

        #     print("micropython.mem_info() from received_message_handler.py")
        #     micropython.mem_info()
        #     print("Allocation count:", micropython.alloc_count())
        # except AttributeError:
        #     print(
        #         "To show allocation count, create the build with TREZOR_MEMPERF=1"
        #     )
    ctrl_byte, _, payload_length = ustruct.unpack(">BHH", message_buffer)
    message_length = payload_length + INIT_HEADER_LENGTH

    _check_checksum(message_length, message_buffer)

    # Synchronization process
    seq_bit = control_byte.get_seq_bit(ctrl_byte)
    ack_bit = control_byte.get_ack_bit(ctrl_byte)
    if __debug__:
        log.debug(
            __name__,
            "handle_completed_message - seq bit of message: %d, ack bit of message: %d",
            seq_bit,
            ack_bit,
            iface=ctx.iface,
        )
    # 0: Update "last-time used"
    update_channel_last_used(ctx.channel_id)

    # 1: Handle ACKs
    if control_byte.is_ack(ctrl_byte):
        await handle_ack(ctx, ack_bit)
        return

    if _should_have_ctrl_byte_encrypted_transport(
        ctx
    ) and not control_byte.is_encrypted_transport(ctrl_byte):
        raise ThpError("Message is not encrypted. Ignoring")

    # 2: Handle message with unexpected sequential bit
    if seq_bit != ABP.get_expected_receive_seq_bit(ctx.channel_cache):
        if __debug__:
            log.debug(
                __name__,
                "Received message with an unexpected sequential bit",
                iface=ctx.iface,
            )
        await _send_ack(ctx, ack_bit=seq_bit)
        raise ThpError("Received message with an unexpected sequential bit")

    # 3: Send ACK in response
    await _send_ack(ctx, ack_bit=seq_bit)

    ABP.set_expected_receive_seq_bit(ctx.channel_cache, 1 - seq_bit)

    try:
        _handle_message_to_app_or_channel(
            ctx, payload_length, message_length, ctrl_byte
        )
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await ctx.write(error_message, e.session_id)
    except ThpUnallocatedChannelError:
        await ctx.write_error(ThpErrorType.UNALLOCATED_CHANNEL)
        ctx.clear()
    except ThpDecryptionError:
        await ctx.write_error(ThpErrorType.DECRYPTION_FAILED)
        ctx.clear()
    except ThpInvalidDataError:
        await ctx.write_error(ThpErrorType.INVALID_DATA)
        ctx.clear()
    except ThpDeviceLockedError:
        await ctx.write_error(ThpErrorType.DEVICE_LOCKED)

    if __debug__:
        log.debug(__name__, "handle_received_message - end", iface=ctx.iface)


def _send_ack(ctx: Channel, ack_bit: int) -> Awaitable[None]:
    ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ACK_MESSAGE, ack_bit)
    header = PacketHeader(ctrl_byte, ctx.get_channel_id_int(), CHECKSUM_LENGTH)
    if __debug__:
        log.debug(
            __name__,
            "Writing ACK message to a channel with cid: %s, ack_bit: %d",
            hexlify_if_bytes(ctx.channel_id),
            ack_bit,
            iface=ctx.iface,
        )
    return write_payload_to_wire_and_add_checksum(ctx.iface, header, b"")


def _check_checksum(message_length: int, message_buffer: utils.BufferType) -> None:
    if __debug__:
        log.debug(__name__, "check_checksum")
    if not checksum.is_valid(
        checksum=message_buffer[message_length - CHECKSUM_LENGTH : message_length],
        data=memoryview(message_buffer)[: message_length - CHECKSUM_LENGTH],
    ):
        if __debug__:
            log.debug(__name__, "Invalid checksum, ignoring message.")
        raise ThpError("Invalid checksum, ignoring message.")


async def handle_ack(ctx: Channel, ack_bit: int) -> None:
    if not ABP.is_ack_valid(ctx.channel_cache, ack_bit):
        return
    # ACK is expected and it has correct sync bit
    if __debug__:
        log.debug(
            __name__,
            "Received ACK message with correct ack bit",
            iface=ctx.iface,
        )
    if ctx.transmission_loop is not None:
        ctx.transmission_loop.stop_immediately()
        if __debug__:
            log.debug(__name__, "Stopped transmission loop", iface=ctx.iface)
    elif __debug__:
        log.debug(__name__, "Transmission loop was not stopped!", iface=ctx.iface)

    ABP.set_sending_allowed(ctx.channel_cache, True)

    if ctx.write_task_spawn is not None:
        if __debug__:
            log.debug(
                __name__,
                'Control to "write_encrypted_payload_loop" task',
                iface=ctx.iface,
            )
        await ctx.write_task_spawn
        # Note that no the write_task_spawn could result in loop.clear(),
        # which will result in termination of this function - any code after
        # this await might not be executed


def _handle_message_to_app_or_channel(
    ctx: Channel,
    payload_length: int,
    message_length: int,
    ctrl_byte: int,
) -> None:
    state = ctx.get_channel_state()

    if state == ChannelState.ENCRYPTED_TRANSPORT:
        return _handle_state_ENCRYPTED_TRANSPORT(ctx, message_length)

    if state == ChannelState.TH1:
        return _handle_state_TH1(ctx, payload_length, message_length, ctrl_byte)

    if state == ChannelState.TH2:
        return _handle_state_TH2(ctx, message_length, ctrl_byte)

    if _is_channel_state_pairing(state):
        return _handle_pairing(ctx, message_length)

    raise ThpError("Unimplemented channel state")


def _handle_state_TH1(
    ctx: Channel,
    payload_length: int,
    message_length: int,
    ctrl_byte: int,
) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_TH1", iface=ctx.iface)
    if not control_byte.is_handshake_init_req(ctrl_byte):
        raise ThpError("Message received is not a handshake init request!")
    if not payload_length == PUBKEY_LENGTH + CHECKSUM_LENGTH:
        raise ThpError("Message received is not a valid handshake init request!")

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    ctx.handshake = Handshake()

    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO buffer is gone :/

    host_ephemeral_public_key = bytearray(
        buffer[INIT_HEADER_LENGTH : message_length - CHECKSUM_LENGTH]
    )
    trezor_ephemeral_public_key, encrypted_trezor_static_public_key, tag = (
        ctx.handshake.handle_th1_crypto(
            get_encoded_device_properties(ctx.iface), host_ephemeral_public_key
        )
    )

    if __debug__:
        log.debug(
            __name__,
            "trezor ephemeral public key: %s",
            hexlify_if_bytes(trezor_ephemeral_public_key),
            iface=ctx.iface,
        )
        log.debug(
            __name__,
            "encrypted trezor masked static public key: %s",
            hexlify_if_bytes(encrypted_trezor_static_public_key),
            iface=ctx.iface,
        )
        log.debug(__name__, "tag: %s", hexlify_if_bytes(tag), iface=ctx.iface)

    payload = trezor_ephemeral_public_key + encrypted_trezor_static_public_key + tag

    # send handshake init response message
    ctx.write_handshake_message(HANDSHAKE_INIT_RES, payload)
    ctx.set_channel_state(ChannelState.TH2)
    return


def _handle_state_TH2(ctx: Channel, message_length: int, ctrl_byte: int) -> None:
    from apps.thp.credential_manager import decode_credential, validate_credential

    if __debug__:
        log.debug(__name__, "handle_state_TH2", iface=ctx.iface)
    if not control_byte.is_handshake_comp_req(ctrl_byte):
        raise ThpError("Message received is not a handshake completion request!")

    if ctx.handshake is None:
        raise ThpUnallocatedChannelError(
            "Handshake object is not prepared. Create new channel."
        )

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO handle
    host_encrypted_static_public_key = buffer[
        INIT_HEADER_LENGTH : INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH
    ]
    handshake_completion_request_noise_payload = buffer[
        INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH : message_length - CHECKSUM_LENGTH
    ]

    ctx.handshake.handle_th2_crypto(
        host_encrypted_static_public_key, handshake_completion_request_noise_payload
    )

    ctx.channel_cache.set(CHANNEL_KEY_RECEIVE, ctx.handshake.key_receive)
    ctx.channel_cache.set(CHANNEL_KEY_SEND, ctx.handshake.key_send)
    ctx.channel_cache.set(CHANNEL_HANDSHAKE_HASH, ctx.handshake.h)
    ctx.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
    ctx.channel_cache.set_int(CHANNEL_NONCE_SEND, 1)

    noise_payload = _decode_message(
        buffer[
            INIT_HEADER_LENGTH
            + KEY_LENGTH
            + TAG_LENGTH : message_length
            - CHECKSUM_LENGTH
            - TAG_LENGTH
        ],
        0,
        "ThpHandshakeCompletionReqNoisePayload",
    )
    if TYPE_CHECKING:
        assert ThpHandshakeCompletionReqNoisePayload.is_type_of(noise_payload)

    if __debug__:
        log.debug(
            __name__,
            "host static public key: %s, noise payload: %s",
            utils.hexlify_if_bytes(host_encrypted_static_public_key),
            utils.hexlify_if_bytes(handshake_completion_request_noise_payload),
            iface=ctx.iface,
        )

    # key is decoded in handshake._handle_th2_crypto
    host_static_public_key = host_encrypted_static_public_key[:PUBKEY_LENGTH]
    ctx.channel_cache.set_host_static_public_key(bytearray(host_static_public_key))

    paired: bool = False
    trezor_state = _TREZOR_STATE_UNPAIRED

    if noise_payload.host_pairing_credential is not None:
        try:  # TODO change try-except for something better
            credential = decode_credential(noise_payload.host_pairing_credential)
            paired = validate_credential(
                credential,
                host_static_public_key,
            )
            if paired:
                trezor_state = _TREZOR_STATE_PAIRED
                ctx.credential = credential
            else:
                ctx.credential = None
        except DataError as e:
            if __debug__:
                log.exception(__name__, e, iface=ctx.iface)
            pass

    # send hanshake completion response
    ctx.write_handshake_message(
        HANDSHAKE_COMP_RES,
        ctx.handshake.get_handshake_completion_response(trezor_state),
    )

    ctx.handshake = None

    if paired:
        ctx.set_channel_state(ChannelState.TC1)
    else:
        ctx.set_channel_state(ChannelState.TP0)


def _handle_state_ENCRYPTED_TRANSPORT(ctx: Channel, message_length: int) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT", iface=ctx.iface)

    ctx.decrypt_buffer(message_length)

    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO handle
    session_id, message_type = ustruct.unpack(
        ">BH", memoryview(buffer)[INIT_HEADER_LENGTH:]
    )
    if session_id not in ctx.sessions:

        s = session_manager.get_session_from_cache(ctx, session_id)

        if s is None:
            s = SeedlessSessionContext(ctx, session_id)

        ctx.sessions[session_id] = s
        loop.schedule(s.handle())

    elif ctx.sessions[session_id].get_session_state() is SessionState.UNALLOCATED:
        raise ThpUnallocatedSessionError(session_id)

    s = ctx.sessions[session_id]
    update_session_last_used(s.channel_id, (s.session_id).to_bytes(1, "big"))

    s.incoming_message.put(
        Message(
            message_type,
            buffer[
                INIT_HEADER_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : message_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
    )
    if __debug__:
        log.debug(
            __name__,
            f"Scheduled message to be handled by a session (session_id: {session_id}, msg_type (int): {message_type})",
            iface=ctx.iface,
        )


def _handle_pairing(ctx: Channel, message_length: int) -> None:
    from .pairing_context import PairingContext

    if ctx.connection_context is None:
        ctx.connection_context = PairingContext(ctx)
        loop.schedule(ctx.connection_context.handle())

    ctx.decrypt_buffer(message_length)
    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO handle
    message_type = ustruct.unpack(
        ">H", buffer[INIT_HEADER_LENGTH + SESSION_ID_LENGTH :]
    )[0]

    ctx.connection_context.incoming_message.put(
        Message(
            message_type,
            buffer[
                INIT_HEADER_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : message_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
    )


def _should_have_ctrl_byte_encrypted_transport(ctx: Channel) -> bool:
    return ctx.get_channel_state() not in (
        ChannelState.UNALLOCATED,
        ChannelState.TH1,
        ChannelState.TH2,
    )


def _decode_message(
    buffer: bytes,
    msg_type: int,
    message_name: str | None = None,
    wire_enum: str = "ThpMessageType",
) -> protobuf.MessageType:
    if __debug__:
        log.debug(__name__, "decode message")
    if message_name is not None:
        expected_type = protobuf.type_for_name(message_name)
    else:
        expected_type = protobuf.type_for_wire(wire_enum, msg_type)
    return message_handler.wrap_protobuf_load(buffer, expected_type)


def _is_channel_state_pairing(state: int) -> bool:
    return state in (
        ChannelState.TP0,
        ChannelState.TP1,
        ChannelState.TP2,
        ChannelState.TP3,
        ChannelState.TP4,
        ChannelState.TC1,
    )
