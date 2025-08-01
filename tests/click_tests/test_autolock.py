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

import math
import time
from typing import TYPE_CHECKING, Tuple

import pytest

from trezorlib import btc, device, exceptions, messages
from trezorlib.client import PASSPHRASE_ON_DEVICE
from trezorlib.debuglink import DebugLink, LayoutType
from trezorlib.protobuf import MessageType
from trezorlib.tools import parse_path

from .. import common
from .. import translations as TR
from ..device_tests.bitcoin.coinjoin_req import make_coinjoin_request
from ..tx_cache import TxCache
from . import recovery
from .common import go_next, unlock_gesture

if TYPE_CHECKING:
    from trezorlib.debuglink import LayoutContent

    from ..device_handler import BackgroundDeviceHandler

TX_CACHE_MAINNET = TxCache("Bitcoin")
TX_CACHE_TESTNET = TxCache("Testnet")

FAKE_TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
FAKE_TXHASH_f982c0 = bytes.fromhex(
    "f982c0a283bd65a59aa89eded9e48f2a3319cb80361dfab4cf6192a03badb60a"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)

PIN4 = "1234"


def _passphrase_j(debug: DebugLink) -> Tuple[int, int]:
    if debug.layout_type is LayoutType.Bolt:
        return debug.screen_buttons.pin_passphrase_grid(1, 1)
    else:
        return debug.screen_buttons.pin_passphrase_grid(0, 1)


def _center_button(debug: DebugLink) -> Tuple[int, int]:
    return debug.screen_buttons.pin_passphrase_grid(1, 1)


def set_autolock_delay(device_handler: "BackgroundDeviceHandler", delay_ms: int):
    debug = device_handler.debuglink()
    session = device_handler.get_session()
    debug.synchronize_at("PinKeyboard")
    debug.input("1234")
    session = device_handler.result()

    device_handler.run_with_provided_session(session, device.apply_settings, auto_lock_delay_ms=delay_ms)  # type: ignore

    debug.synchronize_at(TR.auto_lock__title)
    assert TR.regexp("auto_lock__change_template").match(
        debug.read_layout().text_content().strip()
    )

    layout = go_next(debug)
    if debug.layout_type is LayoutType.Delizia:
        debug.click(debug.screen_buttons.tap_to_confirm())
        layout = debug.read_layout()
    assert layout.main_component() == "Homescreen"
    device_handler.result()
    return session


