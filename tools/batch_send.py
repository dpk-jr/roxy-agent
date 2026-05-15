#!/usr/bin/env python3
"""
Batch Sender — Kirim native token ke banyak address sekaligus.

Usage:
  python3 batch_send.py --chain eth --file recipients.csv
  python3 batch_send.py --chain base --to 0xABC,0xDEF --amount 0.001

CSV format: address,amount
  0xABC123...,0.001
  0xDEF456...,0.002
"""

import os
import sys
import json
import csv
import argparse
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

CRED_DIR = Path.home() / ".agent" / "credentials"
load_dotenv(CRED_DIR / "rescue-config.env")

CHAINS = {
    "eth": {"name": "Ethereum", "rpc": f"https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', '')}", "chain_id": 1, "native": "ETH"},
    "base": {"name": "Base", "rpc": "https://mainnet.base.org", "chain_id": 8453, "native": "ETH"},
    "arb": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "chain_id": 42161, "native": "ETH"},
    "op": {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "chain_id": 10, "native": "ETH"},
    "polygon": {"name": "Polygon", "rpc": "https://polygon-bor-rpc.publicnode.com", "chain_id": 137, "native": "POL"},
    "zksync": {"name": "zkSync", "rpc": "https://mainnet.era.zksync.io", "chain_id": 324, "native": "ETH"},
    "linea": {"name": "Linea", "rpc": "https://rpc.linea.build", "chain_id": 59144, "native": "ETH"},
    "scroll": {"name": "Scroll", "rpc": "https://rpc.scroll.io", "chain_id": 534352, "native": "ETH"},
    "blast": {"name": "Blast", "rpc": "https://rpc.blast.io", "chain_id": 81457, "native": "ETH"},
}

# Testnets
TESTNETS = {
    "eth-sepolia": {"name": "ETH Sepolia", "rpc": "https://ethereum-sepolia-rpc.publicnode.com", "chain_id": 11155111, "native": "ETH"},
    "base-sepolia": {"name": "Base Sepolia", "rpc": "https://sepolia.base.org", "chain_id": 84532, "native": "ETH"},
    "arb-sepolia": {"name": "Arb Sepolia", "rpc": "https://sepolia-rollup.arbitrum.io/rpc", "chain_id": 421614, "native": "ETH"},
    "op-sepolia": {"name": "OP Sepolia", "rpc": "https://sepolia.optimism.io", "chain_id": 11155420, "native": "ETH"},
}


def decrypt_pk():
    with open(CRED_DIR / "roxy-evm-wallet.enc.json") as f:
        wallet = json.load(f)
    master = os.getenv("ROXY_MASTER_PASSWORD", "")
    salt = base64.b64decode(wallet["salt"])
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(master.encode()))
    return Fernet(key).decrypt(wallet["encrypted_private_key"].encode()).decode(), wallet["address"]


def batch_send(chain_key: str, recipients: list, dry_run: bool = False, testnet: bool = False):
    """
    Send native token to multiple recipients.
    recipients: list of (address, amount_float)
    """
    chains = TESTNETS if testnet else CHAINS
    if chain_key not in chains:
        return {"error": f"Unknown chain: {chain_key}"}
    
    config = chains[chain_key]
    w3 = Web3(Web3.HTTPProvider(config["rpc"], request_kwargs={"timeout": 30}))
    
    if not w3.is_connected():
        return {"error": f"Cannot connect to {config['name']}"}
    
    pk, from_addr = decrypt_pk()
    from_addr = Web3.to_checksum_address(from_addr)
    
    balance = w3.eth.get_balance(from_addr)
    balance_eth = float(w3.from_wei(balance, 'ether'))
    gas_price = w3.eth.gas_price
    gas_per_tx = gas_price * 21000
    
    total_send = sum(amt for _, amt in recipients)
    total_gas = float(w3.from_wei(gas_per_tx * len(recipients), 'ether'))
    
    print(f"\n📋 **Batch Send — {config['name']}**")
    print(f"   From: {from_addr}")
    print(f"   Balance: {balance_eth:.8f} {config['native']}")
    print(f"   Recipients: {len(recipients)}")
    print(f"   Total send: {total_send:.8f} {config['native']}")
    print(f"   Est. gas: {total_gas:.8f} {config['native']}")
    print(f"   Total needed: {total_send + total_gas:.8f} {config['native']}")
    
    if balance_eth < total_send + total_gas:
        return {"error": f"Insufficient balance. Need {total_send + total_gas:.8f}, have {balance_eth:.8f}"}
    
    if dry_run:
        print(f"\n🔍 **DRY RUN — no transactions sent**")
        for i, (to, amt) in enumerate(recipients):
            print(f"   {i+1}. {to} → {amt:.8f} {config['native']}")
        return {"status": "dry_run", "recipients": len(recipients)}
    
    # Execute
    results = []
    nonce = w3.eth.get_transaction_count(from_addr)
    
    print(f"\n⏳ Sending...")
    for i, (to_addr, amount) in enumerate(recipients):
        try:
            to_addr = Web3.to_checksum_address(to_addr)
            amount_wei = w3.to_wei(amount, 'ether')
            
            tx = {
                'from': from_addr,
                'to': to_addr,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': gas_price,
                'nonce': nonce + i,
                'chainId': config['chain_id'],
            }
            
            signed = w3.eth.account.sign_transaction(tx, pk)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            status = "✅" if receipt.status == 1 else "❌"
            print(f"   {status} {i+1}. {to_addr[:10]}... → {amount:.8f} | {tx_hash.hex()[:16]}...")
            
            results.append({
                "to": to_addr,
                "amount": amount,
                "tx_hash": tx_hash.hex(),
                "status": "success" if receipt.status == 1 else "failed",
                "gas_used": receipt.gasUsed,
            })
        except Exception as e:
            print(f"   ❌ {i+1}. {to_addr[:10]}... → ERROR: {str(e)[:50]}")
            results.append({"to": to_addr, "amount": amount, "status": "error", "error": str(e)[:100]})
    
    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n📊 **Result: {success}/{len(recipients)} succeeded**")
    
    return {"status": "completed", "results": results, "success": success, "total": len(recipients)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch send native token")
    parser.add_argument("--chain", required=True, help="Chain key (eth, base, arb, op, polygon, etc)")
    parser.add_argument("--file", help="CSV file: address,amount")
    parser.add_argument("--to", help="Comma-separated addresses")
    parser.add_argument("--amount", type=float, help="Amount per recipient (if --to used)")
    parser.add_argument("--testnet", action="store_true", help="Use testnet")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only")
    
    args = parser.parse_args()
    
    recipients = []
    if args.file:
        with open(args.file) as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    recipients.append((row[0].strip(), float(row[1].strip())))
    elif args.to and args.amount:
        for addr in args.to.split(","):
            recipients.append((addr.strip(), args.amount))
    else:
        print("Use --file CSV or --to ADDRS --amount AMT")
        sys.exit(1)
    
    batch_send(args.chain, recipients, dry_run=args.dry_run, testnet=args.testnet)
