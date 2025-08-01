from typing import *


# upymod/modtrezorio/modtrezorio-hid.h
class HID:
    """
    USB HID interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        ep_in: int,
        ep_out: int,
        emu_port: int,
        report_desc: bytes,
        subclass: int = 0,
        protocol: int = 0,
        polling_interval: int = 1,
        max_packet_len: int = 64,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: bytes) -> int:
        """
        Sends message using USB HID (device) or UDP (emulator).
        """

    def read(self, buf: bytearray, offset: int = 0) -> int:
        """
        Reads message using USB HID (device) or UDP (emulator).
        """

    def write_blocking(self, msg: bytes, timeout_ms: int) -> int:
        """
        Sends message using USB HID (device) or UDP (emulator).
        """
    RX_PACKET_LEN: ClassVar[int]
    """Length of one USB RX packet."""
    TX_PACKET_LEN: ClassVar[int]
    """Length of one USB TX packet."""


# upymod/modtrezorio/modtrezorio-poll.h
def poll(ifaces: Iterable[int], list_ref: list, timeout_ms: int) -> bool:
    """
    Wait until one of `ifaces` is ready to read or write (using masks
    `io.POLL_READ` and `io.POLL_WRITE`) and assign the result into
    `list_ref`:

    - `list_ref[0]` - the interface number, including the mask
    - `list_ref[1]` - for touch event, tuple of:
                    (event_type, x_position, y_position)
                  - for button event (T1), tuple of:
                    (event type, button number)
                  - for USB read event, received bytes

    If timeout occurs, False is returned, True otherwise.
    """


# upymod/modtrezorio/modtrezorio-usb.h
class USB:
    """
    USB device configuration.
    """

    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        release_num: int,
        device_class: int = 0,
        device_subclass: int = 0,
        device_protocol: int = 0,
        manufacturer: str = "",
        product: str = "",
        interface: str = "",
        usb21_enabled: bool = True,
        usb21_landing: bool = True,
    ) -> None:
        """
        """

    def add(self, iface: HID | VCP | WebUSB) -> None:
        """
        Registers passed interface into the USB stack.
        """

    def open(self, serial_number: str) -> None:
        """
        Initializes the USB stack.
        """

    def close(self) -> None:
        """
        Cleans up the USB stack.
        """


# upymod/modtrezorio/modtrezorio-vcp.h
class VCP:
    """
    USB VCP interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        data_iface_num: int,
        ep_in: int,
        ep_out: int,
        ep_cmd: int,
        emu_port: int,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """


# upymod/modtrezorio/modtrezorio-webusb.h
class WebUSB:
    """
    USB WebUSB interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        ep_in: int,
        ep_out: int,
        emu_port: int,
        subclass: int = 0,
        protocol: int = 0,
        polling_interval: int = 1,
        max_packet_len: int = 64,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: bytes) -> int:
        """
        Sends message using USB WebUSB (device) or UDP (emulator).
        """

    def read(self, buf: bytearray, offset: int = 0) -> int:
        """
        Reads message using USB WebUSB (device) or UDP (emulator).
        """
    RX_PACKET_LEN: ClassVar[int]
    """Length of one USB RX packet."""
    TX_PACKET_LEN: ClassVar[int]
    """Length of one USB TX packet."""
from . import fatfs, haptic, sdcard, ble, pm
POLL_READ: int  # wait until interface is readable and return read data
POLL_WRITE: int  # wait until interface is writable

BLE: int  # interface id of the BLE events
BLE_EVENT: int # interface id for BLE events

PM_EVENT: int  # interface id for power manager events

TOUCH: int  # interface id of the touch events
TOUCH_START: int  # event id of touch start event
TOUCH_MOVE: int  # event id of touch move event
TOUCH_END: int  # event id of touch end event
BUTTON: int  # interface id of button events
BUTTON_PRESSED: int  # button down event
BUTTON_RELEASED: int  # button up event
BUTTON_LEFT: int  # button number of left button
BUTTON_RIGHT: int  # button number of right button
USB_EVENT: int # interface id for USB events
WireInterface = Union[HID, WebUSB, BleInterface]
