# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import io
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

import click
import requests

from .. import device, messages, toif
from . import AliasedGroup, ChoiceType, with_session

if TYPE_CHECKING:
    from ..transport.session import Session

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ROTATION = {
    "north": messages.DisplayRotation.North,
    "east": messages.DisplayRotation.East,
    "south": messages.DisplayRotation.South,
    "west": messages.DisplayRotation.West,
}

SAFETY_LEVELS = {
    "strict": messages.SafetyCheckLevel.Strict,
    "prompt": messages.SafetyCheckLevel.PromptTemporarily,
}

T1_TR_IMAGE_SIZE = (128, 64)


def image_to_t1(filename: Path) -> bytes:
    if not PIL_AVAILABLE:
        raise click.ClickException(
            "Image library is missing. Please install via 'pip install Pillow'."
        )

    if filename.suffix == ".toif":
        raise click.ClickException("TOIF images not supported on Trezor One")

    try:
        image = Image.open(filename)
    except Exception as e:
        raise click.ClickException("Failed to load image") from e

    if image.size != T1_TR_IMAGE_SIZE:
        if click.confirm(
            f"Image is not 128x64, but {image.size}. Do you want to resize it automatically?",
            default=True,
        ):
            image = image.resize(T1_TR_IMAGE_SIZE, Image.Resampling.LANCZOS)
        else:
            raise click.ClickException("Wrong size of the image - should be 128x64")

    image = image.convert("1")
    return image.tobytes("raw", "1")


def image_to_toif(filename: Path, width: int, height: int, greyscale: bool) -> bytes:
    if filename.suffix == ".toif":
        try:
            toif_image = toif.from_bytes(filename.read_bytes())
            image = toif_image.to_image()
        except Exception as e:
            raise click.ClickException("TOIF file is corrupted") from e

    elif not PIL_AVAILABLE:
        raise click.ClickException(
            "Image library is missing. Please install via 'pip install Pillow'."
        )

    else:
        try:
            image = Image.open(filename)
            toif_image = toif.from_image(image)
        except Exception as e:
            raise click.ClickException(
                "Failed to convert image to Trezor format"
            ) from e

    if toif_image.size != (width, height):
        if click.confirm(
            f"Image is not {width}x{height}, but {image.size[0]}x{image.size[1]}. Do you want to resize it automatically?",
            default=True,
        ):
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        else:
            raise click.ClickException(
                f"Wrong size of image - should be {width}x{height}"
            )

    if greyscale:
        image = image.convert("1")
    toif_image = toif.from_image(image)

    if not greyscale and toif_image.mode != toif.ToifMode.full_color:
        raise click.ClickException("Wrong image mode - should be full_color")
    if greyscale and toif_image.mode != toif.ToifMode.grayscale_eh:
        raise click.ClickException("Wrong image mode - should be grayscale_eh")

    return toif_image.to_bytes()


def image_to_jpeg(filename: Path, width: int, height: int, quality: int = 90) -> bytes:
    needs_regeneration = False
    if filename.suffix in (".jpg", ".jpeg") and not PIL_AVAILABLE:
        click.echo("Warning: Image library is missing, skipping image validation.")
        return filename.read_bytes()

    if not PIL_AVAILABLE:
        raise click.ClickException(
            "Image library is missing. Please install via 'pip install Pillow'."
        )

    try:
        image = Image.open(filename)
    except Exception as e:
        raise click.ClickException("Failed to open image") from e

    if image.size != (width, height):
        if click.confirm(
            f"Image is not {width}x{height}, but {image.size[0]}x{image.size[1]}. Do you want to resize it automatically?",
            default=True,
        ):
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            needs_regeneration = True
        else:
            raise click.ClickException(
                f"Wrong size of image - should be {width}x{height}"
            )

    if image.mode != "RGB":
        image = image.convert("RGB")
        needs_regeneration = True

    if filename.suffix in (".jpg", ".jpeg"):
        if image.info.get("progressive"):  # pyright: ignore[reportAttributeAccessIssue]
            needs_regeneration = True

    if needs_regeneration:
        buf = io.BytesIO()
        image.save(buf, format="jpeg", progressive=False, quality=quality)
        return buf.getvalue()
    else:
        return filename.read_bytes()


def _should_remove(enable: Optional[bool], remove: bool) -> bool:
    """Helper to decide whether to remove something or not.

    Needed for backwards compatibility purposes, so we can support
    both positive (enable) and negative (remove) args.
    """
    if remove and enable:
        raise click.ClickException("Argument and option contradict each other")

    if remove or enable is False:
        return True

    return False


