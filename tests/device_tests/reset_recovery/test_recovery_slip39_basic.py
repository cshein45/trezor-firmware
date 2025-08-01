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

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import SessionDebugWrapper as Session

from ...common import (
    MNEMONIC_SLIP39_BASIC_20_3of6,
    MNEMONIC_SLIP39_BASIC_20_3of6_SECRET,
    MNEMONIC_SLIP39_BASIC_EXT_20_2of3,
    MNEMONIC_SLIP39_BASIC_EXT_20_2of3_SECRET,
)
from ...input_flows import (
    InputFlowSlip39BasicRecovery,
    InputFlowSlip39BasicRecoveryAbort,
    InputFlowSlip39BasicRecoveryAbortBetweenShares,
    InputFlowSlip39BasicRecoveryAbortOnNumberOfWords,
    InputFlowSlip39BasicRecoveryInvalidFirstShare,
    InputFlowSlip39BasicRecoveryInvalidSecondShare,
    InputFlowSlip39BasicRecoveryNoAbort,
    InputFlowSlip39BasicRecoverySameShare,
    InputFlowSlip39BasicRecoveryShareInfoBetweenShares,
    InputFlowSlip39BasicRecoveryWrongNthWord,
)

pytestmark = [pytest.mark.models("core"), pytest.mark.uninitialized_session]

MNEMONIC_SLIP39_BASIC_20_1of1 = [
    "academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic rebuild aquatic spew"
]


MNEMONIC_SLIP39_BASIC_33_2of5 = [
    "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
    "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
]

VECTORS = (
    (
        MNEMONIC_SLIP39_BASIC_20_3of6,
        MNEMONIC_SLIP39_BASIC_20_3of6_SECRET,
        messages.BackupType.Slip39_Basic,
    ),
    (
        MNEMONIC_SLIP39_BASIC_EXT_20_2of3,
        MNEMONIC_SLIP39_BASIC_EXT_20_2of3_SECRET,
        messages.BackupType.Slip39_Basic_Extendable,
    ),
    (
        MNEMONIC_SLIP39_BASIC_33_2of5,
        "b770e0da1363247652de97a39bdbf2463be087848d709ecbf28e84508e31202a",
        messages.BackupType.Slip39_Basic,
    ),
)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("shares, secret, backup_type", VECTORS)
def test_secret(
    session: Session, shares: list[str], secret: str, backup_type: messages.BackupType
):
    with session.client as client:
        IF = InputFlowSlip39BasicRecovery(session.client, shares)
        client.set_input_flow(IF.get())
        device.recover(session, pin_protection=False, label="label")

    # Workflow successfully ended
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is backup_type

    # Check mnemonic
    assert session.client.debug.state().mnemonic_secret.hex() == secret


@pytest.mark.setup_client(uninitialized=True)
def test_recover_with_pin_passphrase(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecovery(
            session.client, MNEMONIC_SLIP39_BASIC_20_3of6, pin="654"
        )
        client.set_input_flow(IF.get())
        device.recover(
            session,
            pin_protection=True,
            passphrase_protection=True,
            label="label",
        )

    # Workflow successfully ended
    assert session.features.pin_protection is True
    assert session.features.passphrase_protection is True
    assert session.features.backup_type is messages.BackupType.Slip39_Basic


@pytest.mark.setup_client(uninitialized=True)
def test_abort(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryAbort(session.client)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert session.features.initialized is False
        assert session.features.recovery_status is messages.RecoveryStatus.Nothing


@pytest.mark.models(skip=["legacy", "safe3"])
@pytest.mark.setup_client(uninitialized=True)
def test_abort_on_number_of_words(session: Session):
    # on Caesar, test_abort actually aborts on the # of words selection
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryAbortOnNumberOfWords(session.client)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        assert session.features.initialized is False
        assert session.features.recovery_status is messages.RecoveryStatus.Nothing


@pytest.mark.setup_client(uninitialized=True)
def test_abort_between_shares(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryAbortBetweenShares(
            session.client, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert session.features.initialized is False
        assert session.features.recovery_status is messages.RecoveryStatus.Nothing


@pytest.mark.models("eckhart")
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_share_info_between_shares(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryShareInfoBetweenShares(
            session, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_noabort(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryNoAbort(
            session.client, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert session.features.initialized is True


@pytest.mark.setup_client(uninitialized=True)
def test_invalid_mnemonic_first_share(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryInvalidFirstShare(session)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert session.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_invalid_mnemonic_second_share(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryInvalidSecondShare(
            session, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")
        session.refresh_features()
        assert session.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("nth_word", range(3))
def test_wrong_nth_word(session: Session, nth_word: int):
    share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
    with session.client as client:
        IF = InputFlowSlip39BasicRecoveryWrongNthWord(session, share, nth_word)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_same_share(session: Session):
    share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
    with session.client as client:
        IF = InputFlowSlip39BasicRecoverySameShare(session, share)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(session, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_1of1(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicRecovery(session.client, MNEMONIC_SLIP39_BASIC_20_1of1)
        client.set_input_flow(IF.get())
        device.recover(
            session,
            pin_protection=False,
            passphrase_protection=False,
            label="label",
        )

    # Workflow successfully ended
    assert session.features.initialized is True
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is messages.BackupType.Slip39_Basic
