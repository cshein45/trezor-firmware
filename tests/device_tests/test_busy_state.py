# This file is part of the Trezor project.
#
# Copyright (C) 2022 SatoshiLabs and contributors
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

from trezorlib import btc, device
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

PIN = "1234"


def _assert_busy(session: Session, should_be_busy: bool, screen: str = "Homescreen"):
    assert session.features.busy is should_be_busy
    if session.client.layout_type is not LayoutType.T1:
        if should_be_busy:
            assert (
                "CoinJoinProgress"
                in session.client.debug.read_layout().all_components()
            )
        else:
            assert session.client.debug.read_layout().main_component() == screen


@pytest.mark.setup_client(pin=PIN)
def test_busy_state(session: Session):

    screen = (
        "Homescreen"
        if session.client.layout_type is LayoutType.Eckhart
        else "Lockscreen"
    )
    _assert_busy(session, False, screen)
    assert session.features.unlocked is False

    # Show busy dialog for 1 minute.
    device.set_busy(session, expiry_ms=60 * 1000)
    _assert_busy(session, True)
    assert session.features.unlocked is False

    with session.client as client:
        client.use_pin_sequence([PIN])
        btc.get_address(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), show_display=True
        )

    session.refresh_features()
    _assert_busy(session, True)
    assert session.features.unlocked is True

    # Hide the busy dialog.
    device.set_busy(session, None)

    _assert_busy(session, False)
    assert session.features.unlocked is True


@pytest.mark.models("core")
def test_busy_expiry_core(session: Session):
    WAIT_TIME_MS = 1500
    TOLERANCE = 1000

    _assert_busy(session, False)
    # Start a timer
    start = time.monotonic()
    # Show the busy dialog.
    device.set_busy(session, expiry_ms=WAIT_TIME_MS)
    _assert_busy(session, True)

    # Wait until the layout changes
    time.sleep(0.1)  # Improves stability of the test for devices with THP
    session.client.debug.wait_layout()
    end = time.monotonic()

    # Check that the busy dialog was shown for at least WAIT_TIME_MS.
    duration = (end - start) * 1000
    assert WAIT_TIME_MS <= duration <= WAIT_TIME_MS + TOLERANCE

    # Check that the device is no longer busy.
    # Also needs to come back to Homescreen (for UI tests).
    session.refresh_features()
    _assert_busy(session, False)


@pytest.mark.flaky(retries=5)
@pytest.mark.models("legacy")
def test_busy_expiry_legacy(session: Session):
    _assert_busy(session, False)
    # Show the busy dialog.
    device.set_busy(session, expiry_ms=1500)
    _assert_busy(session, True)

    # Hasn't expired yet.
    time.sleep(0.1)
    _assert_busy(session, True)

    # Wait for it to expire. Add some tolerance to account for CI/hardware slowness.
    time.sleep(4.0)

    # Check that the device is no longer busy.
    # Also needs to come back to Homescreen (for UI tests).
    session.refresh_features()
    _assert_busy(session, False)
