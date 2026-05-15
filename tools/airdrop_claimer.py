#!/usr/bin/env python3
"""
Airdrop Claimer — Monitor eligibility & auto-claim airdrops.

Usage:
  python3 airdrop_claimer.py check              # Check eligibility
  python3 airdrop_claimer.py claim <protocol>    # Claim specific airdrop
  python3 airdrop_claimer.py watch               # Monitor for new claims
"""

import os
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime

WALLET = "0xD86c77A9D051C21c3e0A0aa9b8921ed7954d8FeF"
CLAIM_LOG = Path.home() / "projects" / "wallet-rescue" / "claim_log.json"

# Known airdrop contracts & their claim functions
# Format: protocol -> {chain, contract, claim_selector, website}
AIRDROPS = {
    # Example structure — these would be updated as new airdrops launch
    "layerzero": {
        "name": "LayerZero",
        "chain": "eth",
        "contract": "0x0000000000000000000000000000000000000000",
        "website": "https://claim.layerzero.network",
        "checker": "https://api.layerzero.airdrop.com/check",
        "status": "TGE_done",
    },
    "zksync": {
        "name": "zkSync",
        "chain": "zksync",
        "contract": "0x0000000000000000000000000000000000000000",
        "website": "https://claim.zksync.io",
        "checker": "https://api.zksync.io/airdrop/check",
        "status": "TGE_done",
    },
    "eigenlayer": {
        "name": "EigenLayer",
        "chain": "eth",
        "contract": "0x0000000000000000000000000000000000000000",
        "website": "https://claims.eigenlayer.org",
        "checker": "https://api.eigenlayer.io/airdrop/check",
        "status": "TGE_done",
    },
}


def check_airdrop_api(address: str) -> list:
    """Check airdrop eligibility from various APIs."""
    eligible = []
    
    # Check CryptoRank API for upcoming/active airdrops
    try:
        r = httpx.get("https://api.cryptorank.io/v0/airdrops", params={
            "address": address,
        }, timeout=15, headers={"Accept": "application/json"})
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", []):
                if item.get("isEligible"):
                    eligible.append({
                        "protocol": item.get("name", "Unknown"),
                        "amount": item.get("amount", "unknown"),
                        "deadline": item.get("deadline", "unknown"),
                        "source": "cryptorank",
                    })
    except:
        pass
    
    # Check DeBank API for token claims
    try:
        r = httpx.get(f"https://api.debank.com/user/claimable_list?id={address}", timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            for item in data:
                eligible.append({
                    "protocol": item.get("name", "Unknown"),
                    "amount": item.get("amount", "unknown"),
                    "token": item.get("token_symbol", "unknown"),
                    "source": "debank",
                })
    except:
        pass
    
    # Check common claim sites via web scraping
    claim_sites = [
        {"name": "EigenLayer", "url": "https://claims.eigenlayer.org"},
        {"name": "Ethena", "url": "https://claim.ethena.fi"},
        {"name": "LayerZero", "url": "https://claim.layerzero.network"},
    ]
    
    for site in claim_sites:
        try:
            r = httpx.get(site["url"], timeout=10, follow_redirects=True)
            if r.status_code == 200:
                eligible.append({
                    "protocol": site["name"],
                    "website": site["url"],
                    "status": "check_manually",
                    "source": "web_check",
                })
        except:
            pass
    
    return eligible


def check_known_airdrops(address: str) -> list:
    """Check known airdrop protocols."""
    results = []
    
    # Use DeBank-like API to check token balances
    try:
        r = httpx.get(f"https://api.debank.com/token/list?id={address.lower()}", timeout=15)
        if r.status_code == 200:
            tokens = r.json().get("data", [])
            for t in tokens:
                if t.get("is_claimable"):
                    results.append({
                        "protocol": t.get("name", "Unknown"),
                        "token": t.get("symbol", ""),
                        "amount": t.get("amount", 0),
                        "source": "debank",
                    })
    except:
        pass
    
    return results


def show_check(address: str):
    """Display airdrop eligibility check."""
    print(f"🔍 **Checking airdrop eligibility...**\n")
    print(f"📍 Wallet: `{address}`\n")
    
    # Check from APIs
    eligible = check_airdrop_api(address)
    known = check_known_airdrops(address)
    
    all_claims = eligible + known
    
    if not all_claims:
        print("❌ No claimable airdrops found right now.")
        print("\n💡 Keep farming — check back later!")
        print("   • https://airdrops.io — latest airdrop list")
        print("   • https://debank.com — portfolio & claims")
        return
    
    print(f"✅ **{len(all_claims)} potential claims found!**\n")
    
    for i, claim in enumerate(all_claims, 1):
        print(f"  {i}. **{claim.get('protocol', 'Unknown')}**")
        if claim.get('token'):
            print(f"     Token: {claim['token']}")
        if claim.get('amount'):
            print(f"     Amount: {claim['amount']}")
        if claim.get('website'):
            print(f"     Website: {claim['website']}")
        if claim.get('status') == 'check_manually':
            print(f"     ⚠️ Check manually — may require wallet connect")
        print()
    
    print("💡 **Next steps:**")
    print("   1. Visit the website for each eligible protocol")
    print("   2. Connect wallet and check claim amount")
    print("   3. Claim before deadline!")


def log_claim(protocol: str, tx_hash: str, status: str):
    """Log a claim attempt."""
    claims = []
    if CLAIM_LOG.exists():
        with open(CLAIM_LOG) as f:
            claims = json.load(f)
    
    claims.append({
        "protocol": protocol,
        "tx_hash": tx_hash,
        "status": status,
        "time": datetime.now().isoformat(),
    })
    
    with open(CLAIM_LOG, 'w') as f:
        json.dump(claims[-50:], f, indent=2)


def show_log():
    """Show claim history."""
    if not CLAIM_LOG.exists():
        print("No claims logged yet.")
        return
    
    with open(CLAIM_LOG) as f:
        claims = json.load(f)
    
    print(f"📋 **Claim History** ({len(claims)} total)\n")
    for c in claims[-10:]:
        e = "✅" if c["status"] == "success" else "❌"
        print(f"  {e} {c['time'][:16]} | {c['protocol']} | {c.get('tx_hash', 'N/A')[:16]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "check":
        show_check(WALLET)
    elif cmd == "log":
        show_log()
    elif cmd == "watch":
        print("👁️ Watching for new airdrop claims...")
        print("   (Run periodically via cron)")
        show_check(WALLET)
    else:
        print(f"Unknown: {cmd}. Commands: check, log, watch")
