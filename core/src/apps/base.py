from typing import TYPE_CHECKING

import storage.device as storage_device
from storage.cache_common import APP_COMMON_BUSY_DEADLINE_MS, APP_COMMON_SEED
from trezor import TR, config, utils, wire, workflow
from trezor.enums import HomescreenFormat, MessageType
from trezor.messages import Success, UnlockPath
from trezor.ui.layouts import confirm_action
from trezor.wire import context
from trezor.wire.message_handler import filters, remove_filter

from . import workflow_handlers

if TYPE_CHECKING:
    from typing import NoReturn

    from trezor import protobuf
    from trezor.messages import (
        Cancel,
        CancelAuthorization,
        DoPreauthorized,
        EndSession,
        Features,
        GetFeatures,
        Initialize,
        LockDevice,
        Ping,
        SetBusy,
    )
    from trezor.wire import Handler, Msg

    if utils.USE_THP:
        from trezor.messages import (
            Failure,
            ThpCreateNewSession,
            ThpCredentialRequest,
            ThpCredentialResponse,
        )


_SCREENSAVER_IS_ON = False


def busy_expiry_ms() -> int:
    """
    Returns the time left until the busy state expires or 0 if the device is not in the busy state.
    """

    busy_deadline_ms = context.cache_get_int(APP_COMMON_BUSY_DEADLINE_MS)
    if busy_deadline_ms is None:
        return 0

    import utime

    expiry_ms = utime.ticks_diff(busy_deadline_ms, utime.ticks_ms())
    return expiry_ms if expiry_ms > 0 else 0


def _language_version_matches() -> bool | None:
    """
    Whether translation blob version matches firmware version.
    Returns None if there is no blob.
    """
    from trezor import translations

    header = translations.TranslationsHeader.load_from_flash()
    if header is None:
        return True

    return header.version == utils.VERSION


