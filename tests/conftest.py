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

from __future__ import annotations

import logging
import os
import typing as t
from enum import IntEnum
from pathlib import Path
from time import sleep

import cryptography
import pytest
import xdist
from _pytest.python import IdMaker
from _pytest.reports import TestReport

from trezorlib import debuglink, exceptions, log, messages, models
from trezorlib.client import Channel, ProtocolVersion
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.device import apply_settings
from trezorlib.device import wipe as wipe_device
from trezorlib.transport import Timeout, enumerate_devices, get_transport
from trezorlib.transport.thp.protocol_v1 import ProtocolV1Channel, UnexpectedMagicError

# register rewrites before importing from local package
# so that we see details of failed asserts from this module
pytest.register_assert_rewrite("tests.common")

from . import translations, ui_tests
from .device_handler import BackgroundDeviceHandler
from .emulators import EmulatorWrapper

if t.TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.mark import Mark
    from _pytest.nodes import Node
    from _pytest.terminal import TerminalReporter

    from trezorlib._internal.emulator import Emulator
    from trezorlib.client import TrezorClient
    from trezorlib.debuglink import SessionDebugWrapper


HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "core"

LOG = logging.getLogger(__name__)

LOCK_TIME = 0.2

# So that we see details of failed asserts from this module
pytest.register_assert_rewrite("tests.common")
pytest.register_assert_rewrite("tests.input_flows")
pytest.register_assert_rewrite("tests.input_flows_helpers")


def _emulator_wrapper_main_args() -> list[str]:
    """Look at TREZOR_PROFILING env variable, so that we can generate coverage reports."""
    do_profiling = os.environ.get("TREZOR_PROFILING") == "1"
    if do_profiling:
        src_dir = HERE.parent / "core" / "src"
        # So that the coverage reports have the correct paths
        os.environ["TREZOR_SRC"] = str(src_dir)
        return ["-m", "prof"]
    else:
        return ["-m", "main"]


@pytest.fixture
def core_emulator(request: pytest.FixtureRequest) -> t.Iterator[Emulator]:
    """Fixture returning default core emulator with possibility of screen recording."""
    with EmulatorWrapper("core", main_args=_emulator_wrapper_main_args()) as emu:
        # Modifying emu.client to add screen recording (when --ui=test is used)
        _check_protocol(request, emu.client)
        with ui_tests.screen_recording(emu.client, request, lambda: emu.client) as _:
            yield emu


@pytest.fixture(scope="session")
def emulator(request: pytest.FixtureRequest) -> t.Generator["Emulator", None, None]:
    """Fixture for getting emulator connection in case tests should operate it on their own.

    Is responsible for starting it at the start of the session and stopping
    it at the end of the session - using `with EmulatorWrapper...`.

    Makes sure that each process will run the emulator on a different
    port and with different profile directory, which is cleaned afterwards.

    Used so that we can run the device tests in parallel using `pytest-xdist` plugin.
    Docs: https://pypi.org/project/pytest-xdist/

    NOTE for parallel tests:
    So that all worker processes will explore the tests in the exact same order,
    we cannot use the "built-in" random order, we need to specify our own,
    so that all the processes share the same order.
    Done by appending `--random-order-seed=$RANDOM` as a `pytest` argument,
    using system RNG.
    """

    model = str(request.session.config.getoption("model"))
    interact = os.environ.get("INTERACT") == "1"

    assert model in ("core", "legacy")
    if model == "legacy":
        raise RuntimeError(
            "Legacy emulator is not supported until it can be run on arbitrary ports."
        )

    worker_id = xdist.get_xdist_worker_id(request)
    assert worker_id.startswith("gw")
    worker_id = int(worker_id[2:])

    with EmulatorWrapper(
        model,
        worker_id=worker_id,
        headless=True,
        auto_interact=not interact,
        main_args=_emulator_wrapper_main_args(),
    ) as emu:
        yield emu


@pytest.fixture(scope="session")
def _raw_client(request: pytest.FixtureRequest) -> t.Generator[Client, None, None]:
    client = _get_raw_client(request)
    try:
        yield client
    finally:
        client.close_transport()


