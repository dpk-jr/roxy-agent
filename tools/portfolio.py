#!/usr/bin/env python3
"""
Portfolio Tracker — Cek balance semua chain (EVM + Solana) dalam USD.

Usage:
  python3 portfolio.py              # Full portfolio
  python3 portfolio.py evm          # EVM only
  python3 portfolio.py solana       # Solana only
"""

import os
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

CRED_DIR = Path.home() / ".agent" / "credentials"
load_dotenv(CRED_DIR / "rescue-config.env")

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")

EVM_WALLET = os.getenv("ROXY_EVM_WALLET", "YOUR_WALLET_ADDRESS")
SOL_WALLET = os.getenv("ROXY_SOLANA_WALLET", "YOUR_SOLANA_ADDRESS")

CHAINS = {
    "eth": {"name": "Ethereum", "rpc": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}", "native": "ETH"},
    "base": {"name": "Base", "rpc": "https://mainnet.base.org", "native": "ETH"},
    "arb": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "native": "ETH"},
    "op": {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "native": "ETH"},
    "polygon": {"name": "Polygon", "rpc": "https://polygon-bor-rpc.publicnode.com", "native": "POL"},
    "zksync": {"name": "zkSync", "rpc": "https://mainnet.era.zksync.io", "native": "ETH"},
    "linea": {"name": "Linea", "rpc": "https://rpc.linea.build", "native": "ETH"},
    "scroll": {"name": "Scroll", "rpc": "https://rpc.scroll.io", "native": "ETH"},
    "blast": {"name": "Blast", "rpc": "https://rpc.blast.io", "native": "ETH"},
}


def get_eth_price() -> float:
    """Get ETH price in USD from CoinGecko."""
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=10)
        return r.json()["ethereum"]["usd"]
    except:
        return 0


def get_sol_price() -> float:
    """Get SOL price in USD."""
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=10)
        return r.json()["solana"]["usd"]
    except:
        return 0


def get_pol_price() -> float:
    """Get POL price in USD."""
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/simple/price?ids=matic-network&vs_currencies=usd", timeout=10)
        return r.json()["matic-network"]["usd"]
    except:
        return 0


def check_evm():
    """Check all EVM chains."""
    eth_price = get_eth_price()
    pol_price = get_pol_price()
    
    results = []
    total_usd = 0
    
    for key, cfg in CHAINS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(cfg["rpc"], request_kwargs={"timeout": 10}))
            if not w3.is_connected():
                results.append({"chain": cfg["name"], "status": "disconnected"})
                continue
            
            bal_wei = w3.eth.get_balance(Web3.to_checksum_address(EVM_WALLET))
            bal = float(w3.from_wei(bal_wei, 'ether'))
            
            price = pol_price if cfg["native"] == "POL" else eth_price
            usd = bal * price
            total_usd += usd
            
            results.append({
                "chain": cfg["name"],
                "native": cfg["native"],
                "balance": bal,
                "price": price,
                "usd": usd,
            })
        except Exception as e:
            results.append({"chain": cfg["name"], "status": "error", "error": str(e)[:50]})
    
    return results, total_usd


def check_solana():
    """Check Solana balance."""
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey
        
        client = Client("https://api.mainnet-beta.solana.com")
        addr = Pubkey.from_string(SOL_WALLET)
        resp = client.get_balance(addr)
        bal = resp.value / 1e9
        sol_price = get_sol_price()
        usd = bal * sol_price
        
        return {"chain": "Solana", "native": "SOL", "balance": bal, "price": sol_price, "usd": usd}, usd
    except Exception as e:
        return {"chain": "Solana", "status": "error", "error": str(e)[:50]}, 0


def show_portfolio(mode="all"):
    """Display portfolio."""
    total_usd = 0
    
    print("📊 **ROXY PORTFOLIO**\n")
    
    if mode in ("all", "evm"):
        results, evm_usd = check_evm()
        total_usd += evm_usd
        print("🔗 **EVM Chains:**")
        for r in results:
            if "status" in r and r["status"] in ("disconnected", "error"):
                print(f"  ❌ {r['chain']:12} | {r.get('status', 'error')}")
            else:
                usd_str = f"${r['usd']:.2f}" if r['usd'] > 0 else "$0.00"
                print(f"  {'✅' if r['balance'] > 0 else '⚪'} {r['chain']:12} | {r['balance']:.8f} {r['native']} | {usd_str}")
        print()
    
    if mode in ("all", "solana"):
        sol_result, sol_usd = check_solana()
        total_usd += sol_usd
        print("☀️ **Solana:**")
        if "status" in sol_result:
            print(f"  ❌ Solana       | {sol_result.get('status', 'error')}")
        else:
            usd_str = f"${sol_result['usd']:.2f}" if sol_result['usd'] > 0 else "$0.00"
            e = "✅" if sol_result['balance'] > 0 else "⚪"
            print(f"  {e} Solana       | {sol_result['balance']:.9f} SOL | {usd_str}")
        print()
    
    print(f"💰 **Total: ${total_usd:.2f} USD**")
    print(f"\n📍 EVM: `{EVM_WALLET}`")
    print(f"📍 SOL: `{SOL_WALLET}`")


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    show_portfolio(mode)
