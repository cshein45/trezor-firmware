# This file is part of the Trezor project.
#
# Copyright (C) 2012-2023 SatoshiLabs and contributors
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
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator, Optional

import pytest

from trezorlib import messages
from trezorlib.client import PASSPHRASE_ON_DEVICE
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session

from ..common import TEST_ADDRESS_N
from .common import CommonPass, PassphraseCategory, get_char_category

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("t2t1", "delizia", "eckhart")

KEYBOARD_CATEGORIES_BOLT = [
    PassphraseCategory.Numeric,
    PassphraseCategory.LettersLower,
    PassphraseCategory.LettersUpper,
    PassphraseCategory.Special,
]

# Common for Delizia and Eckhart
KEYBOARD_CATEGORIES_DE = [
    PassphraseCategory.LettersLower,
    PassphraseCategory.LettersUpper,
    PassphraseCategory.Numeric,
    PassphraseCategory.Special,
]

# TODO: better read this from the trace
KEYBOARD_CATEGORY = PassphraseCategory.LettersLower
COORDS_PREV: tuple[int, int] = (0, 0)

# Testing the maximum length is really 50

DA_50 = 25 * "da"
DA_50_ADDRESS = "mg5L2i8HZKUvceK1sfmGHhE4gichFSsdvm"
assert len(DA_50) == 50

DA_49 = DA_50[:-1]
DA_49_ADDRESS = "mxrB75ydMS3ZzqmYKK28fj4bNMEx7dDw6e"
assert len(DA_49) == 49
assert DA_49_ADDRESS != DA_50_ADDRESS

DA_51 = DA_50 + "d"
DA_51_ADDRESS = DA_50_ADDRESS
assert len(DA_51) == 51
assert DA_51_ADDRESS == DA_50_ADDRESS


def _get_test_address(session: Session) -> None:
    resp = session.call_raw(
        messages.GetAddress(address_n=TEST_ADDRESS_N, coin_name="Testnet")
    )
    if isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    if isinstance(resp, messages.PassphraseRequest):
        resp = session.call_raw(messages.PassphraseAck(on_device=True))
    if isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    assert isinstance(resp, messages.Address)
    return resp.address


@contextmanager
def prepare_passphrase_dialogue(
    device_handler: "BackgroundDeviceHandler", address: Optional[str] = None
) -> Generator["DebugLink", None, None]:
    debug = device_handler.debuglink()
    device_handler.get_session(passphrase=PASSPHRASE_ON_DEVICE)
    debug.synchronize_at("PassphraseKeyboard")

    # Resetting the category as it could have been changed by previous tests
    global KEYBOARD_CATEGORY
    KEYBOARD_CATEGORY = PassphraseCategory.LettersLower  # type: ignore

    yield debug
    session = device_handler.result()

    device_handler.run_with_provided_session(session, _get_test_address)  # type: ignore
    result = device_handler.result()
    if address is not None:
        assert result == address


def keyboard_categories(layout_type: LayoutType) -> list[PassphraseCategory]:
    if layout_type is LayoutType.Bolt:
        return KEYBOARD_CATEGORIES_BOLT
    elif layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
        return KEYBOARD_CATEGORIES_DE
    else:
        raise ValueError("Wrong layout type")


def go_to_category(
    debug: "DebugLink", category: PassphraseCategory, verify_layout: bool = False
) -> None:
    """
    Go to a specific category on the passphrase keyboard.

    Navigates through the on-screen categories by swiping left or right
    until the desired category is reached. If `verify_layout` is set to True,
    the function will assert that the category change has been correctly applied
    by reading and validating the current layout from the debug interface.
    """
    global KEYBOARD_CATEGORY
    global COORDS_PREV

    # Already there
    if KEYBOARD_CATEGORY == category:
        return

    current_index = keyboard_categories(debug.layout_type).index(KEYBOARD_CATEGORY)
    target_index = keyboard_categories(debug.layout_type).index(category)
    if target_index > current_index:
        for _ in range(target_index - current_index):
            debug.swipe_left()
    else:
        for _ in range(current_index - target_index):
            debug.swipe_right()
    if verify_layout:
        layout = debug.read_layout().find_unique_value_by_key(
            "active_layout", default="", only_type=str
        )
        # do the check if Rust debug string exists
        if layout:
            assert (
                layout in PassphraseCategory.__members__
            ), f"Unknown layout name from debug: {layout}"
            assert (
                PassphraseCategory[layout] == category
            ), f"Layout mismatch: expected {category}, got {PassphraseCategory[layout]}"

    KEYBOARD_CATEGORY = category  # type: ignore
    # Category changed, reset coordinates
    COORDS_PREV = (0, 0)  # type: ignore