def get_features() -> Features:
    import storage.recovery as storage_recovery
    from trezor import translations
    from trezor.enums import BackupAvailability, Capability, RecoveryStatus
    from trezor.messages import Features
    from trezor.ui import HEIGHT, WIDTH

    from apps.common import backup, mnemonic, safety_checks

    v_major, v_minor, v_patch, _v_build = utils.VERSION

    f = Features(
        vendor="trezor.io",
        fw_vendor=utils.firmware_vendor(),
        language=translations.get_language(),
        language_version_matches=_language_version_matches(),
        major_version=v_major,
        minor_version=v_minor,
        patch_version=v_patch,
        revision=utils.SCM_REVISION,
        model=utils.MODEL,
        internal_model=utils.INTERNAL_MODEL,
        device_id=storage_device.get_device_id(),
        label=storage_device.get_label(),
        pin_protection=config.has_pin(),
        unlocked=config.is_unlocked(),
        busy=busy_expiry_ms() > 0,
        homescreen_width=WIDTH,
        homescreen_height=HEIGHT,
        unit_color=utils.unit_color(),
        unit_btconly=utils.unit_btconly(),
        unit_packaging=utils.unit_packaging(),
        bootloader_locked=utils.bootloader_locked(),
    )

    if (
        utils.INTERNAL_MODEL == "T2B1"  # pylint: disable=consider-using-in
        or utils.INTERNAL_MODEL == "T3B1"
    ):
        f.homescreen_format = HomescreenFormat.ToiG
    else:
        f.homescreen_format = HomescreenFormat.Jpeg

    if utils.BITCOIN_ONLY:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Crypto,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
            Capability.Translations,
        ]
    else:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Bitcoin_like,
            Capability.Binance,
            Capability.Cardano,
            Capability.Crypto,
            Capability.Ethereum,
            Capability.Monero,
            Capability.Ripple,
            Capability.Stellar,
            Capability.Tezos,
            Capability.U2F,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
            Capability.Solana,
            Capability.Translations,
        ]

        # We don't support some currencies on later models (see #2793)
        if utils.INTERNAL_MODEL == "T2T1":
            f.capabilities.extend(
                [
                    Capability.NEM,
                    Capability.EOS,
                ]
            )

    if utils.USE_HAPTIC:
        f.haptic_feedback = storage_device.get_haptic_feedback()
        f.capabilities.append(Capability.Haptic)

    if utils.USE_BACKLIGHT:
        f.capabilities.append(Capability.Brightness)

    if utils.USE_BLE:
        f.capabilities.append(Capability.BLE)

    if utils.INTERNAL_MODEL == "T3W1":  # TODO utils.USE_NFC
        f.capabilities.append(Capability.NFC)

    # Only some models are capable of SD card
    if utils.USE_SD_CARD:
        from trezor import sdcard

        f.sd_card_present = sdcard.is_present()
    else:
        f.sd_card_present = False

    if utils.USE_OPTIGA:
        from trezor.crypto import optiga

        f.optiga_sec = optiga.get_sec()

    f.initialized = storage_device.is_initialized()

    # private fields:
    if config.is_unlocked():
        # passphrase_protection is private, see #1807
        f.passphrase_protection = storage_device.is_passphrase_enabled()
        if storage_device.needs_backup():
            f.backup_availability = BackupAvailability.Required
        elif backup.repeated_backup_enabled():
            f.backup_availability = BackupAvailability.Available
        else:
            f.backup_availability = BackupAvailability.NotAvailable
        f.unfinished_backup = storage_device.unfinished_backup()
        f.no_backup = storage_device.no_backup()
        f.flags = storage_device.get_flags()
        if storage_recovery.is_in_progress():
            f.recovery_status = RecoveryStatus.Recovery
            f.recovery_type = storage_recovery.get_type()
        elif backup.repeated_backup_enabled():
            f.recovery_status = RecoveryStatus.Backup
        else:
            f.recovery_status = RecoveryStatus.Nothing
        f.backup_type = mnemonic.get_type()

        # Only some models are capable of SD card
        if utils.USE_SD_CARD:
            import storage.sd_salt as storage_sd_salt

            f.sd_protection = storage_sd_salt.is_enabled()
        else:
            f.sd_protection = False

        f.wipe_code_protection = config.has_wipe_code()
        f.passphrase_always_on_device = storage_device.get_passphrase_always_on_device()
        f.safety_checks = safety_checks.read_setting()
        f.auto_lock_delay_ms = storage_device.get_autolock_delay_ms()
        f.display_rotation = storage_device.get_rotation()
        f.experimental_features = storage_device.get_experimental_features()
        f.hide_passphrase_from_host = storage_device.get_hide_passphrase_from_host()

    return f


