from bip_utils import (
    Bip39SeedGenerator,
    Bip44, Bip44Coins,
    Bip49, Bip49Coins,
    Bip84, Bip84Coins,
    Bip86, Bip86Coins,
    Bip44Changes,
    BtcAddrDecoder
)


def is_valid_btc_address(address: str) -> bool:
    """
    Validate Bitcoin address checksum.

    Returns:
        bool
    """

    try:
        BtcAddrDecoder.DecodeAddr(address)
        return True

    except Exception:
        return False


def generate_bitcoin_addresses(mnemonic, index=0):
    """
    Generate all major Bitcoin address types from a mnemonic.

    If ANY generated address fails checksum validation,
    return None.

    Args:
        mnemonic (str): BIP39 seed phrase
        index (int): Address index

    Returns:
        dict | None
    """

    try:

        # =====================================================
        # GENERATE SEED
        # =====================================================
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

        addresses = {}

        # =====================================================
        # LEGACY ADDRESS (starts with 1)
        # BIP44
        # =====================================================
        bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)

        legacy_address = (
            bip44
            .Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

        if not is_valid_btc_address(legacy_address):
            print("INVALID CHECKSUM => LEGACY ADDRESS")
            return None

        addresses["legacy"] = legacy_address

        # =====================================================
        # P2SH SEGWIT ADDRESS (starts with 3)
        # BIP49
        # =====================================================
        bip49 = Bip49.FromSeed(seed_bytes, Bip49Coins.BITCOIN)

        p2sh_address = (
            bip49
            .Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

        if not is_valid_btc_address(p2sh_address):
            print("INVALID CHECKSUM => P2SH SEGWIT ADDRESS")
            return None

        addresses["p2sh_segwit"] = p2sh_address

        # =====================================================
        # NATIVE SEGWIT ADDRESS (starts with bc1)
        # BIP84
        # =====================================================
        bip84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)

        native_segwit_address = (
            bip84
            .Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

        if not is_valid_btc_address(native_segwit_address):
            print("INVALID CHECKSUM => NATIVE SEGWIT ADDRESS")
            return None

        addresses["native_segwit"] = native_segwit_address

        # =====================================================
        # TAPROOT ADDRESS (starts with bc1p)
        # BIP86
        # =====================================================
        bip86 = Bip86.FromSeed(seed_bytes, Bip86Coins.BITCOIN)

        taproot_address = (
            bip86
            .Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

        if not is_valid_btc_address(taproot_address):
            print("INVALID CHECKSUM => TAPROOT ADDRESS")
            return None

        addresses["taproot"] = taproot_address

        # =====================================================
        # ALL CHECKSUMS VALID
        # =====================================================
        return addresses

    except Exception as e:

        print(f"ADDRESS GENERATION FAILED => {e}")

        return None


# # =========================================================
# # EXAMPLE USAGE
# # =========================================================

# mnemonic = (
#     "abandon abandon abandon abandon abandon "
#     "abandon abandon abandon abandon abandon "
#     "abandon about"
# )

# result = generate_bitcoin_addresses(mnemonic)

# print(result)