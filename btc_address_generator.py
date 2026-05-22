from bip_utils import (
    Bip39SeedGenerator,
    Bip44, Bip44Coins,
    Bip49, Bip49Coins,
    Bip84, Bip84Coins,
    Bip86, Bip86Coins,
    Bip44Changes
)


def generate_bitcoin_addresses(mnemonic, index=0):
    """
    Generate all major Bitcoin address types from a mnemonic.

    Args:
        mnemonic (str): BIP39 seed phrase
        index (int): Address index

    Returns:
        dict: Dictionary containing all address types
    """

    # Generate seed
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    addresses = {}

    # ---------------------------------------------------
    # Legacy Address (starts with 1)
    # BIP44
    # ---------------------------------------------------
    bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)

    addresses["legacy"] = (
        bip44
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
        .PublicKey()
        .ToAddress()
    )

    # ---------------------------------------------------
    # P2SH SegWit Address (starts with 3)
    # BIP49
    # ---------------------------------------------------
    bip49 = Bip49.FromSeed(seed_bytes, Bip49Coins.BITCOIN)

    addresses["p2sh_segwit"] = (
        bip49
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
        .PublicKey()
        .ToAddress()
    )

    # ---------------------------------------------------
    # Native SegWit Address (starts with bc1)
    # BIP84
    # ---------------------------------------------------
    bip84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)

    addresses["native_segwit"] = (
        bip84
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
        .PublicKey()
        .ToAddress()
    )

    # ---------------------------------------------------
    # Taproot Address (starts with bc1p)
    # BIP86
    # ---------------------------------------------------
    bip86 = Bip86.FromSeed(seed_bytes, Bip86Coins.BITCOIN)

    addresses["taproot"] = (
        bip86
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
        .PublicKey()
        .ToAddress()
    )

    return addresses


# ---------------------------------------------------
# Example Usage
# ---------------------------------------------------

mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

result = generate_bitcoin_addresses(mnemonic)

print(result)