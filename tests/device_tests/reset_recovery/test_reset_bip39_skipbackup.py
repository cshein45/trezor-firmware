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
from mnemonic import Mnemonic

from trezorlib import messages
from trezorlib.debuglink import SessionDebugWrapper as Session

from ...common import EXTERNAL_ENTROPY, generate_entropy

pytestmark = pytest.mark.models("legacy")

STRENGTH = 128


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_skip_backup(session: Session):
    debug = session.client.debug
    ret = session.call_raw(
        messages.ResetDevice(
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            skip_backup=True,
        )
    )

    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    internal_entropy = debug.state().reset_entropy
    ret = session.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))
    assert isinstance(ret, messages.Success)

    # Check if device is properly initialized
    ret = session.call_raw(messages.GetFeatures())
    assert ret.initialized is True
    assert ret.backup_availability == messages.BackupAvailability.Required
    assert ret.unfinished_backup is False
    assert ret.no_backup is False

    # Generate mnemonic locally
    entropy = generate_entropy(STRENGTH, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # start Backup workflow
    ret = session.call_raw(messages.BackupDevice())

    mnemonic = []
    for _ in range(STRENGTH // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(debug.read_reset_word())
        debug.press_yes()
        session.call_raw(messages.ButtonAck())

    mnemonic = " ".join(mnemonic)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    mnemonic = []
    for _ in range(STRENGTH // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(debug.read_reset_word())
        debug.press_yes()
        ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.Success)

    mnemonic = " ".join(mnemonic)

    # Compare that second pass printed out the same mnemonic once again
    assert mnemonic == expected_mnemonic

    # start backup again - should fail
    ret = session.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_skip_backup_break(session: Session):
    debug = session.client.debug
    ret = session.call_raw(
        messages.ResetDevice(
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            skip_backup=True,
        )
    )

    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    ret = session.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))
    assert isinstance(ret, messages.Success)

    # Check if device is properly initialized
    ret = session.call_raw(messages.GetFeatures())
    assert ret.initialized is True
    assert ret.backup_availability == messages.BackupAvailability.Required
    assert ret.unfinished_backup is False
    assert ret.no_backup is False

    # start Backup workflow
    ret = session.call_raw(messages.BackupDevice())

    # send Initialize -> break workflow
    ret = session.call_raw(messages.Initialize())
    assert isinstance(ret, messages.Features)
    assert ret.initialized is True
    assert ret.backup_availability == messages.BackupAvailability.NotAvailable
    assert ret.unfinished_backup is True
    assert ret.no_backup is False

    # start backup again - should fail
    ret = session.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)

    # read Features again
    ret = session.call_raw(messages.Initialize())
    assert isinstance(ret, messages.Features)
    assert ret.initialized is True
    assert ret.backup_availability == messages.BackupAvailability.NotAvailable
    assert ret.unfinished_backup is True
    assert ret.no_backup is False


def test_initialized_device_backup_fail(session: Session):
    ret = session.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)
