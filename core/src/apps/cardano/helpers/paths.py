from micropython import const

from apps.common.paths import HARDENED, PathSchema, unharden  # noqa: F401

SLIP44_ID = const(1815)

BYRON_ROOT = [44 | HARDENED, SLIP44_ID | HARDENED]
SHELLEY_ROOT = [1852 | HARDENED, SLIP44_ID | HARDENED]
MULTISIG_ROOT = [1854 | HARDENED, SLIP44_ID | HARDENED]
MINTING_ROOT = [1855 | HARDENED, SLIP44_ID | HARDENED]

# fmt: off
SCHEMA_PUBKEY = PathSchema.parse("m/[44,1852,1854]'/coin_type'/account'/*", SLIP44_ID)
# minting has a specific schema for key derivation - see CIP-1855
SCHEMA_MINT = PathSchema.parse(f"m/1855'/coin_type'/[0-{HARDENED - 1}]'", SLIP44_ID)
SCHEMA_PAYMENT = PathSchema.parse("m/[44,1852]'/coin_type'/account'/[0,1]/address_index", SLIP44_ID)
# staking is only allowed on Shelley paths with suffix /2/0
SCHEMA_STAKING = PathSchema.parse("m/1852'/coin_type'/account'/2/address_index", SLIP44_ID)
SCHEMA_STAKING_ANY_ACCOUNT = PathSchema.parse(f"m/1852'/coin_type'/[0-{HARDENED - 1}]'/2/address_index", SLIP44_ID)
# fmt: on

ACCOUNT_PATH_INDEX = const(2)
ACCOUNT_PATH_LENGTH = const(3)
CHAIN_STAKING_KEY = const(2)

ADDRESS_INDEX_PATH_INDEX = const(4)
RECOMMENDED_ADDRESS_INDEX = const(0)  # https://cips.cardano.org/cips/cip11/