def _get_raw_client(request: pytest.FixtureRequest) -> Client:
    # In case tests run in parallel, each process has its own emulator/client.
    # Requesting the emulator fixture only if relevant.
    if request.session.config.getoption("control_emulators"):
        emu_fixture = request.getfixturevalue("emulator")
        client = emu_fixture.client
    else:
        interact = os.environ.get("INTERACT") == "1"
        if not interact:
            # prevent tests from getting stuck in case there is an USB packet loss
            Channel._DEFAULT_READ_TIMEOUT = 50.0

        path = os.environ.get("TREZOR_PATH")
        if path:
            client = _client_from_path(request, path, interact)
        else:
            client = _find_client(request, interact)

    return client


def _client_from_path(
    request: pytest.FixtureRequest, path: str, interact: bool
) -> Client:
    try:
        transport = get_transport(path)
        return Client(transport, auto_interact=not interact, open_transport=True)
    except Exception as e:
        request.session.shouldstop = "Failed to communicate with Trezor"
        raise RuntimeError(f"Failed to open debuglink for {path}") from e


def _find_client(request: pytest.FixtureRequest, interact: bool) -> Client:
    devices = enumerate_devices()
    for device in devices:
        return Client(device, auto_interact=not interact, open_transport=True)

    request.session.shouldstop = "Failed to communicate with Trezor"
    raise RuntimeError("No debuggable device found")


class ModelsFilter:
    MODEL_SHORTCUTS = {
        "core": models.TREZORS - {models.T1B1},
        "legacy": {models.T1B1},
        "t1": {models.T1B1},
        "t2": {models.T2T1},
        "tt": {models.T2T1},
        "safe": {models.T2B1, models.T3T1, models.T3B1, models.T3W1},
        "safe3": {models.T2B1, models.T3B1},
        "safe5": {models.T3T1},
        "delizia": {models.T3T1},
        "eckhart": {models.T3W1},
    }

    def __init__(self, node: Node) -> None:
        markers = node.iter_markers("models")
        self.models = set(models.TREZORS)
        for marker in markers:
            self._refine_by_marker(marker)

    def __contains__(self, model: models.TrezorModel) -> bool:
        return model in self.models

    def __bool__(self) -> bool:
        return bool(self.models)

    def _refine_by_marker(self, marker: Mark) -> None:
        """Apply the marker selector to the current models selection."""
        if marker.args:
            self.models &= self._set_from_marker_list(marker.args)
        if "skip" in marker.kwargs:
            self.models -= self._set_from_marker_list(marker.kwargs["skip"])

    @classmethod
    def _set_from_marker_list(
        cls, marker_list: str | t.Sequence[str] | t.Sequence[models.TrezorModel]
    ) -> set[models.TrezorModel]:
        """Given either a possible value of pytest.mark.models positional args,
        or a value of the `skip` kwarg, return a set of models specified by that value.
        """
        if not marker_list:
            raise ValueError("No models specified")

        if isinstance(marker_list[0], models.TrezorModel):
            # raw list of TrezorModels
            return set(marker_list)  # type: ignore [incompatible with return type]

        if len(marker_list) == 1:
            # @pytest.mark.models("t2t1,t2b1") -> ("t2t1,t2b1",) -> "t2t1,t2b1"
            marker_list = marker_list[0]

        if isinstance(marker_list, str):
            # either a single model / shortcut, or a comma-separated text list
            # @pytest.mark.models("t2t1,t2b1") -> "t2t1,t2b1" -> ["t2t1", "t2b1"]
            marker_list = [s.strip() for s in marker_list.split(",")]

        selected_models = set()
        for marker in marker_list:
            assert isinstance(marker, str)
            if marker in cls.MODEL_SHORTCUTS:
                selected_models |= cls.MODEL_SHORTCUTS[marker]
            elif (model := models.by_internal_name(marker.upper())) is not None:
                selected_models.add(model)
            else:
                raise ValueError(f"Unknown model: {marker}")

        return selected_models