def press_char(debug: "DebugLink", char: str) -> None:
    """Press a character"""
    global COORDS_PREV

    # Space and couple others are a special case
    if char in " *#":
        char_category = PassphraseCategory.LettersLower
    else:
        char_category = get_char_category(char)

    go_to_category(debug, char_category)

    coords, amount = debug.button_actions.passphrase(char)
    # If the button is the same as for the previous char,
    # waiting a second before pressing it again.
    # (not for a space in Bolt layout)
    is_bolt_space = debug.layout_type is LayoutType.Bolt and char == " "
    if coords == COORDS_PREV and not is_bolt_space:
        time.sleep(1.1)
    COORDS_PREV = coords  # type: ignore
    for _ in range(amount):
        debug.click(coords)


def input_passphrase(debug: "DebugLink", passphrase: str, check: bool = True) -> None:
    """Input a passphrase with validation it got added"""
    if check:
        before = debug.read_layout().passphrase()
    for char in passphrase:
        press_char(debug, char)
    if check:
        after = debug.read_layout().passphrase()
        assert after == before + passphrase


def enter_passphrase(debug: "DebugLink") -> None:
    """Enter a passphrase"""
    is_empty: bool = len(debug.read_layout().passphrase()) == 0
    debug.click(debug.screen_buttons.passphrase_confirm())
    if is_empty and debug.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ui_yes())


def delete_char(debug: "DebugLink") -> None:
    """Deletes the last char"""
    debug.click(debug.screen_buttons.pin_passphrase_erase())


VECTORS = (  # passphrase, address
    (CommonPass.SHORT, CommonPass.SHORT_ADDRESS),
    (CommonPass.WITH_SPACE, CommonPass.WITH_SPACE_ADDRESS),
    (CommonPass.RANDOM_25, CommonPass.RANDOM_25_ADDRESS),
    (DA_49, DA_49_ADDRESS),
    (DA_50, DA_50_ADDRESS),
)


@pytest.mark.parametrize("passphrase, address", VECTORS)
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input(
    device_handler: "BackgroundDeviceHandler", passphrase: str, address: str
):
    with prepare_passphrase_dialogue(device_handler, address) as debug:
        input_passphrase(debug, passphrase)
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input_over_50_chars(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, DA_51_ADDRESS) as debug:  # type: ignore
        input_passphrase(debug, DA_51, check=False)
        assert debug.read_layout().passphrase() == DA_50
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_delete(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.SHORT_ADDRESS) as debug:
        input_passphrase(debug, CommonPass.SHORT[:8])

        for _ in range(4):
            delete_char(debug)
        if debug.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
            debug.read_layout()

        input_passphrase(debug, CommonPass.SHORT[8 - 4 :])
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_delete_all(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        passphrase = "trezor"
        input_passphrase(debug, passphrase)

        for _ in range(len(passphrase)):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_loop_all_characters(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        for category in (
            PassphraseCategory.Numeric,
            PassphraseCategory.LettersLower,
            PassphraseCategory.LettersUpper,
            PassphraseCategory.Special,
        ):
            go_to_category(debug, category, True)
        if debug.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
            debug.read_layout()

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_click_same_button_many_times(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        a_coords, _ = debug.button_actions.passphrase("a")
        for _ in range(10):
            debug.click(a_coords)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_prompt_disappears(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        input_passphrase(debug, "a")

        # Wait a second for the prompt to disappear
        time.sleep(1.1)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_long_spaces_deletion(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        input_passphrase(
            debug,
            "a"
            + " " * 7
            + "b"
            + " " * 7
            + "c"
            + " " * 7
            + "d"
            + " " * 7
            + "e"
            + " " * 7
            + "f",
        )
        for _ in range(12):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_dollar_sign_deletion(
    device_handler: "BackgroundDeviceHandler",
):
    # Checks that dollar signs will not leave one pixel on the top after deleting
    # (was a bug previously on model T)
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        passphrase = "$$ I want $$"
        input_passphrase(debug, passphrase)

        for _ in range(len(passphrase)):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_cycle_through_last_character(
    device_handler: "BackgroundDeviceHandler",
):
    # Checks that we can cycle through the last (50th) passphrase character
    # (was a bug previously)
    with prepare_passphrase_dialogue(device_handler) as debug:
        passphrase = DA_49 + "i"  # for i we need to cycle through "ghi" three times
        input_passphrase(debug, passphrase)
        enter_passphrase(debug)
