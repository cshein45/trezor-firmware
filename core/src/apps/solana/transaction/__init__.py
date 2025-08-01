from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader
from trezor.wire import DataError

from ..constants import (
    MICROLAMPORTS_PER_LAMPORT,
    SOLANA_BASE_FEE_LAMPORTS,
    SOLANA_COMPUTE_UNIT_LIMIT,
)
from ..types import AddressType
from .instruction import Instruction
from .instructions import (
    COMPUTE_BUDGET_PROGRAM_ID,
    COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
    COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
    get_instruction,
    get_instruction_id_length,
)
from .parse import parse_block_hash, parse_pubkey, parse_var_int

if TYPE_CHECKING:
    from ..types import Account, Address, AddressReference, RawInstruction


class Fee:
    def __init__(
        self,
        base: int,
        priority: int,
        rent: int,
    ) -> None:
        self.base = base
        self.priority = priority
        self.rent = rent
        self.total = base + priority + rent


class Transaction:
    blind_signing = False
    required_signers_count = 0

    version: int | None = None

    addresses: list[Address]

    blockhash: bytes

    raw_instructions: list[RawInstruction]
    instructions: list[Instruction]

    address_lookup_tables_rw_addresses: list[AddressReference]
    address_lookup_tables_ro_addresses: list[AddressReference]

    def __init__(self, serialized_tx: bytes) -> None:
        self._parse_transaction(serialized_tx)
        self._create_instructions()
        self._determine_if_blind_signing()

    def _parse_transaction(self, serialized_tx: bytes) -> None:
        serialized_tx_reader = BufferReader(serialized_tx)
        self._parse_header(serialized_tx_reader)

        self._parse_addresses(serialized_tx_reader)

        self.blockhash = parse_block_hash(serialized_tx_reader)

        self._parse_instructions(serialized_tx_reader)

        self._parse_address_lookup_tables(serialized_tx_reader)

        if serialized_tx_reader.remaining_count() != 0:
            raise DataError("Invalid transaction")

    def _parse_header(self, serialized_tx_reader: BufferReader) -> None:
        self.version: int | None = None

        if serialized_tx_reader.peek() & 0b10000000:
            self.version = serialized_tx_reader.get() & 0b01111111
            # only version 0 is supported
            if self.version > 0:
                raise DataError("Unsupported transaction version")

        self.required_signers_count: int = serialized_tx_reader.get()
        self.num_signature_read_only_addresses: int = serialized_tx_reader.get()
        self.num_read_only_addresses: int = serialized_tx_reader.get()

    def _parse_addresses(self, serialized_tx_reader: BufferReader) -> None:
        num_of_addresses = parse_var_int(serialized_tx_reader)

        assert (
            num_of_addresses
            >= self.required_signers_count
            + self.num_signature_read_only_addresses
            + self.num_read_only_addresses
        )

        addresses: list[Address] = []
        for i in range(num_of_addresses):
            if i < self.required_signers_count:
                type = AddressType.AddressSig
            elif (
                i < self.required_signers_count + self.num_signature_read_only_addresses
            ):
                type = AddressType.AddressSigReadOnly
            elif (
                i
                < self.required_signers_count
                + self.num_signature_read_only_addresses
                + self.num_read_only_addresses
            ):
                type = AddressType.AddressRw
            else:
                type = AddressType.AddressReadOnly

            address = parse_pubkey(serialized_tx_reader)

            addresses.append((address, type))

        self.addresses = addresses

    def _parse_instructions(self, serialized_tx_reader: BufferReader) -> None:
        num_of_instructions = parse_var_int(serialized_tx_reader)

        self.raw_instructions = []

        for _ in range(num_of_instructions):
            program_index = serialized_tx_reader.get()
            program_id = base58.encode(self.addresses[program_index][0])
            num_of_accounts = parse_var_int(serialized_tx_reader)
            accounts: list[int] = []
            for _ in range(num_of_accounts):
                account_index = serialized_tx_reader.get()
                accounts.append(account_index)

            data_length = parse_var_int(serialized_tx_reader)

            instruction_id_length = get_instruction_id_length(program_id)
            if 0 < instruction_id_length <= data_length:
                instruction_id = int.from_bytes(
                    serialized_tx_reader.read_memoryview(instruction_id_length),
                    "little",
                )
            else:
                instruction_id = None

            instruction_data = serialized_tx_reader.read_memoryview(
                max(0, data_length - instruction_id_length)
            )

            self.raw_instructions.append(
                (program_index, instruction_id, accounts, instruction_data)
            )

    def _parse_address_lookup_tables(self, serialized_tx: BufferReader) -> None:
        self.address_lookup_tables_rw_addresses = []
        self.address_lookup_tables_ro_addresses = []

        if self.version is None:
            return

        address_lookup_tables_count = parse_var_int(serialized_tx)
        for _ in range(address_lookup_tables_count):
            account = parse_pubkey(serialized_tx)

            table_rw_indexes_count = parse_var_int(serialized_tx)
            for _ in range(table_rw_indexes_count):
                index = serialized_tx.get()
                self.address_lookup_tables_rw_addresses.append(
                    (account, index, AddressType.AddressRw)
                )

            table_ro_indexes_count = parse_var_int(serialized_tx)
            for _ in range(table_ro_indexes_count):
                index = serialized_tx.get()
                self.address_lookup_tables_ro_addresses.append(
                    (account, index, AddressType.AddressReadOnly)
                )

    def _create_instructions(self) -> None:
        # Instructions reference accounts by index in this combined list.
        combined_accounts = (
            self.addresses
            + self.address_lookup_tables_rw_addresses
            + self.address_lookup_tables_ro_addresses
        )

        self.instructions = []
        for (
            program_index,
            instruction_id,
            accounts,
            instruction_data,
        ) in self.raw_instructions:
            program_id = base58.encode(self.addresses[program_index][0])
            instruction_accounts = [
                combined_accounts[account_index] for account_index in accounts
            ]
            instruction = get_instruction(
                program_id,
                instruction_id,
                instruction_accounts,
                instruction_data,
            )

            self.instructions.append(instruction)

    def _determine_if_blind_signing(self) -> None:
        for instruction in self.instructions:
            if (
                not instruction.is_program_supported
                or not instruction.is_instruction_supported
            ):
                self.blind_signing = True
                break

    def get_visible_instructions(self) -> list[Instruction]:
        return [
            instruction
            for instruction in self.instructions
            if not instruction.is_ui_hidden
        ]

    def calculate_fee(self) -> Fee | None:
        number_of_signers = 0
        for address in self.addresses:
            if address[1] == AddressType.AddressSig:
                number_of_signers += 1

        base_fee = SOLANA_BASE_FEE_LAMPORTS * number_of_signers

        unit_price = 0
        is_unit_price_set = False
        unit_limit = SOLANA_COMPUTE_UNIT_LIMIT
        is_unit_limit_set = False

        for instruction in self.instructions:
            if instruction.program_id == COMPUTE_BUDGET_PROGRAM_ID:
                if (
                    instruction.instruction_id
                    == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT
                    and not is_unit_limit_set
                ):
                    unit_limit = instruction.units
                    is_unit_limit_set = True
                elif (
                    instruction.instruction_id
                    == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE
                    and not is_unit_price_set
                ):
                    unit_price = instruction.lamports
                    is_unit_price_set = True

        priority_fee = unit_price * unit_limit  # in microlamports
        rent = self.calculate_rent()
        if rent is None:
            return None
        return Fee(
            base=base_fee,
            priority=(priority_fee + MICROLAMPORTS_PER_LAMPORT - 1)
            // MICROLAMPORTS_PER_LAMPORT,
            rent=rent,
        )

    def get_account_address(self, account: Account) -> bytes | None:
        if len(account) == 2:
            return account[0]
        else:
            # AddressReference points to an Address Lookup Table account, whose contents are unavailable here:
            # https://github.com/trezor/trezor-firmware/issues/5369#issuecomment-3083683085
            # https://docs.anza.xyz/proposals/versioned-transactions#limitations
            return None

    def calculate_rent(self) -> int | None:
        """
        Returns max rent exemption in lamports.

        To estimate rent exemption from a transaction we need to go over the instructions.
        When new accounts are created, space must be allocated for them, rent exemption value depends on that space.

        There are a handful of instruction that allocate space:
        - System program create account instruction (the space data parameter)
        - System program create account with seed instruction (the space data parameter)
        - System program allocate instruction (the space data parameter)
        - System program allocate with seed instruction (the space data parameter)
        - Associated token account program create instruction (165 bytes for Token, 170-195 for Token22)
        - Associated token account program create idempotent instruction (165 bytes for Token, 170-195 for Token22, might not allocate)

        Associated token account program allocates space based on used extensions which must be enabled in the same transaction.
        Currently, the token22 extensions aren't supported, so the max value of 195 bytes is assumed.
        The min Token22 account size is the base Token account size plus some overhead.
        The max Token22 account size is derived from the program source code:
        https://github.com/solana-program/token-2022/blob/d9cfcf32cf5fbb3ee32f9f873d3fe3c94356e981/program/src/extension/mod.rs#L1299
        Note that Token/Token22 programs don't allocate space by themselves, they only use preallocated accounts.
        """
        from ..constants import (
            SOLANA_ACCOUNT_OVERHEAD_SIZE,
            SOLANA_RENT_EXEMPTION_YEARS,
            SOLANA_RENT_LAMPORTS_PER_BYTE_YEAR,
            SOLANA_TOKEN22_MAX_ACCOUNT_SIZE,
            SOLANA_TOKEN_ACCOUNT_SIZE,
        )
        from ..transaction.instructions import (
            _TOKEN_2022_PROGRAM_ID,
            _TOKEN_PROGRAM_ID,
            is_atap_account_creation,
            is_system_program_account_creation,
        )

        allocation = 0
        for instruction in self.instructions:
            if is_system_program_account_creation(instruction):
                allocation += (
                    instruction.parsed_data["space"] + SOLANA_ACCOUNT_OVERHEAD_SIZE
                )
            elif is_atap_account_creation(instruction):
                spl_token_account = self.get_account_address(
                    instruction.parsed_accounts["spl_token"]
                )
                if spl_token_account == base58.decode(_TOKEN_PROGRAM_ID):
                    allocation += (
                        SOLANA_TOKEN_ACCOUNT_SIZE + SOLANA_ACCOUNT_OVERHEAD_SIZE
                    )
                elif spl_token_account == base58.decode(_TOKEN_2022_PROGRAM_ID):
                    allocation += (
                        SOLANA_TOKEN22_MAX_ACCOUNT_SIZE + SOLANA_ACCOUNT_OVERHEAD_SIZE
                    )
                else:
                    return None

        rent_exemption = (
            allocation
            * SOLANA_RENT_LAMPORTS_PER_BYTE_YEAR
            * SOLANA_RENT_EXEMPTION_YEARS
        )

        return rent_exemption