@click.group(name="set")
def cli() -> None:
    """Device settings."""


@cli.command()
@click.option("-r", "--remove", is_flag=True, hidden=True)
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@with_session(seedless=True)
def pin(session: "Session", enable: Optional[bool], remove: bool) -> None:
    """Set, change or remove PIN."""
    # Remove argument is there for backwards compatibility
    device.change_pin(session, remove=_should_remove(enable, remove))


@cli.command()
@click.option("-r", "--remove", is_flag=True, hidden=True)
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@with_session(seedless=True)
def wipe_code(session: "Session", enable: Optional[bool], remove: bool) -> None:
    """Set or remove the wipe code.

    The wipe code functions as a "self-destruct PIN". If the wipe code is ever
    entered into any PIN entry dialog, then all private data will be immediately
    removed and the device will be reset to factory defaults.
    """
    # Remove argument is there for backwards compatibility
    device.change_wipe_code(session, remove=_should_remove(enable, remove))


@cli.command()
# keep the deprecated -l/--label option, make it do nothing
@click.option("-l", "--label", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.argument("label")
@with_session(seedless=True)
def label(session: "Session", label: str) -> None:
    """Set new device label."""
    device.apply_settings(session, label=label)


@cli.command()
@with_session(seedless=True)
def brightness(session: "Session") -> None:
    """Set display brightness."""
    device.set_brightness(session)


@cli.command()
@click.argument("enable", type=ChoiceType({"on": True, "off": False}))
@with_session(seedless=True)
def haptic_feedback(session: "Session", enable: bool) -> None:
    """Enable or disable haptic feedback."""
    device.apply_settings(session, haptic_feedback=enable)


@cli.command()
@click.argument("path_or_url", required=False)
@click.option(
    "-r", "--remove", is_flag=True, default=False, help="Switch back to english."
)
@click.option("-d/-D", "--display/--no-display", default=None)
@with_session(seedless=True)
def language(
    session: "Session", path_or_url: str | None, remove: bool, display: bool | None
) -> None:
    """Set new language with translations."""
    if remove != (path_or_url is None):
        raise click.ClickException("Either provide a path or URL or use --remove")

    if remove:
        language_data = b""
    else:
        assert path_or_url is not None
        if path_or_url.endswith(".json"):
            raise click.ClickException(
                "Provided file is a JSON file, not a blob file.\n"
                "Generate blobs by running `python core/translations/cli.py gen` in root."
            )
        try:
            language_data = Path(path_or_url).read_bytes()
        except Exception:
            try:
                language_data = requests.get(path_or_url).content
            except Exception:
                raise click.ClickException(
                    f"Failed to load translations from {path_or_url}"
                ) from None
    device.change_language(session, language_data=language_data, show_display=display)


@cli.command()
@click.argument("rotation", type=ChoiceType(ROTATION))
@with_session(seedless=True)
def display_rotation(session: "Session", rotation: messages.DisplayRotation) -> None:
    """Set display rotation.

    Configure display rotation for Trezor Model T. The options are
    north, east, south or west.
    """
    device.apply_settings(session, display_rotation=rotation)


@cli.command()
@click.argument("delay", type=str)
@with_session(seedless=True)
def auto_lock_delay(session: "Session", delay: str) -> None:
    """Set auto-lock delay (in seconds)."""

    if not session.features.pin_protection:
        raise click.ClickException("Set up a PIN first")

    value, unit = delay[:-1], delay[-1:]
    units = {"s": 1, "m": 60, "h": 3600}
    if unit in units:
        seconds = float(value) * units[unit]
    else:
        seconds = float(delay)  # assume seconds if no unit is specified
    device.apply_settings(session, auto_lock_delay_ms=int(seconds * 1000))


@cli.command()
@click.argument("flags")
@with_session(seedless=True)
def flags(session: "Session", flags: str) -> None:
    """Set device flags."""
    if flags.lower().startswith("0b"):
        flags_int = int(flags, 2)
    elif flags.lower().startswith("0x"):
        flags_int = int(flags, 16)
    else:
        flags_int = int(flags)
    device.apply_flags(session, flags=flags_int)


@cli.command()
@click.argument("filename")
@click.option(
    "-f", "--filename", "_ignore", is_flag=True, hidden=True, expose_value=False
)
@click.option("-q", "--quality", type=int, default=90, help="JPEG quality (0-100)")
@with_session(seedless=True)
def homescreen(session: "Session", filename: str, quality: int) -> None:
    """Set new homescreen.

    To revert to default homescreen, use 'trezorctl set homescreen default'
    """
    if filename == "default":
        img = b""
    else:
        path = Path(filename)
        if not path.exists() or not path.is_file():
            raise click.ClickException("Cannot open file")

        if session.features.model == "1":
            img = image_to_t1(path)
        else:
            if session.features.homescreen_format == messages.HomescreenFormat.Jpeg:
                width = (
                    session.features.homescreen_width
                    if session.features.homescreen_width is not None
                    else 240
                )
                height = (
                    session.features.homescreen_height
                    if session.features.homescreen_height is not None
                    else 240
                )
                img = image_to_jpeg(path, width, height, quality)
            elif session.features.homescreen_format == messages.HomescreenFormat.ToiG:
                width = session.features.homescreen_width
                height = session.features.homescreen_height
                if width is None or height is None:
                    raise click.ClickException("Device did not report homescreen size.")
                img = image_to_toif(path, width, height, True)
            elif (
                session.features.homescreen_format == messages.HomescreenFormat.Toif
                or session.features.homescreen_format is None
            ):
                width = (
                    session.features.homescreen_width
                    if session.features.homescreen_width is not None
                    else 144
                )
                height = (
                    session.features.homescreen_height
                    if session.features.homescreen_height is not None
                    else 144
                )
                img = image_to_toif(path, width, height, False)

            else:
                raise click.ClickException(
                    "Unknown image format requested by the device."
                )

    device.apply_settings(session, homescreen=img)


@cli.command()
@click.option(
    "--always", is_flag=True, help='Persist the "prompt" setting across Trezor reboots.'
)
@click.argument("level", type=ChoiceType(SAFETY_LEVELS))
@with_session(seedless=True)
def safety_checks(
    session: "Session", always: bool, level: messages.SafetyCheckLevel
) -> None:
    """Set safety check level.

    Set to "strict" to get the full Trezor security (default setting).

    Set to "prompt" if you want to be able to allow potentially unsafe actions, such as
    mismatching coin keys or extreme fees.

    This is a power-user feature. Use with caution.
    """
    if always and level == messages.SafetyCheckLevel.PromptTemporarily:
        level = messages.SafetyCheckLevel.PromptAlways
    device.apply_settings(session, safety_checks=level)


@cli.command()
@click.argument("enable", type=ChoiceType({"on": True, "off": False}))
@with_session(seedless=True)
def experimental_features(session: "Session", enable: bool) -> None:
    """Enable or disable experimental message types.

    This is a developer feature. Use with caution.
    """
    device.apply_settings(session, experimental_features=enable)


#
# passphrase operations
#


# Using special class AliasedGroup, so we can support multiple commands
# to invoke the same function to keep backwards compatibility
@cli.command(cls=AliasedGroup, name="passphrase")
def passphrase_main() -> None:
    """Enable, disable or configure passphrase protection."""
    # this exists in order to support command aliases for "enable-passphrase"
    # and "disable-passphrase". Otherwise `passphrase` would just take an argument.


# Cast for type-checking purposes
passphrase = cast(AliasedGroup, passphrase_main)


@passphrase.command(name="on")
@click.option("-f/-F", "--force-on-device/--no-force-on-device", default=None)
@with_session(seedless=True)
def passphrase_on(session: "Session", force_on_device: Optional[bool]) -> None:
    """Enable passphrase."""
    if session.features.passphrase_protection is not True:
        use_passphrase = True
    else:
        use_passphrase = None
    device.apply_settings(
        session,
        use_passphrase=use_passphrase,
        passphrase_always_on_device=force_on_device,
    )


@passphrase.command(name="off")
@with_session(seedless=True)
def passphrase_off(session: "Session") -> None:
    """Disable passphrase."""
    device.apply_settings(session, use_passphrase=False)


# Registering the aliases for backwards compatibility
# (these are not shown in --help docs)
passphrase.aliases = {
    "enabled": passphrase_on,
    "disabled": passphrase_off,
}


@passphrase.command(name="hide")
@click.argument("hide", type=ChoiceType({"on": True, "off": False}))
@with_session(seedless=True)
def hide_passphrase_from_host(session: "Session", hide: bool) -> None:
    """Enable or disable hiding passphrase coming from host.

    This is a developer feature. Use with caution.
    """
    device.apply_settings(session, hide_passphrase_from_host=hide)
