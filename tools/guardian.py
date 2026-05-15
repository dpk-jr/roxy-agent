#!/usr/bin/env python3
"""
Wallet Guardian — Mainnet + Testnet
Support: Send, Swap, Bridge, Approve

Usage:
  python3 guardian.py status                    # Cek balance mainnet
  python3 guardian.py status testnet            # Cek balance testnet
  python3 guardian.py send <chain> <to> <amount> # Send native token
  python3 guardian.py chains                    # List semua chain
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# ─── Config ────────────────────────────────────────────────────────────────

CRED_DIR = Path.home() / ".agent" / "credentials"
load_dotenv(CRED_DIR / "rescue-config.env")

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")
RESCUE_WALLET = os.getenv("RESCUE_EVM_WALLET", "YOUR_RESCUE_WALLET_ADDRESS")

# Load main wallet
with open(CRED_DIR / "roxy-evm-wallet.enc.json") as f:
    WALLET_DATA = json.load(f)
MAIN_WALLET = WALLET_DATA["address"]
ENCRYPTED_KEY = WALLET_DATA["encrypted_private_key"]
SALT = WALLET_DATA["salt"]

# ─── Chain Config ──────────────────────────────────────────────────────────

MAINNETS = {
    "eth": {"name": "Ethereum", "rpc": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}", "chain_id": 1, "native": "ETH"},
    "base": {"name": "Base", "rpc": "https://mainnet.base.org", "chain_id": 8453, "native": "ETH"},
    "arb": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "chain_id": 42161, "native": "ETH"},
    "op": {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "chain_id": 10, "native": "ETH"},
    "polygon": {"name": "Polygon", "rpc": "https://polygon-bor-rpc.publicnode.com", "chain_id": 137, "native": "POL"},
    "zksync": {"name": "zkSync Era", "rpc": "https://mainnet.era.zksync.io", "chain_id": 324, "native": "ETH"},
    "linea": {"name": "Linea", "rpc": "https://rpc.linea.build", "chain_id": 59144, "native": "ETH"},
    "scroll": {"name": "Scroll", "rpc": "https://rpc.scroll.io", "chain_id": 534352, "native": "ETH"},
    "blast": {"name": "Blast", "rpc": "https://rpc.blast.io", "chain_id": 81457, "native": "ETH"},
}

TESTNETS = {
    "eth-sepolia": {"name": "ETH Sepolia", "rpc": "https://ethereum-sepolia-rpc.publicnode.com", "chain_id": 11155111, "native": "ETH", "faucet": "https://sepoliafaucet.com"},
    "base-sepolia": {"name": "Base Sepolia", "rpc": "https://sepolia.base.org", "chain_id": 84532, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/base-sepolia"},
    "arb-sepolia": {"name": "Arb Sepolia", "rpc": "https://sepolia-rollup.arbitrum.io/rpc", "chain_id": 421614, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/arbitrum-sepolia"},
    "op-sepolia": {"name": "OP Sepolia", "rpc": "https://sepolia.optimism.io", "chain_id": 11155420, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/optimism-sepolia"},
    "polygon-amoy": {"name": "Polygon Amoy", "rpc": "https://rpc-amoy.polygon.technology", "chain_id": 80002, "native": "POL", "faucet": "https://faucet.polygon.technology"},
    "zksync-sepolia": {"name": "zkSync Sepolia", "rpc": "https://sepolia.era.zksync.dev", "chain_id": 300, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/zksync-sepolia"},
    "linea-sepolia": {"name": "Linea Sepolia", "rpc": "https://rpc.sepolia.linea.build", "chain_id": 59141, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/linea-sepolia"},
    "scroll-sepolia": {"name": "Scroll Sepolia", "rpc": "https://sepolia-rpc.scroll.io", "chain_id": 534351, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/scroll-sepolia"},
    "blast-sepolia": {"name": "Blast Sepolia", "rpc": "https://sepolia.blast.io", "chain_id": 168587773, "native": "ETH", "faucet": "https://www.alchemy.com/faucets/blast-sepolia"},
}


def get_chains(network="mainnet"):
    return MAINNETS if network == "mainnet" else TESTNETS


# ─── Helper ────────────────────────────────────────────────────────────────

def get_web3(chain_key: str, network="mainnet") -> Web3:
    chains = get_chains(network)
    return Web3(Web3.HTTPProvider(chains[chain_key]["rpc"], request_kwargs={"timeout": 15}))


def decrypt_private_key() -> str:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import base64
    master = os.getenv("ROXY_MASTER_PASSWORD", "")
    salt = base64.b64decode(SALT)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(master.encode()))
    return Fernet(key).decrypt(ENCRYPTED_KEY.encode()).decode()


# ─── Core Functions ────────────────────────────────────────────────────────

def show_status(network="mainnet"):
    chains = get_chains(network)
    label = "Mainnet" if network == "mainnet" else "Testnet"
    print(f"📊 {label} Status: {MAIN_WALLET}\n")
    for ck, c in chains.items():
        try:
            w3 = get_web3(ck, network)
            if not w3.is_connected():
                print(f"  ❌ {c['name']:20} | disconnected")
                continue
            bal = w3.from_wei(w3.eth.get_balance(Web3.to_checksum_address(MAIN_WALLET)), 'ether')
            n = w3.eth.get_transaction_count(Web3.to_checksum_address(MAIN_WALLET))
            e = "✅" if float(bal) > 0 else "⚪"
            print(f"  {e} {c['name']:20} | {float(bal):.8f} {c['native']} | nonce={n}")
        except Exception as ex:
            print(f"  ❌ {c['name']:20} | {str(ex)[:50]}")
    print(f"\n🆘 Rescue: {RESCUE_WALLET}")


def send_native(chain_key: str, to_addr: str, amount_eth: float, network="mainnet"):
    """Send native token (ETH/POL) to an address."""
    chains = get_chains(network)
    if chain_key not in chains:
        return {"error": f"Unknown chain: {chain_key}. Available: {', '.join(chains.keys())}"}
    
    config = chains[chain_key]
    w3 = get_web3(chain_key, network)
    
    if not w3.is_connected():
        return {"error": f"Cannot connect to {config['name']}"}
    
    from_addr = Web3.to_checksum_address(MAIN_WALLET)
    to_addr = Web3.to_checksum_address(to_addr)
    amount_wei = w3.to_wei(amount_eth, 'ether')
    
    # Check balance
    balance = w3.eth.get_balance(from_addr)
    if balance < amount_wei:
        return {"error": f"Insufficient balance. Have: {w3.from_wei(balance, 'ether'):.8f}, Need: {amount_eth}"}
    
    # Estimate gas
    gas_price = w3.eth.gas_price
    gas_limit = 21000
    gas_cost = gas_price * gas_limit
    
    if balance < amount_wei + gas_cost:
        max_send = w3.from_wei(balance - gas_cost, 'ether')
        return {"error": f"Not enough for gas. Max sendable: {max_send:.8f} {config['native']}"}
    
    pk = decrypt_private_key()
    nonce = w3.eth.get_transaction_count(from_addr)
    
    tx = {
        'from': from_addr,
        'to': to_addr,
        'value': amount_wei,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': config['chain_id'],
    }
    
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    return {
        "status": "success" if receipt.status == 1 else "failed",
        "chain": config['name'],
        "network": network,
        "from": from_addr,
        "to": to_addr,
        "amount": amount_eth,
        "native": config['native'],
        "tx_hash": tx_hash.hex(),
        "gas_used": receipt.gasUsed,
        "block": receipt.blockNumber,
    }


def list_chains():
    print("🔗 Available Chains:\n")
    print("  MAINNET:")
    for k, v in MAINNETS.items():
        print(f"    {k:15} — {v['name']}")
    print("\n  TESTNET:")
    for k, v in TESTNETS.items():
        print(f"    {k:15} — {v['name']}")
    print(f"\n  Usage: python3 guardian.py send <chain> <to> <amount> [--testnet]")


# ─── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    network = "testnet" if "--testnet" in sys.argv else "mainnet"
    
    if cmd == "status":
        show_status(network)
    elif cmd == "chains":
        list_chains()
    elif cmd == "send":
        if len(sys.argv) < 5:
            print("Usage: python3 guardian.py send <chain> <to> <amount> [--testnet]")
            sys.exit(1)
        chain = sys.argv[2]
        to = sys.argv[3]
        amount = float(sys.argv[4])
        result = send_native(chain, to, amount, network)
        print(json.dumps(result, indent=2))
    elif cmd == "sweep-all":
        # Sweep from main guardian
        print("Use: python3 guardian.py sweep-all (from guardian.py)")
    else:
        print(f"Unknown: {cmd}. Commands: status, chains, send")
