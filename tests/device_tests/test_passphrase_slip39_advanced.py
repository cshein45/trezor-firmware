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

from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..common import (
    MNEMONIC_SLIP39_ADVANCED_20,
    MNEMONIC_SLIP39_ADVANCED_33,
    get_test_address,
)


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20, passphrase=True)
@pytest.mark.models("core")
def test_128bit_passphrase(client: Client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K3dzDLfeY3cMp23u5vDeFYftu5RPYZPucKc99mNEddU4w99GxdgUGcSfMpVDxhnR1XpJzZNXRN1m6xNgnzFS5MwMP6QyBRKV
    """
    assert client.features.passphrase_protection is True
    session = client.get_session(passphrase="TREZOR")
    address = get_test_address(session)
    assert address == "mkKDUMRR1CcK8eLAzCZAjKnNbCquPoWPxN"

    session = client.get_session(passphrase="ROZERT")
    address_compare = get_test_address(session)
    assert address != address_compare
    assert address_compare == "n1HeeeojjHgQnG6Bf5VWkM1gcpQkkXqSGw"


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_33, passphrase=True)
@pytest.mark.models("core")
def test_256bit_passphrase(client: Client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K2UspC9FRPfQC9NcDB4HPkx1XG9UEtuceYtpcCZ6ypNZWdgfxQ9dAFVeD1F4Zg4roY7nZm2LB7THPD6kaCege3M7EuS8v85c
    """
    assert client.features.passphrase_protection is True
    session = client.get_session(passphrase="TREZOR")
    address = get_test_address(session)
    assert address == "mxVtGxUJ898WLzPMmy6PT1FDHD1GUCWGm7"

    session = client.get_session(passphrase="ROZERT")
    address_compare = get_test_address(session)
    assert address != address_compare
