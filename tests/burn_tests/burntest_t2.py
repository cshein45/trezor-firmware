#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import os
import random
import string

from trezorlib import device
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.transport import enumerate_devices, get_transport


def get_device():
    path = os.environ.get("TREZOR_PATH")
    if path:
        return get_transport(path)
    else:
        devices = enumerate_devices()
        for d in devices:
            if hasattr(d, "find_debug"):
                return d
        raise RuntimeError("No debuggable device found")


def pin_input_flow(client: Client, old_pin: str, new_pin: str):
    # do you want to change pin?
    yield
    client.debug.press_yes()
    if old_pin is not None:
        # enter old pin
        yield
        client.debug.input(old_pin)
    # enter new pin
    yield
    client.debug.input(new_pin)
    # repeat new pin
    yield
    client.debug.input(new_pin)


if __name__ == "__main__":
    wirelink = get_device()
    client = Client(wirelink)
    session = client.get_seedless_session()

    i = 0

    last_pin = None

    while True:
        # set private field
        device.apply_settings(client, use_passphrase=True)
        assert client.features.passphrase_protection is True
        device.apply_settings(client, use_passphrase=False)
        assert client.features.passphrase_protection is False

        # set public field
        label = "".join(random.choices(string.ascii_uppercase + string.digits, k=17))
        device.apply_settings(client, label=label)
        assert client.features.label == label

        # change PIN
        new_pin = "".join(random.choices(string.digits, k=random.randint(6, 10)))
        session.set_input_flow(pin_input_flow(client, last_pin, new_pin))
        device.change_pin(client)
        session.set_input_flow(None)
        last_pin = new_pin

        print(f"iteration {i}")
        i = i + 1

    wirelink.close()