@pytest.fixture(scope="function")
def _client_unlocked(
    request: pytest.FixtureRequest, _raw_client: Client
) -> t.Generator[Client, None, None]:
    """Client fixture.

    Every test function that requires a client instance will get it from here.
    If we can't connect to a debuggable device, the test will fail.
    If 'skip_t2t1' is used and TT is connected, the test is skipped. Vice versa with T1
    and 'skip_t1b1'. Same with T2B1, T3T1.

    The client instance is wiped and preconfigured with "all all all..." mnemonic, no
    password and no pin. It is possible to customize this with the `setup_client`
    marker.

    To specify a custom mnemonic and/or custom pin and/or enable passphrase:

    @pytest.mark.setup_client(mnemonic=MY_MNEMONIC, pin="9999", passphrase=True)

    To receive a client instance that was not initialized:

    @pytest.mark.setup_client(uninitialized=True)

    To enable experimental features:

    @pytest.mark.experimental
    """
    models_filter = ModelsFilter(request.node)
    if _raw_client.model not in models_filter:
        pytest.skip(f"Skipping test for model {_raw_client.model.internal_name}")

    is_btc_only = (
        messages.Capability.Bitcoin_like not in _raw_client.features.capabilities
    )
    if request.node.get_closest_marker("altcoin") and is_btc_only:
        pytest.skip("Skipping altcoin test")

    _check_protocol(request, _raw_client)

    protocol_version = _raw_client.protocol_version

    sd_marker = request.node.get_closest_marker("sd_card")
    if sd_marker and not _raw_client.features.sd_card_present:
        raise RuntimeError(
            "This test requires SD card.\n"
            "To skip all such tests, run:\n"
            "  pytest -m 'not sd_card' <test path>"
        )

    test_ui = request.config.getoption("ui")
    fail_on_gc_leak = not request.config.getoption("ignore_gc_leak")

    _raw_client.reset_debug_features()
    if isinstance(_raw_client.protocol, ProtocolV1Channel):
        try:
            _raw_client.sync_responses()
        except Exception:
            request.session.shouldstop = "Failed to communicate with Trezor"
            pytest.fail("Failed to communicate with Trezor")

    # Resetting all the debug events to not be influenced by previous test
    _raw_client.debug.reset_debug_events()

    # Make sure there are no GC leaks from previous tests
    _raw_client.debug.check_gc_info(fail_on_gc_leak)

    if test_ui:
        # we need to reseed before the wipe
        _raw_client.debug.reseed(0)

    if sd_marker:
        should_format = sd_marker.kwargs.get("formatted", True)
        _raw_client.debug.erase_sd_card(format=should_format)

    while True:
        try:
            if _raw_client.is_invalidated:
                try:
                    _raw_client = _raw_client.get_new_client()
                except exceptions.ThpError as e:
                    LOG.error(f"Failed to re-create a client: {e}")
                    sleep(LOCK_TIME)
                    try:
                        _raw_client = _raw_client.get_new_client()
                    except Exception:
                        sleep(LOCK_TIME)
                        _raw_client = _get_raw_client(request)

            session = _raw_client.get_seedless_session()
            wipe_device(session)
            if protocol_version is ProtocolVersion.V2:
                sleep(LOCK_TIME)  # Makes tests more stable (wait for wipe to finish)
            break
        except cryptography.exceptions.InvalidTag:
            # Get a new client
            _raw_client = _get_raw_client(request)

    _raw_client.reset_protocol()

    if not _raw_client.features.bootloader_mode:
        _raw_client.refresh_features()

    # Load language again, as it got erased in wipe
    if _raw_client.model is not models.T1B1:
        lang = request.session.config.getoption("lang") or "en"
        assert isinstance(lang, str)
        translations.set_language(_raw_client.get_seedless_session(), lang)

    setup_params = dict(
        uninitialized=False,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase=False,
        needs_backup=False,
        no_backup=False,
    )

    marker = request.node.get_closest_marker("setup_client")
    if marker:
        setup_params.update(marker.kwargs)

    use_passphrase = setup_params["passphrase"] is True or isinstance(
        setup_params["passphrase"], str
    )
    if not setup_params["uninitialized"]:
        session = _raw_client.get_seedless_session()
        debuglink.load_device(
            session,
            mnemonic=setup_params["mnemonic"],  # type: ignore
            pin=setup_params["pin"],  # type: ignore
            passphrase_protection=use_passphrase,
            label="test",
            needs_backup=setup_params["needs_backup"],  # type: ignore
            no_backup=setup_params["no_backup"],  # type: ignore
            _skip_init_device=False,
        )
        _raw_client._setup_pin = setup_params["pin"]

        if request.node.get_closest_marker("experimental"):
            apply_settings(session, experimental_features=True)
        session.end()

    try:
        yield _raw_client
    finally:
        # Make sure there are no GC leaks from this test
        _raw_client.debug.check_gc_info(fail_on_gc_leak)


