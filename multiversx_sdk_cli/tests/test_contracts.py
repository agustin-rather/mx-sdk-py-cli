import logging
from pathlib import Path

import pytest
from Cryptodome.Hash import keccak
from multiversx_sdk_core.address import Address, compute_contract_address

from multiversx_sdk_cli import errors
from multiversx_sdk_cli.accounts import Account
from multiversx_sdk_cli.constants import DEFAULT_HRP
from multiversx_sdk_cli.contract_verification import _create_request_signature
from multiversx_sdk_cli.contracts import (SmartContract,
                                          _interpret_as_number_if_safely,
                                          _prepare_argument)

logging.basicConfig(level=logging.INFO)

testdata_folder = Path(__file__).parent / "testdata"


def test_playground_keccak():
    hexhash = keccak.new(digest_bits=256).update(b"").hexdigest()
    assert hexhash == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_compute_address():
    contract = SmartContract()
    contract.owner = Account(address=Address.from_hex("93ee6143cdc10ce79f15b2a6c2ad38e9b6021c72a1779051f47154fd54cfbd5e", DEFAULT_HRP))

    contract.owner.nonce = 0
    contract.address = compute_contract_address(contract.owner.address, contract.owner.nonce, DEFAULT_HRP)
    assert contract.address
    assert contract.address.hex() == "00000000000000000500bb652200ed1f994200ab6699462cab4b1af7b11ebd5e"
    assert contract.address.bech32() == "erd1qqqqqqqqqqqqqpgqhdjjyq8dr7v5yq9tv6v5vt9tfvd00vg7h40q6779zn"

    contract.owner.nonce = 1
    contract.address = compute_contract_address(contract.owner.address, contract.owner.nonce, DEFAULT_HRP)
    assert contract.address.hex() == "000000000000000005006e4f90488e27342f9a46e1809452c85ee7186566bd5e"
    assert contract.address.bech32() == "erd1qqqqqqqqqqqqqpgqde8eqjywyu6zlxjxuxqfg5kgtmn3setxh40qen8egy"


def test_prepare_argument():
    assert _prepare_argument('0x5') == '05'
    assert _prepare_argument('5') == '05'
    assert _prepare_argument('0x05f') == '005F'
    assert _prepare_argument('0xaaa') == '0AAA'
    assert _prepare_argument('str:a') == '61'
    assert _prepare_argument('str:aaa') == '616161'

    assert _prepare_argument(155) == '9B'
    assert _prepare_argument('155') == '9B'

    assert \
        _prepare_argument('erd1qr9av6ar4ymr05xj93jzdxyezdrp6r4hz6u0scz4dtzvv7kmlldse7zktc') == \
        '00CBD66BA3A93637D0D22C6426989913461D0EB716B8F860556AC4C67ADBFFDB'

    assert _prepare_argument('str:TOK-123456') == '544F4B2D313233343536'
    assert _prepare_argument('str:TOK-a1c2ef') == '544F4B2D613163326566'
    assert _prepare_argument('str:TokenName') == '546F6B656E4E616D65'
    assert _prepare_argument('str:/#%placeholder&*') == '2F2325706C616365686F6C646572262A'

    assert _prepare_argument(True) == "01"
    assert _prepare_argument(False) == "00"
    assert _prepare_argument("TrUe") == "01"
    assert _prepare_argument("fAlSe") == "00"

    with pytest.raises(errors.UnknownArgumentFormat):
        _ = _prepare_argument('0x05fq')

    assert _prepare_argument("str:") == ""
    assert _prepare_argument("0x") == ""


def test_contract_verification_create_request_signature():
    account = Account(pem_file=str(testdata_folder / "walletKey.pem"))
    contract_address = Address.from_bech32("erd1qqqqqqqqqqqqqpgqeyj9g344pqguukajpcfqz9p0rfqgyg4l396qespdck")
    request_payload = b"test"
    signature = _create_request_signature(account, contract_address, request_payload)

    assert signature.hex() == "30111258cc42ea08e0c6a3e053cc7086a88d614b8b119a244904e9a19896c73295b2fe5c520a1cb07cfe20f687deef9f294a0a05071e85c78a70a448ea5f0605"


def test_interpret_as_number_if_safely():
    assert _interpret_as_number_if_safely("") == 0
    assert _interpret_as_number_if_safely("0x5") == 5
    assert _interpret_as_number_if_safely("FF") == 255
