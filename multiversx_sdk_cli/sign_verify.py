from typing import Dict

from multiversx_sdk_core import Address, MessageV1
from multiversx_sdk_wallet import UserVerifier

from multiversx_sdk_cli.accounts import Account


class SignedMessage:
    def __init__(self, address: str, message: str, signature: str) -> None:
        self.address = address
        self.message = message

        hex_prefixes = ["0x", "0X"]
        signature_start_sequence = signature[0:2]

        if signature_start_sequence in hex_prefixes:
            signature = signature[2:]

        self.signature = signature

    def verify_signature(self) -> bool:
        verifier = UserVerifier.from_address(Address.from_bech32(self.address))
        verifiable_message = MessageV1.from_string(self.message)
        verifiable_message.signature = bytes.fromhex(self.signature)
        is_signed = verifier.verify(verifiable_message)
        return is_signed

    def to_dictionary(self) -> Dict[str, str]:
        return {
            "address": self.address,
            "message": self.message,
            "signature": "0x" + self.signature
        }


def sign_message(message: str, account: Account) -> SignedMessage:
    signature = account.sign_message(message.encode())
    return SignedMessage(account.address.bech32(), message, signature)
