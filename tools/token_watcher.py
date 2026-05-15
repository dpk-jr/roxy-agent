#!/usr/bin/env python3
"""
Token Watcher — Monitor incoming tokens & native on all chains.
Sends notification when any token with value arrives.

Usage:
  python3 token_watcher.py              # Run once check
  python3 token_watcher.py monitor      # Continuous monitor
  python3 token_watcher.py log          # Show recent deposits
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3

# Solana support
try:
    from solana.rpc.api import Client as SolanaClient
    from solders.pubkey import Pubkey
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

# ─── Config ────────────────────────────────────────────────────────────────

CRED_DIR = Path.home() / ".agent" / "credentials"
LOG_FILE = Path.home() / "projects" / "wallet-rescue" / "deposit_log.json"
load_dotenv(CRED_DIR / "rescue-config.env")

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")
WATCH_WALLET = os.getenv("ROXY_EVM_WALLET", "YOUR_WALLET_ADDRESS")
WATCH_WALLET_SOL = os.getenv("ROXY_SOLANA_WALLET", "YOUR_SOLANA_ADDRESS")

# ─── Chains ────────────────────────────────────────────────────────────────

CHAINS = {
    "eth": {"name": "Ethereum", "rpc": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}", "native": "ETH", "explorer": "https://etherscan.io"},
    "base": {"name": "Base", "rpc": "https://mainnet.base.org", "native": "ETH", "explorer": "https://basescan.org"},
    "arb": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "native": "ETH", "explorer": "https://arbiscan.io"},
    "op": {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "native": "ETH", "explorer": "https://optimistic.etherscan.io"},
    "polygon": {"name": "Polygon", "rpc": "https://polygon-bor-rpc.publicnode.com", "native": "POL", "explorer": "https://polygonscan.com"},
    "zksync": {"name": "zkSync", "rpc": "https://mainnet.era.zksync.io", "native": "ETH", "explorer": "https://explorer.zksync.io"},
    "linea": {"name": "Linea", "rpc": "https://rpc.linea.build", "native": "ETH", "explorer": "https://lineascan.build"},
    "scroll": {"name": "Scroll", "rpc": "https://rpc.scroll.io", "native": "ETH", "explorer": "https://scrollscan.com"},
    "blast": {"name": "Blast", "rpc": "https://rpc.blast.io", "native": "ETH", "explorer": "https://blastscan.io"},
}

# Common ERC-20 tokens to watch (address -> symbol)
KNOWN_TOKENS = {
    # Ethereum
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": {"symbol": "USDT", "decimals": 6, "chains": ["eth", "arb", "op", "polygon"]},
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {"symbol": "USDC", "decimals": 6, "chains": ["eth", "arb", "op", "polygon", "base"]},
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": {"symbol": "WBTC", "decimals": 8, "chains": ["eth"]},
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {"symbol": "WETH", "decimals": 18, "chains": ["eth"]},
}

# ─── State ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    state_file = Path.home() / "projects" / "wallet-rescue" / "watcher_state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {"nonces": {}, "balances": {}, "last_check": None}

def save_state(state: dict):
    state_file = Path.home() / "projects" / "wallet-rescue" / "watcher_state.json"
    state["last_check"] = datetime.now().isoformat()
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def log_deposit(entry: dict):
    deposits = []
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            deposits = json.load(f)
    deposits.append(entry)
    deposits = deposits[-100:]  # keep last 100
    with open(LOG_FILE, 'w') as f:
        json.dump(deposits, f, indent=2)


# ─── Check ─────────────────────────────────────────────────────────────────

def check_chain(chain_key: str, state: dict) -> list:
    """Check a single chain for new deposits. Returns list of alerts."""
    config = CHAINS[chain_key]
    alerts = []
    
    try:
        w3 = Web3(Web3.HTTPProvider(config["rpc"], request_kwargs={"timeout": 15}))
        if not w3.is_connected():
            return alerts
        
        addr = Web3.to_checksum_address(WATCH_WALLET)
        
        # Check native balance
        balance_wei = w3.eth.get_balance(addr)
        balance = float(w3.from_wei(balance_wei, 'ether'))
        
        old_balance = state.get("balances", {}).get(chain_key, 0)
        if balance > old_balance and old_balance > 0:
            diff = balance - old_balance
            alert = {
                "type": "native",
                "chain": config["name"],
                "token": config["native"],
                "amount": diff,
                "balance": balance,
                "time": datetime.now().isoformat(),
                "explorer": config["explorer"],
            }
            alerts.append(alert)
            log_deposit(alert)
        elif balance > old_balance and old_balance == 0 and balance > 0:
            alert = {
                "type": "native_first",
                "chain": config["name"],
                "token": config["native"],
                "amount": balance,
                "balance": balance,
                "time": datetime.now().isoformat(),
                "explorer": config["explorer"],
            }
            alerts.append(alert)
            log_deposit(alert)
        
        # Update balance
        if "balances" not in state:
            state["balances"] = {}
        state["balances"][chain_key] = balance
        
        # Check nonce (for tx activity)
        nonce = w3.eth.get_transaction_count(addr)
        old_nonce = state.get("nonces", {}).get(chain_key, 0)
        if nonce > old_nonce and old_nonce > 0:
            diff = nonce - old_nonce
            alerts.append({
                "type": "activity",
                "chain": config["name"],
                "tx_count": diff,
                "time": datetime.now().isoformat(),
            })
        
        if "nonces" not in state:
            state["nonces"] = {}
        state["nonces"][chain_key] = nonce
        
    except Exception as e:
        pass
    
    return alerts


def check_all() -> list:
    """Check all chains, return alerts."""
    state = load_state()
    all_alerts = []
    
    for chain_key in CHAINS:
        alerts = check_chain(chain_key, state)
        all_alerts.extend(alerts)
    
    # Check Solana
    if SOLANA_AVAILABLE:
        try:
            sol_client = SolanaClient("https://api.mainnet-beta.solana.com")
            addr = Pubkey.from_string(WATCH_WALLET_SOL)
            balance_resp = sol_client.get_balance(addr)
            balance = balance_resp.value / 1e9
            
            old_balance = state.get("balances", {}).get("solana", 0)
            if balance > old_balance and old_balance > 0:
                diff = balance - old_balance
                alert = {
                    "type": "native",
                    "chain": "Solana",
                    "token": "SOL",
                    "amount": diff,
                    "balance": balance,
                    "time": datetime.now().isoformat(),
                    "explorer": "https://solscan.io",
                }
                all_alerts.append(alert)
                log_deposit(alert)
            elif balance > old_balance and old_balance == 0 and balance > 0:
                alert = {
                    "type": "native_first",
                    "chain": "Solana",
                    "token": "SOL",
                    "amount": balance,
                    "balance": balance,
                    "time": datetime.now().isoformat(),
                    "explorer": "https://solscan.io",
                }
                all_alerts.append(alert)
                log_deposit(alert)
            
            if "balances" not in state:
                state["balances"] = {}
            state["balances"]["solana"] = balance
        except Exception as e:
            pass
    
    save_state(state)
    return all_alerts


def format_alerts(alerts: list) -> str:
    """Format alerts as notification message."""
    if not alerts:
        return ""
    
    lines = ["🔔 **TOKEN MASUK!**\n"]
    
    for a in alerts:
        if a["type"] in ("native", "native_first"):
            lines.append(f"💰 **+{a['amount']:.8f} {a['token']}**")
            lines.append(f"   Chain: {a['chain']}")
            lines.append(f"   Balance: {a['balance']:.8f} {a['token']}")
            lines.append(f"   Explorer: {a['explorer']}/address/{WATCH_WALLET}")
            lines.append("")
        elif a["type"] == "activity":
            lines.append(f"⚡ **{a['tx_count']} new tx** on {a['chain']}")
            lines.append("")
    
    lines.append(f"📍 Wallet: `{WATCH_WALLET}`")
    return "\n".join(lines)


# ─── Monitor ───────────────────────────────────────────────────────────────

async def monitor_loop(interval: int = 30):
    """Continuous monitoring loop."""
    print(f"👁️ Token Watcher — Monitoring {WATCH_WALLET}")
    print(f"   Chains: {len(CHAINS)}")
    print(f"   Interval: {interval}s")
    print(f"   Press Ctrl+C to stop\n")
    
    # Init state
    state = load_state()
    for chain_key in CHAINS:
        try:
            w3 = Web3(Web3.HTTPProvider(CHAINS[chain_key]["rpc"], request_kwargs={"timeout": 15}))
            if w3.is_connected():
                addr = Web3.to_checksum_address(WATCH_WALLET)
                bal = float(w3.from_wei(w3.eth.get_balance(addr), 'ether'))
                nonce = w3.eth.get_transaction_count(addr)
                state.setdefault("balances", {})[chain_key] = bal
                state.setdefault("nonces", {})[chain_key] = nonce
                print(f"   ✅ {CHAINS[chain_key]['name']}: {bal:.8f} {CHAINS[chain_key]['native']}")
        except:
            pass
    save_state(state)
    print(f"\n👀 Watching...\n")
    
    while True:
        try:
            alerts = check_all()
            if alerts:
                msg = format_alerts(alerts)
                print(msg)
                print("---")
            else:
                print(f"  ⏪ {datetime.now().strftime('%H:%M:%S')} — no changes")
            await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n🛑 Watcher stopped.")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(interval)


# ─── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: one-time check
        alerts = check_all()
        if alerts:
            print(format_alerts(alerts))
        else:
            print("No new deposits detected.")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    if cmd == "monitor":
        asyncio.run(monitor_loop())
    elif cmd == "log":
        if LOG_FILE.exists():
            with open(LOG_FILE) as f:
                deposits = json.load(f)
            for d in deposits[-10:]:
                print(f"  {d['time']} | {d['chain']} | +{d['amount']:.8f} {d['token']}")
        else:
            print("No deposits logged yet.")
    else:
        print(f"Unknown: {cmd}. Commands: (none), monitor, log")
