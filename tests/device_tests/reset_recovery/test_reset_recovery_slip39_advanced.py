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

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType
from trezorlib.tools import parse_path

from ...common import MOCK_GET_ENTROPY
from ...input_flows import (
    InputFlowSlip39AdvancedRecovery,
    InputFlowSlip39AdvancedResetRecovery,
)
from ...translations import set_language


@pytest.mark.models("core")
@pytest.mark.setup_client(uninitialized=True)
def test_reset_recovery(client: Client):
    session = client.get_seedless_session()
    mnemonics = reset(session)
    session = client.get_session()
    address_before = btc.get_address(session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))
    # we're generating 3of5 groups 3of5 shares each
    test_combinations = [
        mnemonics[0:3]  # shares 1-3 from groups 1-3
        + mnemonics[5:8]
        + mnemonics[10:13],
        mnemonics[2:5]  # shares 3-5 from groups 1-3
        + mnemonics[7:10]
        + mnemonics[12:15],
        mnemonics[10:13]  # shares 1-3 from groups 3-5
        + mnemonics[15:18]
        + mnemonics[20:23],
        mnemonics[12:15]  # shares 3-5 from groups 3-5
        + mnemonics[17:20]
        + mnemonics[22:25],
    ]
    for combination in test_combinations:
        session = client.get_seedless_session()
        lang = client.features.language or "en"
        device.wipe(session)
        client = client.get_new_client()
        session = client.get_seedless_session()
        set_language(session, lang[:2])
        recover(session, combination, click_info=True)
        session = client.get_session()
        address_after = btc.get_address(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0")
        )
        assert address_before == address_after


def reset(session: Session, strength: int = 128) -> list[str]:
    with session.client as client:
        IF = InputFlowSlip39AdvancedResetRecovery(session.client, False)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Slip39_Advanced,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # Check if device is properly initialized
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Advanced_Extendable

    return IF.mnemonics


def recover(session: Session, shares: list[str], click_info: bool = False):
    with session.client as client:
        IF = InputFlowSlip39AdvancedRecovery(client, shares, click_info)
        client.set_input_flow(IF.get())
        device.recover(session, pin_protection=False, label="label")

    # Workflow successfully ended
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Advanced_Extendable
