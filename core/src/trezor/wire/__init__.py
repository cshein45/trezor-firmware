"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec/codec_v1.py` or `trezor/wire/thp/thp_main.py`.
- Transferred over USB interface, or UDP in case of Unix emulation.

This module:

1. Runs workflows, also called `handlers`, to process the message.
2. Creates and passes the `Context` object to the handlers. This provides an interface to
   wait, read, write etc. on the wire.

## Session handler

When the `wire.setup` is called the `handle_session` coroutine is scheduled. The
`handle_session` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known the first handler is called. This way the
`handle_session` goes through all the workflows.

"""

from typing import TYPE_CHECKING

from trezor import loop, protobuf, utils

from .. import workflow
from . import message_handler, protocol_common

if utils.USE_THP:
    from .thp import thp_main
else:
    from .codec.codec_context import CodecContext

from .context import UnexpectedMessageException
from .message_handler import failure

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from .errors import *  # isort:skip # noqa: F401,F403

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any, Callable, Coroutine, Generic, TypeVar

    T = TypeVar("T")
    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[[Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)
else:
    Generic = (object,)
    T = 0


class Provider(Generic[T]):
    def __init__(self, obj: T) -> None:
        self.obj = obj

    def take(self) -> T | None:
        if self.obj is None:
            return None

        obj = self.obj
        self.obj = None
        return obj


def setup(iface: WireInterface) -> None:
    """Initialize the wire stack on the provided WireInterface."""
    loop.schedule(handle_session(iface))


if utils.USE_THP:
    # memory_manager is imported to create READ/WRITE buffers
    # in more stable area of memory
    from .thp import memory_manager  # noqa: F401

    async def handle_session(iface: WireInterface) -> None:

        # Take a mark of modules that are imported at this point, so we can
        # roll back and un-import any others.
        modules = utils.unimport_begin()

        while True:
            try:
                await thp_main.thp_main_loop(iface)
            except Exception as exc:
                # Log and try again.
                if __debug__:
                    log.exception(__name__, exc, iface=iface)
            finally:
                # Unload modules imported by the workflow. Should not raise.
                if __debug__:
                    log.debug(
                        __name__,
                        "utils.unimport_end(modules) and loop.clear()",
                        iface=iface,
                    )
                utils.unimport_end(modules)
                loop.clear()
                return  # pylint: disable=lost-exception

else:

    # Reallocated once per session and shared between all wire interfaces.
    # Acquired by the first call to `CodecContext.read_from_wire()`.
    WIRE_BUFFER_PROVIDER = Provider(bytearray(8192))

    async def handle_session(iface: WireInterface) -> None:
        ctx = CodecContext(iface, WIRE_BUFFER_PROVIDER)
        next_msg: protocol_common.Message | None = None

        # Take a mark of modules that are imported at this point, so we can
        # roll back and un-import any others.
        modules = utils.unimport_begin()
        while True:
            try:
                if next_msg is None:
                    # If the previous run did not keep an unprocessed message for us,
                    # wait for a new one coming from the wire.
                    try:
                        msg = await ctx.read_from_wire()
                    except protocol_common.WireError as exc:
                        if __debug__:
                            log.exception(__name__, exc, iface=iface)
                        await ctx.write(failure(exc))
                        continue
                else:
                    # Process the message from previous run.
                    msg = next_msg
                    next_msg = None

                do_not_restart = False
                try:
                    do_not_restart = await message_handler.handle_single_message(
                        ctx, msg
                    )
                except UnexpectedMessageException as unexpected:
                    # The workflow was interrupted by an unexpected message. We need to
                    # process it as if it was a new message...
                    next_msg = unexpected.msg
                    # ...and we must not restart because that would lose the message.
                    do_not_restart = True
                    continue
                except Exception as exc:
                    # Log and ignore. The session handler can only exit explicitly in the
                    # following finally block.
                    if __debug__:
                        log.exception(__name__, exc, iface=iface)
                finally:
                    # Unload modules imported by the workflow. Should not raise.
                    utils.unimport_end(modules)

                    if not do_not_restart:
                        # Wait for all active workflows to finish.
                        await workflow.join_all()
                        # Let the session be restarted from `main`.
                        if __debug__:
                            log.debug(__name__, "loop.clear()", iface=iface)
                        loop.clear()
                        return  # pylint: disable=lost-exception

            except Exception as exc:
                # Log and try again. The session handler can only exit explicitly via
                # loop.clear() above.
                if __debug__:
                    log.exception(__name__, exc, iface=iface)
