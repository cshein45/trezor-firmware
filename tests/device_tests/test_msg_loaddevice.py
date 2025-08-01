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

from trezorlib import debuglink, device, models
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType

from ..common import (
    MNEMONIC12,
    MNEMONIC_SLIP39_ADVANCED_20,
    MNEMONIC_SLIP39_BASIC_20_3of6,
    get_test_address,
)

pytestmark = [
    pytest.mark.setup_client(uninitialized=True),
    pytest.mark.uninitialized_session,
]


def test_load_device_1(session: Session):
    debuglink.load_device(
        session,
        mnemonic=MNEMONIC12,
        pin="",
        passphrase_protection=False,
        label="test",
    )
    session: Session = session.client.get_session()
    state = session.client.debug.state()
    assert state.mnemonic_secret == MNEMONIC12.encode()
    assert state.pin is None
    assert state.passphrase_protection is False

    address = get_test_address(session)
    assert address == "mkqRFzxmkCGX9jxgpqqFHcxRUmLJcLDBer"


def test_load_device_2(session: Session):
    debuglink.load_device(
        session,
        mnemonic=MNEMONIC12,
        pin="1234",
        passphrase_protection=True,
        label="test",
    )
    session: Session = session.client.get_session(passphrase="passphrase")

    state = session.client.debug.state()
    assert state.mnemonic_secret == MNEMONIC12.encode()

    if session.model is models.T1B1:
        # we do not send PIN in DebugLinkState in Core
        assert state.pin == "1234"
    assert state.passphrase_protection is True

    address = get_test_address(session)
    assert address == "mx77VZjTVixVsU7nCtAKHnGFdsyNCnsWWw"


@pytest.mark.models("core")
def test_load_device_slip39_basic(session: Session):
    session = session
    debuglink.load_device(
        session,
        mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6,
        pin="",
        passphrase_protection=False,
        label="test",
    )
    assert session.features.backup_type == BackupType.Slip39_Basic


@pytest.mark.models("core")
def test_load_device_slip39_advanced(session: Session):
    session = session
    debuglink.load_device(
        session,
        mnemonic=MNEMONIC_SLIP39_ADVANCED_20,
        pin="",
        passphrase_protection=False,
        label="test",
    )
    assert session.features.backup_type == BackupType.Slip39_Advanced


def test_load_device_utf(client: Client):
    words_nfkd = "Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
    words_nfc = "P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
    words_nfkc = "P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
    words_nfd = "Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"

    passphrase_nfkd = (
        "Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko"
    )
    passphrase_nfc = "Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko"
    passphrase_nfkc = "Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko"
    passphrase_nfd = (
        "Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko"
    )
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        mnemonic=words_nfkd,
        pin="",
        passphrase_protection=True,
        label="test",
        skip_checksum=True,
    )
    session: Session = session.client.get_session(passphrase=passphrase_nfkd)
    address_nfkd = get_test_address(session)

    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        mnemonic=words_nfc,
        pin="",
        passphrase_protection=True,
        label="test",
        skip_checksum=True,
    )
    session = client.get_session(passphrase=passphrase_nfc)
    address_nfc = get_test_address(session)

    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        mnemonic=words_nfkc,
        pin="",
        passphrase_protection=True,
        label="test",
        skip_checksum=True,
    )
    session = client.get_session(passphrase=passphrase_nfkc)
    address_nfkc = get_test_address(session)

    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        mnemonic=words_nfd,
        pin="",
        passphrase_protection=True,
        label="test",
        skip_checksum=True,
    )
    session = client.get_session(passphrase=passphrase_nfd)
    address_nfd = get_test_address(session)
    assert address_nfkd == address_nfc
    assert address_nfkd == address_nfkc
    assert address_nfkd == address_nfd
