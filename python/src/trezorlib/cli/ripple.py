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

import json
from typing import TYPE_CHECKING, TextIO

import click

from .. import ripple, tools
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session

PATH_HELP = "BIP-32 path to key, e.g. m/44h/144h/0h/0/0"


@click.group(name="ripple")
def cli() -> None:
    """Ripple commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Ripple address"""
    address_n = tools.parse_path(address)
    return ripple.get_address(session, address_n, show_display, chunkify)


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def sign_tx(session: "Session", address: str, file: TextIO, chunkify: bool) -> None:
    """Sign Ripple transaction"""
    address_n = tools.parse_path(address)
    msg = ripple.create_sign_tx_msg(json.load(file))

    result = ripple.sign_tx(session, address_n, msg, chunkify=chunkify)
    click.echo("Signature:")
    click.echo(result.signature.hex())
    click.echo()
    click.echo("Serialized tx including the signature:")
    click.echo(result.serialized_tx.hex())
