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

import pytest

from trezorlib import device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

from ...input_flows import InputFlowSlip39BasicRecoveryDryRun

pytestmark = pytest.mark.models("core")

SHARES_20_2of3 = [
    "crush merchant academic acid dream decision orbit smug trend trust painting slice glad crunch veteran lunch friar satoshi engage aquatic",
    "crush merchant academic agency devote eyebrow disaster island deploy flip toxic budget numerous airport loyalty fitness resident learn sympathy daughter",
    "crush merchant academic always course verdict rescue paces fridge museum energy solution space ladybug junction national biology game fawn coal",
]

INVALID_SHARES_20_2of3 = [
    "gesture necklace academic acid civil round fiber buyer swing ancient jerky kitchen chest dining enjoy tension museum increase various rebuild",
    "gesture necklace academic agency decrease justice ounce dragon shaped unknown material answer dress wrote smell family squeeze diet angry husband",
]


@pytest.mark.setup_client(mnemonic=SHARES_20_2of3[0:2])
def test_2of3_dryrun(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryDryRun(session.client, SHARES_20_2of3[1:3])
        client.set_input_flow(IF.get())
        device.recover(
            session,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            type=messages.RecoveryType.DryRun,
        )


@pytest.mark.setup_client(mnemonic=SHARES_20_2of3[0:2])
def test_2of3_invalid_seed_dryrun(session: Session):
    # test fails because of different seed on device
    with session.client as client, pytest.raises(
        TrezorFailure, match=r"The seed does not match the one in the device"
    ):
        IF = InputFlowSlip39BasicRecoveryDryRun(
            session.client, INVALID_SHARES_20_2of3, mismatch=True
        )
        client.set_input_flow(IF.get())
        device.recover(
            session,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            type=messages.RecoveryType.DryRun,
        )
