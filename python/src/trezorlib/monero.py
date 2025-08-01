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

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session


# MAINNET = 0
# TESTNET = 1
# STAGENET = 2
# FAKECHAIN = 3


def get_address(
    session: "Session",
    n: "Address",
    show_display: bool = False,
    network_type: messages.MoneroNetworkType = messages.MoneroNetworkType.MAINNET,
    chunkify: bool = False,
) -> bytes:
    return session.call(
        messages.MoneroGetAddress(
            address_n=n,
            show_display=show_display,
            network_type=network_type,
            chunkify=chunkify,
        ),
        expect=messages.MoneroAddress,
    ).address


def get_watch_key(
    session: "Session",
    n: "Address",
    network_type: messages.MoneroNetworkType = messages.MoneroNetworkType.MAINNET,
) -> messages.MoneroWatchKey:
    return session.call(
        messages.MoneroGetWatchKey(address_n=n, network_type=network_type),
        expect=messages.MoneroWatchKey,
    )