@pytest.mark.setup_client(pin=PIN4)
def test_autolock_interrupts_signing(device_handler: "BackgroundDeviceHandler"):
    """Autolock will lock the device that is waiting for the user
    to confirm transaction."""
    session = set_autolock_delay(device_handler, 10_000)

    debug = device_handler.debuglink()
    # try to sign a transaction
    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    device_handler.run_with_provided_session(session, btc.sign_tx, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)  # type: ignore

    debug.synchronize_at([TR.words__send, TR.words__address, TR.words__recipient])
    assert (
        "1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1"
        in debug.read_layout().text_content().replace(" ", "")
    )

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ok())
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.swipe_up()
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        debug.press_right()
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    # wait for autolock to kick in
    time.sleep(10.1)
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4)
def test_autolock_does_not_interrupt_signing(device_handler: "BackgroundDeviceHandler"):
    """Autolock will NOT lock the device once transaction is confirmed."""
    set_autolock_delay(device_handler, 10_000)

    debug = device_handler.debuglink()

    # Prepare session to use later
    session = device_handler.client.get_session()

    # try to sign a transaction
    inp1 = messages.TxInputType(
        address_n=parse_path("86h/0h/0h/0/0"),
        amount=390000,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    device_handler.run_with_provided_session(
        session, btc.sign_tx, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
    )

    debug.synchronize_at([TR.words__send, TR.words__address, TR.words__recipient])
    assert (
        "1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1"
        in debug.read_layout().text_content().replace(" ", "")
    )

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ok())
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.swipe_up()
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
        debug.swipe_up()
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        debug.press_right()
        layout = debug.read_layout()
        assert TR.send__total_amount in layout.text_content()
        assert "0.0039 BTC" in layout.text_content()
    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    client = session.client

    def sleepy_filter(msg: MessageType) -> MessageType:
        time.sleep(10.1)
        client.set_filter(messages.TxAck, None)
        return msg

    with client:
        client.set_filter(messages.TxAck, sleepy_filter)
        # confirm transaction
        # don't wait for layout change, to avoid "layout deadlock detected" error
        if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
            debug.click(debug.screen_buttons.ok(), wait=False)
        elif debug.layout_type is LayoutType.Caesar:
            debug.press_middle(wait=False)
        elif debug.layout_type is LayoutType.Delizia:
            debug.click(debug.screen_buttons.tap_to_confirm(), wait=False)
        else:
            raise ValueError(f"Unsupported layout type: {debug.layout_type}")

        signatures, tx = device_handler.result()
        assert len(signatures) == 1
        assert tx
    assert device_handler.features().unlocked is False


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_passphrase_keyboard(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.get_session(passphrase=PASSPHRASE_ON_DEVICE)  # type: ignore
    debug.synchronize_at("PassphraseKeyboard")

    if debug.layout_type is LayoutType.Caesar:
        # Going into the selected character category
        debug.press_middle()

    # enter passphrase - slowly
    # keep clicking for long enough to trigger the autolock if it incorrectly ignored key presses
    for _ in range(math.ceil(11 / 1.5)):
        if debug.layout_type in (
            LayoutType.Bolt,
            LayoutType.Delizia,
            LayoutType.Eckhart,
        ):
            # click at "j"
            debug.click(_passphrase_j(debug))
        elif debug.layout_type is LayoutType.Caesar:
            # just go right
            # NOTE: because of passphrase randomization it would be a pain to input
            # a specific passphrase, which is not in scope for this test.
            debug.press_right()
        else:
            raise ValueError(f"Unsupported layout type: {debug.layout_type}")

        time.sleep(1.5)

    # Send the passphrase to the client (TT has it clicked already, TR needs to input it)
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.passphrase_confirm())
    elif debug.layout_type is LayoutType.Caesar:
        debug.input("j" * 8)

    session = device_handler.result()

    # get address corresponding to "jjjjjjjj" passphrase
    device_handler.run_with_provided_session(session, common.get_test_address)
    assert device_handler.result() == "mnF4yRWJXmzRB6EuBzuVigqeqTqirQupxJ"


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_interrupts_passphrase(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # get address (derive_seed)
    device_handler.get_session(passphrase=PASSPHRASE_ON_DEVICE)
    debug.synchronize_at("PassphraseKeyboard")

    if debug.layout_type is LayoutType.Caesar:
        # Going into the selected character category
        debug.press_middle()

    # enter passphrase - slowly
    # autolock must activate even if we pressed some buttons
    for _ in range(math.ceil(6 / 1.5)):
        if debug.layout_type in (
            LayoutType.Bolt,
            LayoutType.Delizia,
            LayoutType.Eckhart,
        ):
            debug.click(_center_button(debug))
        elif debug.layout_type is LayoutType.Caesar:
            debug.press_middle()
        else:
            raise ValueError(f"Unsupported layout type: {debug.layout_type}")
        time.sleep(1.5)

    # wait for autolock to kick in
    time.sleep(10.1)
    if debug.layout_type is LayoutType.Eckhart:
        assert debug.read_layout().main_component() == "Homescreen"
    else:
        assert debug.read_layout().main_component() == "Lockscreen"
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def unlock_dry_run(debug: "DebugLink") -> "LayoutContent":
    debug.synchronize_at(
        [TR.recovery__title_dry_run, TR.reset__check_wallet_backup_title]
    )
    layout = go_next(debug)
    assert "PinKeyboard" in layout.all_components()

    debug.input(PIN4)
    layout = debug.read_layout()
    assert layout is not None
    return layout


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_number_of_words(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run_with_session(device.recover, type=messages.RecoveryType.DryRun)

    layout = unlock_dry_run(debug)
    assert TR.recovery__num_of_words in debug.read_layout().text_content()

    if debug.layout_type is LayoutType.Caesar:
        debug.press_right()

    # wait for autolock to trigger
    time.sleep(10.1)
    if debug.layout_type is LayoutType.Eckhart:
        assert debug.read_layout().main_component() == "Homescreen"
    else:
        assert debug.read_layout().main_component() == "Lockscreen"
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()

    # unlock
    # lockscreen triggered automatically
    # debug.wait_layout()
    layout = unlock_gesture(debug)

    assert "PinKeyboard" in layout.all_components()
    debug.input(PIN4)
    layout = debug.read_layout()
    assert layout is not None

    # we are back at homescreen
    assert TR.recovery__num_of_words in debug.read_layout().text_content()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_word_entry(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run_with_session(device.recover, type=messages.RecoveryType.DryRun)

    unlock_dry_run(debug)

    # select 20 words
    recovery.select_number_of_words(debug, 20)

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        layout = go_next(debug)
        assert layout.main_component() == "MnemonicKeyboard"
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        layout = debug.read_layout()
        assert "MnemonicKeyboard" in layout.all_components()
    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    # make sure keyboard locks
    time.sleep(10.1)
    if debug.layout_type is LayoutType.Eckhart:
        assert debug.read_layout().main_component() == "Homescreen"
    else:
        assert debug.read_layout().main_component() == "Lockscreen"
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_enter_word_slowly(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run_with_session(device.recover, type=messages.RecoveryType.DryRun)

    unlock_dry_run(debug)

    # select 20 words
    recovery.select_number_of_words(debug, 20)

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()
        assert layout.main_component() == "MnemonicKeyboard"

        # type the word OCEAN slowly
        for coords in debug.button_actions.type_word("ocea", is_slip39=True):
            time.sleep(9)
            debug.click(coords)
        debug.click(debug.screen_buttons.mnemonic_confirm())
        layout = debug.read_layout()
        # should not have locked, even though we took 9 seconds to type each letter
        assert layout.main_component() == "MnemonicKeyboard"

    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        layout = debug.read_layout()
        assert layout.main_component() == "MnemonicKeyboard"

        # type the word OCEAN slowly
        for coords in debug.button_actions.type_word("ocea", is_slip39=True):
            time.sleep(9)
            debug.click(coords)
        debug.click(debug.screen_buttons.mnemonic_confirm())
        layout = debug.read_layout()
        # should not have locked, even though we took 9 seconds to type each letter
        assert layout.main_component() == "MnemonicKeyboard"

    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        layout = debug.read_layout()
        assert "MnemonicKeyboard" in layout.all_components()

        # pressing middle button three times
        for _ in range(3):
            time.sleep(9)
            debug.press_middle()
        layout = debug.read_layout()
        # should not have locked, even though we took 9 seconds to type each letter
        assert "MnemonicKeyboard" in layout.all_components()

    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.models(skip="eckhart")  # FIXME: broken with THP
@pytest.mark.setup_client(pin=PIN4)
def test_autolock_does_not_interrupt_preauthorized(
    device_handler: "BackgroundDeviceHandler",
):
    # NOTE: FAKE input tx
    # NOTE: mostly copy-pasted from test_authorize_coinjoin.py::test_sign_tx
    session = set_autolock_delay(device_handler, 10_000)

    debug = device_handler.debuglink()

    # Prepare session to use later

    device_handler.run_with_provided_session(
        session,
        btc.authorize_coinjoin,
        coordinator="www.example.com",
        max_rounds=2,
        max_coordinator_fee_rate=500_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    debug.press_yes()
    device_handler.result()

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/0/0
            # tb1pkw382r3plt8vx6e22mtkejnqrxl4z7jugh3w4rjmfmgezzg0xqpsdaww8z
            amount=100_000,
            prev_hash=FAKE_TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex(
                "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
            ),
            ownership_proof=bytearray.fromhex(
                "534c001901019cf1b0ad730100bd7a69e987d55348bb798e2b2096a6a5713e9517655bd2021300014052d479f48d34f1ca6872d4571413660040c3e98841ab23a2c5c1f37399b71bfa6f56364b79717ee90552076a872da68129694e1b4fb0e0651373dcf56db123c5"
            ),
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(32, "big"),
        ),
        messages.TxInputType(
            address_n=parse_path("m/10025h/1h/0h/1h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        ),
    ]

    input_script_pubkeys = [
        bytes.fromhex(
            "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
        ),
        bytes.fromhex(
            "51202f436892d90fb2665519efa3d9f0f5182859124f179486862c2cd7a78ea9ac19"
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/0
            address="tb1pupzczx9cpgyqgtvycncr2mvxscl790luqd8g88qkdt2w3kn7ymhsrdueu2",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1phkcspf88hge86djxgtwx2wu7ddghsw77d6sd7txtcxncu0xpx22shcydyf
            address_n=parse_path("m/10025h/1h/0h/1h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp
            address_n=parse_path("m/10025h/1h/0h/1h/1/2"),
            amount=7_289_000 - 50_000 - 36_445 - 490,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Other's change output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/1
            address="tb1pvt7lzserh8xd5m6mq0zu9s5wxkpe5wgf5ts56v44jhrr6578hz8saxup5m",
            amount=100_000 - 50_000 - 500 - 490,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=36_945,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
    ]

    output_script_pubkeys = [
        bytes.fromhex(
            "5120e0458118b80a08042d84c4f0356d86863fe2bffc034e839c166ad4e8da7e26ef"
        ),
        bytes.fromhex(
            "5120bdb100a4e7ba327d364642dc653b9e6b51783bde6ea0df2ccbc1a78e3cc13295"
        ),
        bytes.fromhex(
            "5120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e"
        ),
        bytes.fromhex(
            "512062fdf14323b9ccda6f5b03c5c2c28e35839a3909a2e14d32b595c63d53c7b88f"
        ),
        bytes.fromhex("76a914a579388225827d9f2fe9014add644487808c695d88ac"),
    ]

    coinjoin_req = make_coinjoin_request(
        "www.example.com",
        inputs,
        input_script_pubkeys,
        outputs,
        output_script_pubkeys,
        no_fee_indices=[],
    )

    client = session.client

    def sleepy_filter(msg: MessageType) -> MessageType:
        time.sleep(10.1)
        client.set_filter(messages.SignTx, None)
        return msg

    with client:
        # Start DoPreauthorized flow when device is unlocked. Wait 10s before
        # delivering SignTx, by that time autolock timer should have fired.
        client.set_filter(messages.SignTx, sleepy_filter)
        device_handler.run_with_provided_session(
            session,
            btc.sign_tx,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            coinjoin_request=coinjoin_req,
            preauthorized=True,
            serialize=False,
        )
        signatures, _ = device_handler.result()

    assert len(signatures) == 2
    assert signatures[0] is None
    assert (
        signatures[1].hex()
        == "c017fce789fa8db54a2ae032012d2dd6d7c76cc1c1a6f00e29b86acbf93022da8aa559009a574792c7b09b2535d288d6e03c6ed169902ed8c4c97626a83fbc11"
    )
    assert device_handler.features().unlocked is False
