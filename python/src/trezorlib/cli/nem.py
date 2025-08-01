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
from typing import TYPE_CHECKING, Optional, TextIO

import click
import requests

from .. import nem, tools
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session

PATH_HELP = "BIP-32 path, e.g. m/44h/134h/0h/0h"


@click.group(name="nem")
def cli() -> None:
    """NEM commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-N", "--network", type=int, default=0x68)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session",
    address: str,
    network: int,
    show_display: bool,
    chunkify: bool,
) -> str:
    """Get NEM address for specified path."""
    address_n = tools.parse_path(address)
    return nem.get_address(session, address_n, network, show_display, chunkify)


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option("-b", "--broadcast", help="NIS to announce transaction to")
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def sign_tx(
    session: "Session",
    address: str,
    file: TextIO,
    broadcast: Optional[str],
    chunkify: bool,
) -> dict:
    """Sign (and optionally broadcast) NEM transaction.

    Transaction file is expected in the NIS (RequestPrepareAnnounce) format.
    """
    address_n = tools.parse_path(address)
    transaction = nem.sign_tx(session, address_n, json.load(file), chunkify=chunkify)

    payload = {"data": transaction.data.hex(), "signature": transaction.signature.hex()}

    if broadcast:
        return requests.post(f"{broadcast}/transaction/announce", json=payload).json()
    else:
        return payload
