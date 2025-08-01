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

from typing import TYPE_CHECKING

import pytest

from trezorlib import device, messages

from .. import translations as TR
from ..common import MOCK_GET_ENTROPY
from . import reset
from .common import LayoutType, go_next

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(uninitialized=True)
def test_reset_bip39(device_handler: "BackgroundDeviceHandler"):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False
    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session,
        device.setup,
        strength=128,
        backup_type=messages.BackupType.Bip39,
        pin_protection=False,
        passphrase_protection=False,
        entropy_check_count=0,
        _get_entropy=MOCK_GET_ENTROPY,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # confirm back up
    if debug.read_layout().page_count() == 1:
        assert any(
            needle in debug.read_layout().text_content()
            for needle in [
                TR.backup__it_should_be_backed_up,
                TR.backup__it_should_be_backed_up_now,
            ]
        )
    reset.confirm_read(debug)

    # confirm backup intro
    # parametrized string
    assert TR.regexp("backup__info_single_share_backup").match(
        debug.read_layout().text_content()
    )
    reset.confirm_read(debug)

    # confirm backup warning
    assert TR.reset__never_make_digital_copy in debug.read_layout().text_content()
    reset.confirm_read(debug, middle_r=True)

    # read words
    words = reset.read_words(debug)

    # confirm words
    reset.confirm_words(debug, words)

    # confirm backup done
    reset.confirm_read(debug)

    # Your backup is done
    if debug.layout_type is not LayoutType.Eckhart:
        go_next(debug)

    # TODO: some validation of the generated secret?

    # retrieve the result to check that it's not a TrezorFailure exception
    device_handler.result()

    features = device_handler.features()
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Bip39