@pytest.fixture(scope="function")
def client(
    request: pytest.FixtureRequest, _client_unlocked: Client
) -> t.Generator[Client, None, None]:
    _client_unlocked.lock()
    if bool(request.node.get_closest_marker("invalidate_client")):
        with ui_tests.screen_recording(_client_unlocked, request):
            try:
                yield _client_unlocked
            finally:
                _client_unlocked.invalidate()
    else:
        with ui_tests.screen_recording(_client_unlocked, request):
            yield _client_unlocked


@pytest.fixture(scope="function")
def session(
    request: pytest.FixtureRequest, _client_unlocked: Client
) -> t.Generator[SessionDebugWrapper, None, None]:
    if bool(request.node.get_closest_marker("uninitialized_session")):
        session = _client_unlocked.get_seedless_session()
    else:
        derive_cardano = bool(request.node.get_closest_marker("cardano"))
        passphrase = ""
        marker = request.node.get_closest_marker("setup_client")
        if marker and isinstance(marker.kwargs.get("passphrase"), str):
            passphrase = marker.kwargs["passphrase"]
        if _client_unlocked._setup_pin is not None:
            _client_unlocked.use_pin_sequence([_client_unlocked._setup_pin])
        session = _client_unlocked.get_session(
            derive_cardano=derive_cardano, passphrase=passphrase
        )

    if _client_unlocked._setup_pin is not None:
        session.lock()
    with ui_tests.screen_recording(_client_unlocked, request):
        yield session
    # Calling session.end() is not needed since the device gets wiped later anyway.


def _check_protocol(request: pytest.FixtureRequest, client: TrezorClient) -> None:
    protocol_marker: Mark | None = request.node.get_closest_marker("protocol")
    if not protocol_marker:
        return

    protocol_version = ProtocolVersion(client.protocol_version)
    expected_marker = f"protocol_{protocol_version.name.lower()}"

    if expected_marker not in protocol_marker.args:
        pytest.skip(f"Test does not support Protocol{protocol_version.name}.")


def _is_main_runner(session_or_request: pytest.Session | pytest.FixtureRequest) -> bool:
    """Return True if the current process is the main test runner.

    In case tests are run in parallel, the main runner is the xdist controller.
    We cannot use `is_xdist_controller` directly because it is False when xdist is
    not used.
    """
    return xdist.get_xdist_worker_id(session_or_request) == "master"


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.getoption("ui"):
        ui_tests.setup(main_runner=_is_main_runner(session))


def pytest_sessionfinish(session: pytest.Session, exitstatus: pytest.ExitCode) -> None:
    test_ui = session.config.getoption("ui")
    if test_ui and _is_main_runner(session):
        session.exitstatus = ui_tests.sessionfinish(
            exitstatus,
            test_ui,  # type: ignore
            bool(session.config.getoption("ui_check_missing")),
            bool(session.config.getoption("do_master_diff")),
        )


def pytest_terminal_summary(
    terminalreporter: "TerminalReporter", exitstatus: pytest.ExitCode, config: "Config"
) -> None:
    println = terminalreporter.write_line
    println("")

    ui_option = config.getoption("ui")
    if ui_option:
        ui_tests.terminal_summary(
            terminalreporter.write_line,
            ui_option,  # type: ignore
            bool(config.getoption("ui_check_missing")),
            exitstatus,
        )


