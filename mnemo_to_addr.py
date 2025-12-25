#!/usr/bin/env python3

import sys
from eth_account import Account

# Enable the HD wallet features
Account.enable_unaudited_hdwallet_features()

# Your 24-word mnemonic
mnemonic = "word1 word2 ... word24"

if sys.stdin:
    mnemonic = sys.stdin.read().strip()
# Derive the account
# By default, this uses the standard path: m/44'/60'/0'/0/0
account = Account.from_mnemonic(mnemonic)

print(f"Address: {account.address}")