if utils.USE_THP:

    async def handle_ThpCreateNewSession(
        message: ThpCreateNewSession,
    ) -> Success | Failure:
        """
        Creates a new `ThpSession` based on the provided parameters and returns a
        `Success` message on success.

        Returns an appropriate `Failure` message if session creation fails.
        """
        from trezor import log, loop
        from trezor.enums import FailureType
        from trezor.messages import Failure
        from trezor.wire import NotInitialized
        from trezor.wire.context import get_context
        from trezor.wire.errors import ActionCancelled, DataError
        from trezor.wire.thp.session_context import GenericSessionContext
        from trezor.wire.thp.session_manager import get_new_session_context

        from apps.common.seed import derive_and_store_roots

        ctx = get_context()

        # Assert that context `ctx` is `GenericSessionContext`
        assert isinstance(ctx, GenericSessionContext)

        channel = ctx.channel
        session_id = ctx.session_id

        # Do not use `ctx` beyond this point, as it is techically
        # allowed to change in between await statements

        if not 0 <= session_id <= 255:
            return Failure(
                code=FailureType.DataError,
                message="Invalid session_id for session creation.",
            )

        new_session = get_new_session_context(
            channel_ctx=channel, session_id=session_id
        )
        try:
            await unlock_device()
            await derive_and_store_roots(new_session, message)
        except DataError as e:
            return Failure(code=FailureType.DataError, message=e.message)
        except ActionCancelled as e:
            return Failure(code=FailureType.ActionCancelled, message=e.message)
        except NotInitialized as e:
            return Failure(code=FailureType.NotInitialized, message=e.message)
        # TODO handle other errors (`Exception` when "Cardano icarus secret is already set!")

        if __debug__:
            log.debug(
                __name__,
                "New session with sid %d and passphrase %s created.",
                session_id,
                message.passphrase if message.passphrase is not None else "",
            )

        channel.sessions[new_session.session_id] = new_session
        loop.schedule(new_session.handle())

        return Success(message="New session created.")

    async def handle_ThpCredentialRequest(
        message: ThpCredentialRequest,
    ) -> ThpCredentialResponse | Failure:
        from trezor.messages import ThpCredentialMetadata, ThpCredentialResponse
        from trezor.wire.context import get_context
        from trezor.wire.thp import crypto
        from trezor.wire.thp.session_context import GenericSessionContext

        from apps.thp.credential_manager import (
            decode_credential,
            issue_credential,
            validate_credential,
        )

        ctx = get_context()

        # Assert that context `ctx` is `GenericSessionContext`
        assert isinstance(ctx, GenericSessionContext)

        # Check that request contains a host static public_key
        if message.host_static_public_key is None:
            return _get_autoconnect_failure(
                "Credential request must contain a host static public_key."
            )

        # Check that request contains valid credential
        if message.credential is None:
            return _get_autoconnect_failure(
                "Credential request must contain a previously issued pairing credential."
            )
        credential = decode_credential(message.credential)
        if not validate_credential(credential, message.host_static_public_key):
            return _get_autoconnect_failure(
                "Credential request contains an invalid pairing credential."
            )

        autoconnect = False
        if message.autoconnect is not None:
            autoconnect = message.autoconnect

        assert credential.cred_metadata is not None
        cred_metadata = ThpCredentialMetadata(
            host_name=credential.cred_metadata.host_name, autoconnect=autoconnect
        )
        if autoconnect:
            from trezor.wire.thp import ui

            await ui.show_autoconnect_credential_confirmation_screen(
                cred_metadata.host_name
            )
        new_cred = issue_credential(
            host_static_public_key=message.host_static_public_key,
            credential_metadata=cred_metadata,
        )
        trezor_static_public_key = crypto.get_trezor_static_public_key()

        return ThpCredentialResponse(
            trezor_static_public_key=trezor_static_public_key, credential=new_cred
        )

    def _get_autoconnect_failure(msg: str) -> Failure:
        from trezor.enums import FailureType
        from trezor.messages import Failure

        return Failure(
            code=FailureType.DataError,
            message=msg,
        )

else:

    async def handle_Initialize(msg: Initialize) -> Features:
        import storage.cache_codec as cache_codec

        session_id = cache_codec.start_session(msg.session_id)

        if not utils.BITCOIN_ONLY:
            from storage.cache_common import APP_COMMON_DERIVE_CARDANO

            derive_cardano = context.cache_get_bool(APP_COMMON_DERIVE_CARDANO)
            have_seed = context.cache_is_set(APP_COMMON_SEED)
            if (
                have_seed
                and msg.derive_cardano is not None
                and msg.derive_cardano != bool(derive_cardano)
            ):
                # seed is already derived, and host wants to change derive_cardano setting
                # => create a new session
                cache_codec.end_current_session()
                session_id = cache_codec.start_session()
                have_seed = False

            if not have_seed:
                context.cache_set_bool(
                    APP_COMMON_DERIVE_CARDANO, bool(msg.derive_cardano)
                )

        features = get_features()
        features.session_id = session_id
        return features


async def handle_GetFeatures(msg: GetFeatures) -> Features:
    return get_features()


async def handle_Cancel(msg: Cancel) -> NoReturn:
    workflow.close_others()
    raise wire.ActionCancelled


async def handle_LockDevice(msg: LockDevice) -> Success:
    lock_device()
    return Success()