def pytest_addoption(parser: "Parser") -> None:
    parser.addoption(
        "--ui",
        action="store",
        choices=["test", "record"],
        help="Enable UI integration tests: 'record' or 'test'",
    )
    parser.addoption(
        "--ui-check-missing",
        action="store_true",
        default=False,
        help="Check UI fixtures are containing the appropriate test cases (fails on `test`,"
        "deletes old ones on `record`).",
    )
    parser.addoption(
        "--control-emulators",
        action="store_true",
        default=False,
        help="Pytest will be responsible for starting and stopping the emulators. "
        "Useful when running tests in parallel.",
    )
    parser.addoption(
        "--model",
        action="store",
        choices=["core", "legacy"],
        help="Which emulator to use: 'core' or 'legacy'. "
        "Only valid in connection with `--control-emulators`",
    )
    parser.addoption(
        "--record-text-layout",
        action="store_true",
        default=False,
        help="Saving debugging traces for each screen change. "
        "Will generate a report with text from all test-cases.",
    )
    parser.addoption(
        "--do-master-diff",
        action="store_true",
        default=False,
        help="Generating a master-diff report. "
        "This shows all unique differing screens compared to master.",
    )
    parser.addoption(
        "--lang",
        action="store",
        choices=translations.LANGUAGES,
        help="Run tests with a specified language: 'en' is the default",
    )
    parser.addoption(
        "--verbose-log-file",
        action="store",
        default=None,
        help="File path for verbose logging",
    )
    parser.addoption(
        "--ignore-gc-leak",
        action="store_true",
        default=False,
        help="Issue a warning when GC leak detected (otherwise, fail the test)",
    )


def pytest_configure(config: "Config") -> None:
    """Called at testsuite setup time.

    Registers known markers, enables verbose output if requested.
    """
    # register known markers
    config.addinivalue_line(
        "markers",
        'models("core", "t1b1", ..., skip=[...], reason="..."): select which models or families to run the test on',
    )
    config.addinivalue_line(
        "markers", "experimental: enable experimental features on Trezor"
    )
    config.addinivalue_line(
        "markers",
        'setup_client(mnemonic="all all all...", pin=None, passphrase=False, uninitialized=False): configure the client instance',
    )
    config.addinivalue_line(
        "markers",
        "uninitialized_session: use uninitialized session instance",
    )
    config.addinivalue_line(
        "markers",
        "invalidate_client: invalidate client after test",
    )
    with open(os.path.join(os.path.dirname(__file__), "REGISTERED_MARKERS")) as f:
        for line in f:
            config.addinivalue_line("markers", line.strip())

    # enable debug if `-v` flag is passed (use multiple times for higher verbosity)
    verbosity = config.getoption("verbose")
    if verbosity:
        log.enable_debug_output(verbosity)

        verbose_log_file = config.getoption("verbose_log_file")
        if verbose_log_file:
            handler = logging.FileHandler(verbose_log_file)
            log.enable_debug_output(verbosity, handler)

    idval_orig = IdMaker._idval_from_value

    def idval_from_value(self: IdMaker, val: object) -> str | None:
        if isinstance(val, IntEnum):
            return f"{type(val).__name__}.{val.name}"
        return idval_orig(self, val)

    IdMaker._idval_from_value = idval_from_value


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Called for each test item (class, individual tests).

    Ensures that altcoin tests are skipped, and that no test is skipped for all models.
    """
    models_filter = ModelsFilter(item)
    if not models_filter:
        raise RuntimeError("Don't skip tests for all trezor models!")


def pytest_set_filtered_exceptions():
    return (Timeout, UnexpectedMagicError)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call) -> t.Generator:
    # Make test results available in fixtures.
    # See https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    # The device_handler fixture uses this as 'request.node.rep_call.passed' attribute,
    # in order to raise error only if the test passed.
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(
    report: TestReport, config: Config
) -> tuple[str, str, tuple[str, dict[str, bool]]] | None:
    if report.passed:
        for prop, _ in report.user_properties:
            if prop == "ui_failed":
                return "ui_failed", "U", ("UI-FAILED", {"red": True})
            if prop == "ui_missing":
                return "ui_missing", "M", ("UI-MISSING", {"yellow": True})
    # else use default handling
    return None


@pytest.fixture
def device_handler(client: Client, request: pytest.FixtureRequest) -> t.Generator:
    device_handler = BackgroundDeviceHandler(client)
    yield device_handler

    # get call test result
    test_res = ui_tests.common.get_last_call_test_result(request)

    if test_res is None:
        return

    # if test finished, make sure all background tasks are done
    finalized_ok = device_handler.check_finalize()
    if test_res and not finalized_ok:  # type: ignore [rep_call must exist]
        raise RuntimeError("Test did not check result of background task")
