#!/usr/bin/env python3
"""
Wallet Rescue — Multi-chain asset rescue tool
Supports: ETH, Base, Arbitrum, Optimism, Polygon, zkSync, Linea, Scroll, Blast, Solana
"""

import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.agent/credentials/rescue-config.env"))

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY")
RESCUE_WALLET = os.getenv("RESCUE_WALLET_ADDRESS")

# ─── Chain Configuration ────────────────────────────────────────────────────

CHAINS = {
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native": "ETH",
        "alchemy": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://rpc.ankr.com/eth",
            "https://ethereum.publicnode.com",
            "https://eth.llamarpc.com",
        ],
        "explorer": "https://etherscan.io",
    },
    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native": "ETH",
        "alchemy": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://mainnet.base.org",
            "https://base.publicnode.com",
            "https://base.llamarpc.com",
        ],
        "explorer": "https://basescan.org",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native": "ETH",
        "alchemy": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.publicnode.com",
            "https://arbitrum.llamarpc.com",
        ],
        "explorer": "https://arbiscan.io",
    },
    "optimism": {
        "name": "Optimism",
        "chain_id": 10,
        "native": "ETH",
        "alchemy": f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://mainnet.optimism.io",
            "https://optimism.publicnode.com",
            "https://optimism.llamarpc.com",
        ],
        "explorer": "https://optimistic.etherscan.io",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native": "POL",
        "alchemy": f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://polygon-rpc.com",
            "https://polygon.publicnode.com",
            "https://polygon.llamarpc.com",
        ],
        "explorer": "https://polygonscan.com",
    },
    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "native": "ETH",
        "alchemy": f"https://zksync-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://mainnet.era.zksync.io",
            "https://zksync.drpc.org",
        ],
        "explorer": "https://explorer.zksync.io",
    },
    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "native": "ETH",
        "alchemy": f"https://linea-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://rpc.linea.build",
            "https://linea.drpc.org",
        ],
        "explorer": "https://lineascan.build",
    },
    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "native": "ETH",
        "alchemy": f"https://scroll-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://rpc.scroll.io",
            "https://scroll.drpc.org",
        ],
        "explorer": "https://scrollscan.com",
    },
    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "native": "ETH",
        "alchemy": f"https://blast-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://rpc.blast.io",
            "https://blast.drpc.org",
        ],
        "explorer": "https://blastscan.io",
    },
    "solana": {
        "name": "Solana",
        "chain_id": 0,
        "native": "SOL",
        "alchemy": f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "fallbacks": [
            "https://api.mainnet-beta.solana.com",
            "https://solana.publicnode.com",
        ],
        "explorer": "https://solscan.io",
    },
}


# ─── RPC Manager ────────────────────────────────────────────────────────────

async def get_working_rpc(chain_name: str) -> str | None:
    """Find working RPC for a chain, Alchemy first then fallbacks."""
    chain = CHAINS.get(chain_name)
    if not chain:
        return None

    urls = [chain["alchemy"]] + chain.get("fallbacks", [])

    for url in urls:
        try:
            async with httpx.AsyncClient() as client:
                if chain_name == "solana":
                    payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
                else:
                    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}

                resp = await client.post(url, json=payload, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if "result" in data or "error" not in data:
                        return url
        except Exception:
            continue

    return None


async def get_balance(chain_name: str, address: str) -> dict:
    """Get native balance for an address on a chain."""
    rpc = await get_working_rpc(chain_name)
    if not rpc:
        return {"error": f"No working RPC for {chain_name}"}

    try:
        async with httpx.AsyncClient() as client:
            if chain_name == "solana":
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [address],
                }
            else:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1,
                }

            resp = await client.post(rpc, json=payload, timeout=10)
            data = resp.json()

            if "result" in data:
                if chain_name == "solana":
                    lamports = data["result"]["value"]
                    return {"lamports": lamports, "sol": lamports / 1e9}
                else:
                    wei = int(data["result"], 16)
                    return {"wei": wei, "ether": wei / 1e18}
            return {"error": data.get("error", "Unknown error")}
    except Exception as e:
        return {"error": str(e)}


# ─── Scanner ────────────────────────────────────────────────────────────────

async def scan_wallet(address: str, chains: list = None):
    """Scan wallet across multiple chains."""
    if chains is None:
        chains = list(CHAINS.keys())

    print(f"\n{'='*60}")
    print(f"🔍 Scanning: {address}")
    print(f"{'='*60}\n")

    results = {}
    for chain_name in chains:
        chain = CHAINS[chain_name]
        balance = await get_balance(chain_name, address)
        results[chain_name] = balance

        if "error" in balance:
            print(f"  ⚠️ {chain['name']}: {balance['error']}")
        elif chain_name == "solana":
            print(f"  💰 {chain['name']}: {balance['sol']:.9f} SOL ({balance['lamports']} lamports)")
        else:
            print(f"  💰 {chain['name']}: {balance['ether']:.6f} {chain['native']}")

    print(f"\n{'='*60}")
    return results


async def check_rpc_health():
    """Check which RPCs are working."""
    print(f"\n{'='*60}")
    print(f"🏥 RPC Health Check")
    print(f"{'='*60}\n")

    for chain_name, chain in CHAINS.items():
        rpc = await get_working_rpc(chain_name)
        status = "✅" if rpc else "❌"
        source = "Alchemy" if rpc and ALCHEMY_KEY and ALCHEMY_KEY in rpc else "Fallback"
        print(f"  {status} {chain['name']}: {source}")

    print()


# ─── Main ───────────────────────────────────────────────────────────────────

async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python wallet_rescue.py scan <address>          — Scan wallet across all chains")
        print("  python wallet_rescue.py scan <address> eth base  — Scan specific chains")
        print("  python wallet_rescue.py health                  — Check RPC health")
        print("  python wallet_rescue.py chains                  — List supported chains")
        return

    cmd = sys.argv[1]

    if cmd == "health":
        await check_rpc_health()

    elif cmd == "chains":
        print(f"\n{'='*60}")
        print(f"⛓️ Supported Chains")
        print(f"{'='*60}\n")
        for name, chain in CHAINS.items():
            print(f"  • {chain['name']} ({chain['native']}) — Chain ID: {chain['chain_id']}")
        print()

    elif cmd == "scan":
        if len(sys.argv) < 3:
            print("Usage: python wallet_rescue.py scan <address> [chain1 chain2 ...]")
            return

        address = sys.argv[2]
        chains = sys.argv[3:] if len(sys.argv) > 3 else None
        await scan_wallet(address, chains)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    asyncio.run(main())
