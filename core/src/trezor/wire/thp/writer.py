from micropython import const
from trezorcrypto import crc
from typing import TYPE_CHECKING

from trezor import io, loop, utils

from . import PacketHeader

INIT_HEADER_LENGTH = const(5)
CONT_HEADER_LENGTH = const(3)
CHECKSUM_LENGTH = const(4)
MAX_PAYLOAD_LEN = const(60000)
MESSAGE_TYPE_LENGTH = const(2)

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Awaitable, Sequence

if __debug__:
    from trezor import log


def write_payload_to_wire_and_add_checksum(
    iface: WireInterface, header: PacketHeader, transport_payload: bytes
) -> Awaitable[None]:
    header_checksum: int = crc.crc32(header.to_bytes())
    checksum: bytes = crc.crc32(transport_payload, header_checksum).to_bytes(
        CHECKSUM_LENGTH, "big"
    )
    data = (transport_payload, checksum)
    return write_payloads_to_wire(iface, header, data)


async def write_payloads_to_wire(
    iface: WireInterface, header: PacketHeader, data: Sequence[bytes]
) -> None:
    n_of_data = len(data)
    total_length = sum(len(item) for item in data)

    current_data_idx = 0
    current_data_offset = 0

    packet = bytearray(iface.TX_PACKET_LEN)
    header.pack_to_init_buffer(packet)
    packet_offset: int = INIT_HEADER_LENGTH
    packet_number = 0
    nwritten = 0
    while nwritten < total_length:
        if packet_number >= 1 and nwritten >= total_length - iface.TX_PACKET_LEN:
            # zero the last packet bytes and add the cont header
            packet[:] = bytearray(iface.TX_PACKET_LEN)
            header.pack_to_cont_buffer(packet)
        elif packet_number == 1:
            # add the cont header when preparing the second packet (if it is not the last)
            header.pack_to_cont_buffer(packet)

        while True:
            n = utils.memcpy(
                packet, packet_offset, data[current_data_idx], current_data_offset
            )
            packet_offset += n
            current_data_offset += n
            nwritten += n

            if packet_offset < iface.TX_PACKET_LEN:
                current_data_idx += 1
                current_data_offset = 0
                if current_data_idx >= n_of_data:
                    break
            elif packet_offset == iface.TX_PACKET_LEN:
                break
            else:
                raise Exception  # Should not happen
        packet_number += 1
        packet_offset = CONT_HEADER_LENGTH

        # write packet to wire (in-lined)
        if __debug__:
            log.debug(
                __name__,
                "write_packet_to_wire: %s",
                utils.hexlify_if_bytes(packet),
                iface=iface,
            )
        while True:
            await loop.wait(iface.iface_num() | io.POLL_WRITE)
            written_by_iface = iface.write(packet)
            if written_by_iface == len(packet):
                break
            assert written_by_iface == 0


async def write_packet_to_wire(iface: WireInterface, packet: bytes) -> None:
    while True:
        await loop.wait(iface.iface_num() | io.POLL_WRITE)
        if __debug__:
            log.debug(
                __name__,
                "write_packet_to_wire: %s",
                utils.hexlify_if_bytes(packet),
                iface=iface,
            )
        n_written = iface.write(packet)
        if n_written == len(packet):
            return