async def handle_SetBusy(msg: SetBusy) -> Success:
    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if msg.expiry_ms:
        import utime

        deadline = utime.ticks_add(utime.ticks_ms(), msg.expiry_ms)
        context.cache_set_int(APP_COMMON_BUSY_DEADLINE_MS, deadline)
    else:
        context.cache_delete(APP_COMMON_BUSY_DEADLINE_MS)
    set_homescreen()
    workflow.close_others()
    return Success()


async def handle_EndSession(msg: EndSession) -> Success:
    ctx = context.get_context()
    ctx.release()
    return Success()


async def handle_Ping(msg: Ping) -> Success:
    if msg.button_protection:
        from trezor.enums import ButtonRequestType as B
        from trezor.ui.layouts import confirm_action

        await confirm_action("ping", TR.words__confirm, "ping", br_code=B.ProtectCall)
    return Success(message=msg.message)


async def handle_DoPreauthorized(msg: DoPreauthorized) -> protobuf.MessageType:
    from trezor.messages import PreauthorizedRequest
    from trezor.wire.context import call_any

    from apps.common import authorization

    if not authorization.is_set():
        raise wire.ProcessError("No preauthorized operation")

    wire_types = authorization.get_wire_types()
    utils.ensure(bool(wire_types), "Unsupported preauthorization found")

    req = await call_any(PreauthorizedRequest(), *wire_types)

    assert req.MESSAGE_WIRE_TYPE is not None
    handler = workflow_handlers.find_registered_handler(req.MESSAGE_WIRE_TYPE)
    if handler is None:
        return wire.message_handler.unexpected_message()

    return await handler(req, authorization.get())  # type: ignore [Expected 1 positional argument]


async def handle_UnlockPath(msg: UnlockPath) -> protobuf.MessageType:
    from trezor.crypto import hmac
    from trezor.messages import UnlockedPathRequest
    from trezor.wire.context import call_any

    from apps.common.paths import SLIP25_PURPOSE
    from apps.common.seed import Slip21Node, get_seed
    from apps.common.writers import write_uint32_le

    _KEYCHAIN_MAC_KEY_PATH = [b"TREZOR", b"Keychain MAC key"]

    # UnlockPath is relevant only for SLIP-25 paths.
    # Note: Currently we only allow unlocking the entire SLIP-25 purpose subtree instead of
    # per-coin or per-account unlocking in order to avoid UI complexity.
    if msg.address_n != [SLIP25_PURPOSE]:
        raise wire.DataError("Invalid path")

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_KEYCHAIN_MAC_KEY_PATH)
    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))
    for i in msg.address_n:
        write_uint32_le(mac, i)
    expected_mac = mac.get_digest()

    # Require confirmation to access SLIP25 paths unless already authorized.
    if msg.mac:
        if len(msg.mac) != len(expected_mac) or not utils.consteq(
            expected_mac, msg.mac
        ):
            raise wire.DataError("Invalid MAC")
    else:
        await confirm_action(
            "confirm_coinjoin_access",
            title="Coinjoin",
            description=TR.coinjoin__access_account,
            verb=TR.buttons__access,
            prompt_screen=True,
        )

    wire_types = (MessageType.GetAddress, MessageType.GetPublicKey, MessageType.SignTx)
    req = await call_any(UnlockedPathRequest(mac=expected_mac), *wire_types)

    assert req.MESSAGE_WIRE_TYPE in wire_types
    handler = workflow_handlers.find_registered_handler(req.MESSAGE_WIRE_TYPE)
    assert handler is not None
    return await handler(req, msg)  # type: ignore [Expected 1 positional argument]


async def handle_CancelAuthorization(msg: CancelAuthorization) -> protobuf.MessageType:
    from apps.common import authorization

    authorization.clear()
    workflow.close_others()
    return Success(message="Authorization cancelled")


