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

import time

import pytest

from trezorlib import device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..common import get_test_address

PIN4 = "1234"


@pytest.mark.setup_client(passphrase=True)
def test_wipe_device(client: Client):
    assert client.features.initialized is True
    assert client.features.label == "test"
    assert client.features.passphrase_protection is True
    device_id = client.features.device_id

    device.wipe(client.get_session())
    client = client.get_new_client()
    assert client.features.initialized is False
    assert client.features.label is None
    assert client.features.passphrase_protection is False
    assert client.features.device_id != device_id


@pytest.mark.setup_client(pin=PIN4)
def test_autolock_not_retained(session: Session):
    client = session.client
    client.use_pin_sequence([PIN4])
    device.apply_settings(session, auto_lock_delay_ms=10_000)

    assert session.features.auto_lock_delay_ms == 10_000

    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()

    assert client.features.auto_lock_delay_ms > 10_000

    client.use_pin_sequence([PIN4, PIN4])
    device.setup(
        session,
        skip_backup=True,
        pin_protection=True,
        passphrase_protection=False,
        entropy_check_count=0,
        backup_type=messages.BackupType.Bip39,
    )

    time.sleep(10.5)
    session = client.get_session()

    with session.client as client:
        # after sleeping for the pre-wipe autolock amount, Trezor must still be unlocked
        client.set_expected_responses([messages.Address])
        get_test_address(session)
