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

import pytest

from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tezos import get_public_key
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.tezos
@pytest.mark.models("core")
def test_tezos_get_public_key(session: Session):
    path = parse_path("m/44h/1729h/0h")
    pk = get_public_key(session, path)
    assert pk == "edpkttLhEbVfMC3DhyVVFzdwh8ncRnEWiLD1x8TAuPU7vSJak7RtBX"

    path = parse_path("m/44h/1729h/1h")
    pk = get_public_key(session, path)
    assert pk == "edpkuTPqWjcApwyD3VdJhviKM5C13zGk8c4m87crgFarQboF3Mp56f"
