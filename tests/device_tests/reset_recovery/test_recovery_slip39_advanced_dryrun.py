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

from ...common import MNEMONIC_SLIP39_ADVANCED_20
from ...input_flows import InputFlowSlip39AdvancedRecoveryDryRun

pytestmark = pytest.mark.models("core")

INVALID_SHARES_SLIP39_ADVANCED_20 = [
    "chest garlic acrobat leaf diploma thank soul predator grant laundry camera license language likely slim twice amount rich total carve",
    "chest garlic acrobat lily adequate dwarf genius wolf faint nylon scroll national necklace leader pants literary lift axle watch midst",
    "chest garlic beard leaf coastal album dramatic learn identify angry dismiss goat plan describe round writing primary surprise sprinkle orbit",
    "chest garlic beard lily burden pistol retreat pickup emphasis large gesture hand eyebrow season pleasure genuine election skunk champion income",
]

# Extra share from another group to make sure it does not matter.
EXTRA_GROUP_SHARE = [
    "eraser senior decision smug corner ruin rescue cubic angel tackle skin skunk program roster trash rumor slush angel flea amazing"
]


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20, passphrase=False)
def test_2of3_dryrun(session: Session):
    with session.client as client:
        IF = InputFlowSlip39AdvancedRecoveryDryRun(
            session.client, EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20
        )
        client.set_input_flow(IF.get())
        device.recover(
            session,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            type=messages.RecoveryType.DryRun,
        )


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20)
def test_2of3_invalid_seed_dryrun(session: Session):
    # test fails because of different seed on device
    with session.client as client, pytest.raises(
        TrezorFailure, match=r"The seed does not match the one in the device"
    ):
        IF = InputFlowSlip39AdvancedRecoveryDryRun(
            session.client, INVALID_SHARES_SLIP39_ADVANCED_20, mismatch=True
        )
        client.set_input_flow(IF.get())
        device.recover(
            session,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            type=messages.RecoveryType.DryRun,
        )
