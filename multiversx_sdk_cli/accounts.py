import logging
from pathlib import Path
from typing import Any, Optional, Protocol
from json import load

import nacl.signing

from multiversx_sdk_cli import constants, errors
from multiversx_sdk_cli.interfaces import IAccount, IAddress, ITransaction
from multiversx_sdk_network_providers.accounts import AccountOnNetwork
from multiversx_sdk_cli.ledger.config import compare_versions
from multiversx_sdk_cli.ledger.ledger_app_handler import SIGN_USING_HASH_VERSION
from multiversx_sdk_cli.ledger.ledger_functions import do_get_ledger_address, do_sign_transaction_with_ledger, do_get_ledger_version, \
    TX_HASH_SIGN_VERSION, TX_HASH_SIGN_OPTIONS
from multiversx_sdk_cli.wallet import bech32
from multiversx_sdk_wallet import UserPEM
from multiversx_sdk_wallet.keyfile import load_from_key_file_object

logger = logging.getLogger("accounts")


class INetworkProvider(Protocol):
    def get_account(self, address: IAddress) -> AccountOnNetwork:
        ...


class Account(IAccount):
    def __init__(self,
                 address: Any = None,
                 pem_file: Optional[str] = None,
                 pem_index: int = 0,
                 key_file: str = "",
                 password: str = "",
                 ledger: bool = False):
        self.address = Address(address)
        self.pem_file = pem_file
        self.pem_index = int(pem_index)
        self.nonce: int = 0
        self.ledger = ledger

        if self.pem_file:
            user_pem_file = UserPEM.from_file(Path(self.pem_file), self.pem_index)
            self.secret_key = user_pem_file.secret_key.hex()
            self.address = Address(user_pem_file.public_key.hex())
        elif key_file and password:
            with open(key_file, 'r') as f:
                key_file_data = load(f)

            address_from_key_file, secret_key = load_from_key_file_object(key_file_data, password)
            self.secret_key = secret_key.hex()
            self.address = Address(address_from_key_file)

    def sync_nonce(self, proxy: INetworkProvider):
        logger.info("Account.sync_nonce()")
        self.nonce = proxy.get_account(self.address).nonce
        logger.info(f"Account.sync_nonce() done: {self.nonce}")

    def sign_transaction(self, transaction: ITransaction) -> str:
        secret_key = bytes.fromhex(self.secret_key)
        signing_key: Any = nacl.signing.SigningKey(secret_key)

        data_json = transaction.serialize()
        signed = signing_key.sign(data_json)
        signature = signed.signature
        assert isinstance(signature, bytes)

        return signature.hex()


class LedgerAccount(Account):
    def __init__(self, account_index: int = 0, address_index: int = 0):
        super().__init__()
        self.account_index = account_index
        self.address_index = address_index
        self.address = Address(do_get_ledger_address(account_index=account_index, address_index=address_index))

    def sign_transaction(self, transaction: ITransaction) -> str:
        ledger_version = do_get_ledger_version()
        should_use_hash_signing = compare_versions(ledger_version, SIGN_USING_HASH_VERSION) >= 0
        if should_use_hash_signing:
            transaction.set_version(TX_HASH_SIGN_VERSION)
            transaction.set_options(TX_HASH_SIGN_OPTIONS)

        signature = do_sign_transaction_with_ledger(transaction.serialize(),
                                                    account_index=self.account_index,
                                                    address_index=self.address_index,
                                                    sign_using_hash=should_use_hash_signing)
        assert isinstance(signature, str)

        return signature


class Address(IAddress):
    HRP = "erd"
    PUBKEY_LENGTH = 32
    PUBKEY_STRING_LENGTH = PUBKEY_LENGTH * 2  # hex-encoded
    BECH32_LENGTH = 62
    _value_hex: str

    def __init__(self, value: Any):
        self._value_hex = ''

        if not value:
            return

        # Copy-constructor
        if isinstance(value, Address):
            value = value._value_hex

        # We keep a hex-encoded string as the "backing" value
        if len(value) == Address.PUBKEY_LENGTH:
            self._value_hex = value.hex()
        elif len(value) == Address.PUBKEY_STRING_LENGTH:
            self._value_hex = _as_string(value)
        elif len(value) == Address.BECH32_LENGTH:
            self._value_hex = _decode_bech32(value).hex()
        else:
            raise errors.BadAddressFormatError(value)

    def hex(self) -> str:
        self._assert_validity()
        return self._value_hex

    def bech32(self) -> str:
        self._assert_validity()
        pubkey = self.pubkey()
        b32 = bech32.bech32_encode(self.HRP, bech32.convertbits(pubkey, 8, 5))
        assert isinstance(b32, str)
        return b32

    def pubkey(self):
        self._assert_validity()
        pubkey = bytes.fromhex(self._value_hex)
        return pubkey

    def is_contract_address(self):
        return self.hex().startswith(constants.SC_HEX_PUBKEY_PREFIX)

    def _assert_validity(self):
        if self._value_hex == '':
            raise errors.EmptyAddressError()

    def __repr__(self):
        return self.bech32()

    @classmethod
    def zero(cls) -> 'Address':
        return Address("0" * 64)


def _as_string(value):
    if isinstance(value, str):
        return value
    return value.decode("utf-8")


def _decode_bech32(value):
    bech32_string = _as_string(value)
    hrp, value_bytes = bech32.bech32_decode(bech32_string)
    if hrp != Address.HRP:
        raise errors.BadAddressFormatError(value)
    decoded_bytes = bech32.convertbits(value_bytes, 5, 8, False)
    return bytearray(decoded_bytes)
