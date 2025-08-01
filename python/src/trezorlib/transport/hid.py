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

import logging
import sys
import time
import typing as t

from ..log import DUMP_PACKETS
from ..models import TREZOR_ONE, TrezorModel
from . import UDEV_RULES_STR, Timeout, Transport, TransportException

LOG = logging.getLogger(__name__)

try:
    import hid

    HID_IMPORTED = True
except Exception as e:
    LOG.info(f"HID transport is disabled: {e}")
    HID_IMPORTED = False


HidDevice = t.Dict[str, t.Any]
HidDeviceHandle = t.Any


class HidTransport(Transport):
    """
    HidTransport implements transport over USB HID interface.
    """

    PATH_PREFIX = "hid"
    ENABLED = HID_IMPORTED

    def __init__(self, device: HidDevice, probe_hid_version: bool = False) -> None:
        self.device = device
        self.device_path = device["path"]
        self.device_serial_number = device["serial_number"]
        self.handle: HidDeviceHandle = None
        self.hid_version = None if probe_hid_version else 2

    def get_path(self) -> str:
        return f"{self.PATH_PREFIX}:{self.device['path'].decode()}"

    @classmethod
    def enumerate(
        cls, models: t.Iterable["TrezorModel"] | None = None, debug: bool = False
    ) -> t.Iterable["HidTransport"]:
        if models is None:
            models = {TREZOR_ONE}
        usb_ids = [id for model in models for id in model.usb_ids]

        devices: t.List["HidTransport"] = []
        for dev in hid.enumerate(0, 0):
            usb_id = (dev["vendor_id"], dev["product_id"])
            if usb_id not in usb_ids:
                continue
            if debug:
                if not is_debuglink(dev):
                    continue
            else:
                if not is_wirelink(dev):
                    continue
            devices.append(HidTransport(dev))
        return devices

    def find_debug(self) -> "HidTransport":
        # For v1 protocol, find debug USB interface for the same serial number
        for debug in HidTransport.enumerate(debug=True):
            if debug.device["serial_number"] == self.device["serial_number"]:
                return debug
        raise TransportException("Debug HID device not found")

    def open(self) -> None:
        self.handle = hid.device()
        try:
            self.handle.open_path(self.device_path)
        except (IOError, OSError) as e:
            if sys.platform.startswith("linux"):
                e.args = e.args + (UDEV_RULES_STR,)
            raise e

        # On some platforms, HID path stays the same over device reconnects.
        # That means that someone could unplug a Trezor, plug a different one
        # and we wouldn't even know.
        # So we check that the serial matches what we expect.
        serial = self.handle.get_serial_number_string()
        if serial != self.device_serial_number:
            self.handle.close()
            self.handle = None
            raise TransportException(
                f"Unexpected device {serial} on path {self.device_path.decode()}"
            )

        self.handle.set_nonblocking(True)

        if self.hid_version is None:
            self.hid_version = self.probe_hid_version()

    def close(self) -> None:
        if self.handle is not None:
            # reload serial, because device.wipe() can reset it
            self.device_serial_number = self.handle.get_serial_number_string()
            self.handle.close()
        self.handle = None

    def write_chunk(self, chunk: bytes) -> None:
        if len(chunk) != 64:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")

        if self.hid_version == 2:
            chunk = b"\x00" + chunk

        LOG.log(DUMP_PACKETS, f"writing packet: {chunk.hex()}")
        self.handle.write(chunk)

    def read_chunk(self, timeout: float | None = None) -> bytes:
        start = time.time()
        while True:
            # hidapi seems to return lists of ints instead of bytes
            chunk = bytes(self.handle.read(64))
            if chunk:
                break
            else:
                if timeout is not None and time.time() - start > timeout:
                    raise Timeout(f"Timeout reading HID packet ({timeout}s)")
                time.sleep(0.001)

        LOG.log(DUMP_PACKETS, f"read packet: {chunk.hex()}")
        if len(chunk) != 64:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        return bytes(chunk)

    def probe_hid_version(self) -> int:
        n = self.handle.write([0, 63] + [0xFF] * 63)
        if n == 65:
            return 2
        n = self.handle.write([63] + [0xFF] * 63)
        if n == 64:
            return 1
        raise TransportException("Unknown HID version")

    def ping(self) -> bool:
        return self.handle is not None


def is_wirelink(dev: HidDevice) -> bool:
    return dev["usage_page"] == 0xFF00 or dev["interface_number"] == 0


def is_debuglink(dev: HidDevice) -> bool:
    return dev["usage_page"] == 0xFF01 or dev["interface_number"] == 1