def set_homescreen() -> None:
    import storage.recovery as storage_recovery

    from apps.common import backup

    set_default = workflow.set_default  # local_cache_attribute

    if context.cache_is_set(APP_COMMON_BUSY_DEADLINE_MS):
        from apps.homescreen import busyscreen

        set_default(busyscreen)

    elif not config.is_unlocked():
        from apps.homescreen import lockscreen

        set_default(lockscreen)

    elif _SCREENSAVER_IS_ON:
        from apps.homescreen import screensaver

        set_default(screensaver, restart=True)

    elif storage_recovery.is_in_progress() or backup.repeated_backup_enabled():
        from apps.management.recovery_device.homescreen import recovery_homescreen

        set_default(recovery_homescreen)

    else:
        from apps.homescreen import homescreen

        set_default(homescreen)


def lock_device(interrupt_workflow: bool = True) -> None:
    if config.has_pin():
        config.lock()
        filters.append(_pinlock_filter)
        set_homescreen()
        if interrupt_workflow:
            workflow.close_others()


def lock_device_if_unlocked() -> None:
    from apps.common.request_pin import can_lock_device

    if not utils.USE_BACKLIGHT and not can_lock_device():
        # on OLED devices without PIN, trigger screensaver
        global _SCREENSAVER_IS_ON

        _SCREENSAVER_IS_ON = True
        set_homescreen()

    elif config.is_unlocked():
        lock_device(interrupt_workflow=workflow.autolock_interrupts_workflow)


async def unlock_device() -> None:
    """Ensure the device is in unlocked state.

    If the storage is locked, attempt to unlock it. Reset the homescreen and the wire
    handler.
    """
    from apps.common.request_pin import verify_user_pin

    global _SCREENSAVER_IS_ON

    if not config.is_unlocked():
        # verify_user_pin will raise if the PIN was invalid
        await verify_user_pin()

    _SCREENSAVER_IS_ON = False
    set_homescreen()
    remove_filter(_pinlock_filter)


def _pinlock_filter(msg_type: int, prev_handler: Handler[Msg]) -> Handler[Msg]:
    if msg_type in workflow.ALLOW_WHILE_LOCKED:
        return prev_handler

    async def wrapper(msg: Msg) -> protobuf.MessageType:
        await unlock_device()
        return await prev_handler(msg)

    return wrapper


# this function is also called when handling ApplySettings
def reload_settings_from_storage() -> None:
    from trezor import ui

    workflow.idle_timer.set(
        storage_device.get_autolock_delay_ms(), lock_device_if_unlocked
    )
    wire.message_handler.EXPERIMENTAL_ENABLED = (
        storage_device.get_experimental_features()
    )
    if ui.display.orientation() != storage_device.get_rotation():
        ui.backlight_fade(ui.BacklightLevels.DIM)
        ui.display.orientation(storage_device.get_rotation())


def boot() -> None:
    from apps.common import backup

    MT = MessageType  # local_cache_global

    # Register workflow handlers
    if utils.USE_THP:
        workflow_handlers.register(MT.ThpCreateNewSession, handle_ThpCreateNewSession)
        workflow_handlers.register(MT.ThpCredentialRequest, handle_ThpCredentialRequest)
    else:
        workflow_handlers.register(MT.Initialize, handle_Initialize)
    for msg_type, handler in [
        (MT.GetFeatures, handle_GetFeatures),
        (MT.Cancel, handle_Cancel),
        (MT.LockDevice, handle_LockDevice),
        (MT.EndSession, handle_EndSession),
        (MT.Ping, handle_Ping),
        (MT.DoPreauthorized, handle_DoPreauthorized),
        (MT.UnlockPath, handle_UnlockPath),
        (MT.CancelAuthorization, handle_CancelAuthorization),
        (MT.SetBusy, handle_SetBusy),
    ]:
        workflow_handlers.register(msg_type, handler)

    reload_settings_from_storage()
    if utils.USE_POWER_MANAGER:
        from apps.management.pm.autodim import autodim_display

        workflow.idle_timer.set(30_000, autodim_display)

    if backup.repeated_backup_enabled():
        backup.activate_repeated_backup()
    if not config.is_unlocked():
        # pinlocked handler should always be the last one
        filters.append(_pinlock_filter)
