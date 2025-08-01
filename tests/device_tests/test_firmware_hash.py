from hashlib import blake2s

import pytest

from trezorlib import firmware, models
from trezorlib.debuglink import SessionDebugWrapper as Session

# size of FIRMWARE_MAXSIZE, see core/embed/models/<model>/model_<model>.h
FIRMWARE_LENGTHS = {
    models.T1B1: 7 * 128 * 1024 + 64 * 1024,
    models.T2T1: 13 * 128 * 1024,
    models.T2B1: 13 * 128 * 1024,
    models.T3T1: 208 * 8 * 1024,
    models.T3B1: 208 * 8 * 1024,
    models.T3W1: 417 * 8 * 1024,
}


def test_firmware_hash_emu(session: Session) -> None:
    if session.features.fw_vendor != "EMULATOR":
        pytest.skip("Only for emulator")

    data = b"\xff" * FIRMWARE_LENGTHS[session.model]

    expected_hash = blake2s(data).digest()
    hash = firmware.get_hash(session, None)
    assert hash == expected_hash

    challenge = b"Hello Trezor"
    expected_hash = blake2s(data, key=challenge).digest()
    hash = firmware.get_hash(session, challenge)
    assert hash == expected_hash


def test_firmware_hash_hw(session: Session) -> None:
    if session.features.fw_vendor == "EMULATOR":
        pytest.skip("Only for hardware")

    # TODO get firmware image from outside the environment, check for actual result
    challenge = b"Hello Trezor"
    empty_data = b"\xff" * FIRMWARE_LENGTHS[session.model]
    empty_hash = blake2s(empty_data).digest()
    empty_hash_challenge = blake2s(empty_data, key=challenge).digest()

    hash = firmware.get_hash(session, None)
    assert hash != empty_hash

    hash2 = firmware.get_hash(session, challenge)
    assert hash != hash2
    assert hash2 != empty_hash_challenge
