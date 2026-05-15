#!/usr/bin/env python3
"""
Roxy Automation — Portfolio, Batch Send, Airdrop, Security.

Usage:
  python3 automation.py portfolio                    # Cek semua balance + USD
  python3 automation.py gas                          # Cek gas price semua chain
  python3 automation.py airdrop                      # Check airdrop eligibility
  python3 automation.py send --chain base --to 0xABC --amount 0.001
  python3 automation.py send --chain eth --file recipients.csv --dry-run
  python3 automation.py approvals --chain eth        # Cek token approvals
  python3 automation.py revoke --chain eth --token <ADDR> --spender <ADDR>
  python3 automation.py scam --chain eth             # Cek scam tokens
"""

import os
import sys
import json
import csv
import argparse
import httpx
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

# ─── Config ────────────────────────────────────────────────────────────────

CRED_DIR = Path.home() / ".agent" / "credentials"
LOG_DIR = Path.home() / "projects" / "wallet-rescue"
load_dotenv(CRED_DIR / "rescue-config.env")

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")
EVM_WALLET = os.getenv("ROXY_EVM_WALLET", "YOUR_WALLET_ADDRESS")
SOL_WALLET = os.getenv("ROXY_SOLANA_WALLET", "YOUR_SOLANA_ADDRESS")

# ─── Chains ────────────────────────────────────────────────────────────────

CHAINS = {
    "eth": {"name": "Ethereum", "rpc": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}", "chain_id": 1, "native": "ETH"},
    "base": {"name": "Base", "rpc": "https://mainnet.base.org", "chain_id": 8453, "native": "ETH"},
    "arb": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "chain_id": 42161, "native": "ETH"},
    "op": {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "chain_id": 10, "native": "ETH"},
    "polygon": {"name": "Polygon", "rpc": "https://polygon-bor-rpc.publicnode.com", "chain_id": 137, "native": "POL"},
    "zksync": {"name": "zkSync", "rpc": "https://mainnet.era.zksync.io", "chain_id": 324, "native": "ETH"},
    "linea": {"name": "Linea", "rpc": "https://rpc.linea.build", "chain_id": 59144, "native": "ETH"},
    "scroll": {"name": "Scroll", "rpc": "https://rpc.scroll.io", "chain_id": 534352, "native": "ETH"},
    "blast": {"name": "Blast", "rpc": "https://rpc.blast.io", "chain_id": 81457, "native": "ETH"},
}

TESTNETS = {
    "eth-sepolia": {"name": "ETH Sepolia", "rpc": "https://ethereum-sepolia-rpc.publicnode.com", "chain_id": 11155111, "native": "ETH"},
    "base-sepolia": {"name": "Base Sepolia", "rpc": "https://sepolia.base.org", "chain_id": 84532, "native": "ETH"},
    "arb-sepolia": {"name": "Arb Sepolia", "rpc": "https://sepolia-rollup.arbitrum.io/rpc", "chain_id": 421614, "native": "ETH"},
    "op-sepolia": {"name": "OP Sepolia", "rpc": "https://sepolia.optimism.io", "chain_id": 11155420, "native": "ETH"},
}


# ─── Helpers ───────────────────────────────────────────────────────────────

def decrypt_pk():
    with open(CRED_DIR / "roxy-evm-wallet.enc.json") as f:
        wallet = json.load(f)
    master = os.getenv("ROXY_MASTER_PASSWORD", "")
    salt = base64.b64decode(wallet["salt"])
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(master.encode()))
    return Fernet(key).decrypt(wallet["encrypted_private_key"].encode()).decode(), wallet["address"]


def get_price(coin: str) -> float:
    """Get USD price from CoinGecko."""
    ids = {"ETH": "ethereum", "SOL": "solana", "POL": "matic-network"}
    try:
        r = httpx.get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids.get(coin, 'ethereum')}&vs_currencies=usd", timeout=10)
        return r.json().get(ids.get(coin, "ethereum"), {}).get("usd", 0)
    except:
        return 0


def get_web3(chain_key: str, testnet: bool = False) -> Web3:
    chains = TESTNETS if testnet else CHAINS
    return Web3(Web3.HTTPProvider(chains[chain_key]["rpc"], request_kwargs={"timeout": 15}))


# ─── Portfolio ─────────────────────────────────────────────────────────────

def cmd_portfolio():
    """Show full portfolio across all chains."""
    eth_price = get_price("ETH")
    pol_price = get_price("POL")
    sol_price = get_price("SOL")
    
    total_usd = 0
    
    print("📊 **ROXY PORTFOLIO**\n")
    print(f"   ETH: ${eth_price:,.2f} | POL: ${pol_price:,.2f} | SOL: ${sol_price:,.2f}\n")
    
    # EVM chains
    print("🔗 **EVM Chains:**")
    for key, cfg in CHAINS.items():
        try:
            w3 = get_web3(key)
            if not w3.is_connected():
                print(f"  ❌ {cfg['name']:12} | disconnected")
                continue
            bal = float(w3.from_wei(w3.eth.get_balance(Web3.to_checksum_address(EVM_WALLET)), 'ether'))
            price = pol_price if cfg["native"] == "POL" else eth_price
            usd = bal * price
            total_usd += usd
            e = "✅" if bal > 0 else "⚪"
            print(f"  {e} {cfg['name']:12} | {bal:.8f} {cfg['native']} | ${usd:.2f}")
        except Exception as ex:
            print(f"  ❌ {cfg['name']:12} | error")
    
    # Solana
    print("\n☀️ **Solana:**")
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey
        client = Client("https://api.mainnet-beta.solana.com")
        resp = client.get_balance(Pubkey.from_string(SOL_WALLET))
        bal = resp.value / 1e9
        usd = bal * sol_price
        total_usd += usd
        e = "✅" if bal > 0 else "⚪"
        print(f"  {e} Solana       | {bal:.9f} SOL | ${usd:.2f}")
    except:
        print(f"  ❌ Solana       | error")
    
    print(f"\n💰 **Total: ${total_usd:.2f} USD**")
    print(f"\n📍 EVM: `{EVM_WALLET}`")
    print(f"📍 SOL: `{SOL_WALLET}`")


# ─── Gas Tracker ───────────────────────────────────────────────────────────

def cmd_gas():
    """Show gas prices on all chains."""
    print("⛽ **Gas Prices**\n")
    for key, cfg in CHAINS.items():
        try:
            w3 = get_web3(key)
            if not w3.is_connected():
                print(f"  ❌ {cfg['name']:12} | disconnected")
                continue
            gas = w3.eth.gas_price
            gwei = float(w3.from_wei(gas, 'gwei'))
            usd_per_tx = float(w3.from_wei(gas * 21000, 'ether')) * get_price("ETH")
            e = "🟢" if gwei < 5 else "🟡" if gwei < 20 else "🔴"
            print(f"  {e} {cfg['name']:12} | {gwei:.2f} Gwei | ~${usd_per_tx:.4f}/tx")
        except:
            print(f"  ❌ {cfg['name']:12} | error")


# ─── Batch Send ────────────────────────────────────────────────────────────

def cmd_send(chain_key: str, recipients: list, dry_run: bool = False, testnet: bool = False):
    """Send native token to multiple recipients."""
    chains = TESTNETS if testnet else CHAINS
    if chain_key not in chains:
        print(f"❌ Unknown chain: {chain_key}")
        print(f"   Available: {', '.join(chains.keys())}")
        return
    
    config = chains[chain_key]
    w3 = get_web3(chain_key, testnet)
    
    if not w3.is_connected():
        print(f"❌ Cannot connect to {config['name']}")
        return
    
    pk, from_addr = decrypt_pk()
    from_addr = Web3.to_checksum_address(from_addr)
    balance = w3.eth.get_balance(from_addr)
    balance_eth = float(w3.from_wei(balance, 'ether'))
    gas_price = w3.eth.gas_price
    
    total_send = sum(amt for _, amt in recipients)
    total_gas = float(w3.from_wei(gas_price * 21000 * len(recipients), 'ether'))
    
    print(f"\n📋 **Batch Send — {config['name']}{' (TESTNET)' if testnet else ''}**")
    print(f"   From: {from_addr}")
    print(f"   Balance: {balance_eth:.8f} {config['native']}")
    print(f"   Recipients: {len(recipients)}")
    print(f"   Total send: {total_send:.8f} {config['native']}")
    print(f"   Est. gas: {total_gas:.8f} {config['native']}")
    
    if balance_eth < total_send + total_gas:
        print(f"\n❌ Insufficient balance!")
        return
    
    if dry_run:
        print(f"\n🔍 **DRY RUN** — no transactions sent")
        for i, (to, amt) in enumerate(recipients, 1):
            print(f"   {i}. {to} → {amt:.8f} {config['native']}")
        return
    
    # Execute
    nonce = w3.eth.get_transaction_count(from_addr)
    success = 0
    
    print(f"\n⏳ Sending...")
    for i, (to_addr, amount) in enumerate(recipients, 1):
        try:
            to_addr = Web3.to_checksum_address(to_addr)
            tx = {
                'from': from_addr, 'to': to_addr,
                'value': w3.to_wei(amount, 'ether'),
                'gas': 21000, 'gasPrice': gas_price,
                'nonce': nonce + i - 1, 'chainId': config['chain_id'],
            }
            signed = w3.eth.account.sign_transaction(tx, pk)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            s = "✅" if receipt.status == 1 else "❌"
            print(f"   {s} {i}. {to_addr[:10]}... → {amount:.8f} | {tx_hash.hex()[:16]}...")
            if receipt.status == 1:
                success += 1
        except Exception as e:
            print(f"   ❌ {i}. {to_addr[:10]}... → ERROR: {str(e)[:50]}")
    
    print(f"\n📊 **Result: {success}/{len(recipients)} succeeded**")


# ─── Airdrop Checker ───────────────────────────────────────────────────────

def cmd_airdrop():
    """Check airdrop eligibility."""
    print(f"🔍 **Checking airdrop eligibility...**\n")
    print(f"📍 Wallet: `{EVM_WALLET}`\n")
    
    found = []
    
    # Check DeBank for claimable tokens
    try:
        r = httpx.get(f"https://api.debank.com/user/claimable_list?id={EVM_WALLET.lower()}", timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            for item in data:
                found.append({"protocol": item.get("name", "Unknown"), "source": "debank"})
    except:
        pass
    
    # Check common claim sites
    sites = [
        ("EigenLayer", "https://claims.eigenlayer.org"),
        ("Ethena", "https://claim.ethena.fi"),
        ("LayerZero", "https://claim.layerzero.network"),
        ("zkSync", "https://claim.zksync.io"),
        ("Starknet", "https://provisions.starknet.io"),
        ("Wormhole", "https://claim.wormhole.com"),
    ]
    
    for name, url in sites:
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            if r.status_code == 200:
                found.append({"protocol": name, "website": url, "source": "web"})
        except:
            pass
    
    if found:
        print(f"✅ **{len(found)} potential claims!**\n")
        for i, f in enumerate(found, 1):
            print(f"  {i}. **{f['protocol']}**")
            if f.get('website'):
                print(f"     {f['website']}")
            print()
    else:
        print("❌ No claimable airdrops found right now.")
    
    print("💡 Check manually: https://debank.com/" + EVM_WALLET)


# ─── Security: Token Approvals ─────────────────────────────────────────────

# ERC-20 Approval event signature
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"

# Known risky/spender addresses
KNOWN_SPENDERS = {
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch Router",
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Exchange",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3 Router02",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0x11111112542d85b3ef69ae05771c2dccff4faa26": "1inch V4",
    "0x111111125421ca6dc452d289314280a0f8842a65": "1inch V5",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap Universal Router",
    "0x000000000022d473030f116ddee9f6b43ac78ba3": "Seaport (OpenSea)",
}

MAX_UINT256 = 2**256 - 1


def cmd_approvals(chain_key: str = "eth", revoke_target: str = None):
    """Check token approvals for our wallet."""
    config = CHAINS.get(chain_key)
    if not config:
        print(f"❌ Unknown chain: {chain_key}")
        return
    
    w3 = get_web3(chain_key)
    if not w3.is_connected():
        print(f"❌ Cannot connect to {config['name']}")
        return
    
    addr = Web3.to_checksum_address(EVM_WALLET)
    print(f"🕵️ **Token Approvals — {config['name']}**\n")
    print(f"📍 Wallet: `{addr}`\n")
    
    # Get approval events from the last 10000 blocks
    try:
        latest = w3.eth.block_number
        from_block = max(0, latest - 5000)
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'topics': [
                APPROVAL_TOPIC,
                '0x' + addr[2:].lower().zfill(64),  # owner
            ],
        })
        
        if not logs:
            print("✅ No token approvals found!")
            return
        
        # Parse approvals - get unique spender+token combos
        approvals = {}
        for log in logs:
            spender = '0x' + log['topics'][2].hex()[-40:]
            token = log['address']
            data = log['data'].hex()
            
            if len(data) >= 66:
                amount = int(data[:66], 16)
            else:
                amount = int(data, 16) if data else 0
            
            key = f"{token.lower()}_{spender.lower()}"
            approvals[key] = {
                "token": token,
                "spender": spender,
                "amount": amount,
                "block": log['blockNumber'],
            }
        
        # Filter active (non-zero) approvals
        active = {k: v for k, v in approvals.items() if v["amount"] > 0}
        
        if not active:
            print("✅ No active token approvals!")
            return
        
        print(f"⚠️ **{len(active)} active approvals found!**\n")
        
        risky = []
        safe = []
        
        for key, app in active.items():
            spender_lower = app["spender"].lower()
            name = KNOWN_SPENDERS.get(spender_lower, "Unknown")
            is_unlimited = app["amount"] >= MAX_UINT256 // 2
            
            entry = {**app, "name": name, "is_unlimited": is_unlimited}
            
            if name == "Unknown" or is_unlimited:
                risky.append(entry)
            else:
                safe.append(entry)
        
        if risky:
            print("🔴 **Risky / Unlimited Approvals:**")
            for r in risky:
                limit = "UNLIMITED ♾️" if r["is_unlimited"] else f"{r['amount']}"
                print(f"  ⚠️ Token: {r['token'][:10]}...")
                print(f"     Spender: {r['name']} ({r['spender'][:10]}...)")
                print(f"     Amount: {limit}")
                print()
        
        if safe:
            print("🟢 **Known Spenders (Limited):**")
            for s in safe:
                print(f"  ✅ {s['name']} — Token: {s['token'][:10]}...")
        
        # Revoke functionality
        if revoke_target:
            print(f"\n⏳ Revoking approval for {revoke_target[:10]}...")
            revoke_approval(chain_key, revoke_target)
        elif risky:
            print(f"\n💡 **To revoke a risky approval:**")
            print(f"   python3 automation.py revoke --chain {chain_key} --token <TOKEN_ADDR> --spender <SPENDER_ADDR>")
            print(f"   Or use https://revoke.cash")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def revoke_approval(chain_key: str, token_addr: str, spender_addr: str = None):
    """Revoke token approval by setting to 0."""
    config = CHAINS[chain_key]
    w3 = get_web3(chain_key)
    pk, from_addr = decrypt_pk()
    from_addr = Web3.to_checksum_address(from_addr)
    
    # ERC-20 approve(address,uint256)
    APPROVE_ABI = json.loads('[{"name":"approve","type":"function","inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"outputs":[{"name":"","type":"bool"}]}]')
    
    token = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=APPROVE_ABI)
    spender = Web3.to_checksum_address(spender_addr) if spender_addr else None
    
    if not spender:
        print("❌ Need --spender address")
        return
    
    nonce = w3.eth.get_transaction_count(from_addr)
    gas_price = w3.eth.gas_price
    
    tx = token.functions.approve(spender, 0).build_transaction({
        'from': from_addr,
        'gas': 60000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': config['chain_id'],
    })
    
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    if receipt.status == 1:
        print(f"✅ Approval revoked! TX: {tx_hash.hex()}")
    else:
        print(f"❌ Revoke failed! TX: {tx_hash.hex()}")


# ─── Security: Scam Token Detector ────────────────────────────────────────

# Known scam token patterns
SCAM_PATTERNS = [
    "airdrop", "reward", "bonus", "claim", "visit", "free",
    "connect", "verify", "validate", "migration", "upgrade",
    "www.", "http", ".com", ".io", ".xyz",
]


def cmd_scam_check(chain_key: str = "eth"):
    """Check wallet for scam/spam tokens."""
    config = CHAINS.get(chain_key)
    if not config:
        print(f"❌ Unknown chain: {chain_key}")
        return
    
    w3 = get_web3(chain_key)
    if not w3.is_connected():
        print(f"❌ Cannot connect to {config['name']}")
        return
    
    addr = Web3.to_checksum_address(EVM_WALLET)
    print(f"🚨 **Scam Token Check — {config['name']}**\n")
    print(f"📍 Wallet: `{addr}`\n")
    
    # Get ERC-20 Transfer events TO our wallet
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    try:
        latest = w3.eth.block_number
        from_block = max(0, latest - 5000)
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'topics': [
                TRANSFER_TOPIC,
                None,  # from (any)
                '0x' + addr[2:].lower().zfill(64),  # to = our wallet
            ],
        })
        
        if not logs:
            print("✅ No incoming token transfers found.")
            return
        
        # Get unique tokens
        tokens = set()
        for log in logs:
            tokens.add(log['address'])
        
        print(f"📊 Found {len(tokens)} tokens received\n")
        
        # Check each token for scam patterns
        ERC20_ABI = json.loads('''[
            {"name":"name","type":"function","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"string"}]},
            {"name":"symbol","type":"function","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"string"}]},
            {"name":"decimals","type":"function","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint8"}]},
            {"name":"balanceOf","type":"function","stateMutability":"view","inputs":[{"name":"account","type":"address"}],"outputs":[{"name":"","type":"uint256"}]}
        ]''')
        
        scam_tokens = []
        legit_tokens = []
        
        for token_addr in tokens:
            try:
                token = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=ERC20_ABI)
                name = token.functions.name().call()
                symbol = token.functions.symbol().call()
                decimals = token.functions.decimals().call()
                balance = token.functions.balanceOf(addr).call()
                
                if balance == 0:
                    continue
                
                # Check scam patterns
                is_scam = False
                reasons = []
                
                name_lower = name.lower()
                symbol_lower = symbol.lower()
                
                for pattern in SCAM_PATTERNS:
                    if pattern in name_lower or pattern in symbol_lower:
                        is_scam = True
                        reasons.append(f"contains '{pattern}'")
                
                # Check if name is super long (common scam)
                if len(name) > 30:
                    is_scam = True
                    reasons.append("name too long")
                
                # Check if symbol is super long
                if len(symbol) > 10:
                    is_scam = True
                    reasons.append("symbol too long")
                
                human_balance = balance / (10 ** decimals)
                
                entry = {
                    "address": token_addr,
                    "name": name,
                    "symbol": symbol,
                    "balance": human_balance,
                    "decimals": decimals,
                    "reasons": reasons,
                }
                
                if is_scam:
                    scam_tokens.append(entry)
                else:
                    legit_tokens.append(entry)
            
            except:
                pass  # Can't parse = likely not a real token
        
        # Display results
        if scam_tokens:
            print(f"🔴 **{len(scam_tokens)} SCAM/SUSPICIOUS tokens:**\n")
            for t in scam_tokens:
                print(f"  🚨 {t['symbol']} ({t['name'][:25]})")
                print(f"     Balance: {t['balance']:,.2f}")
                print(f"     Reason: {', '.join(t['reasons'])}")
                print(f"     Contract: {t['address'][:10]}...")
                print()
            print("⚠️ **DO NOT interact with these tokens!**")
            print("   • Don't visit any websites in the token name")
            print("   • Don't approve or swap them")
            print("   • They'll stay in your wallet but are harmless if ignored")
            print()
        
        if legit_tokens:
            print(f"🟢 **{len(legit_tokens)} legitimate tokens:**\n")
            for t in legit_tokens:
                print(f"  ✅ {t['symbol']} — {t['balance']:,.4f}")
                print(f"     {t['name']}")
        
        if not scam_tokens and not legit_tokens:
            print("✅ No suspicious tokens found!")
    
    except Exception as e:
        print(f"❌ Error: {e}")


# ─── Bridge Optimizer ───────────────────────────────────────────────────────

LI_FI_API = "https://li.quest/v1"


def cmd_bridge(from_chain: str, to_chain: str, amount: float = None, token: str = "ETH"):
    """Find cheapest bridge route and optionally execute."""
    # Map chain names to Li.Fi chain IDs
    CHAIN_IDS = {
        "eth": 1, "ethereum": 1,
        "base": 8453,
        "arb": 42161, "arbitrum": 42161,
        "op": 10, "optimism": 10,
        "polygon": 137,
        "zksync": 324,
        "linea": 59144,
        "scroll": 534352,
        "blast": 81457,
    }
    
    TOKEN_ADDR = {
        "ETH": "0x0000000000000000000000000000000000000000",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    }
    
    from_id = CHAIN_IDS.get(from_chain.lower())
    to_id = CHAIN_IDS.get(to_chain.lower())
    
    if not from_id or not to_id:
        print(f"❌ Unknown chain. Available: {', '.join(CHAIN_IDS.keys())}")
        return
    
    if from_id == to_id:
        print("❌ Source and destination chain must be different!")
        return
    
    # Get wallet balance if no amount specified
    w3 = get_web3(from_chain.lower().split("-")[0])
    addr = Web3.to_checksum_address(EVM_WALLET)
    
    if amount is None:
        bal = w3.eth.get_balance(addr)
        amount = float(w3.from_wei(bal, 'ether')) * 0.95  # use 95%
        if amount <= 0:
            print("❌ No balance on source chain!")
            return
    
    amount_wei = w3.to_wei(amount, 'ether')
    token_addr = TOKEN_ADDR.get(token.upper(), TOKEN_ADDR["ETH"])
    
    print(f"🌉 **Bridge Optimizer**\n")
    print(f"   From: {from_chain.upper()} → {to_chain.upper()}")
    print(f"   Amount: {amount:.8f} {token}")
    print(f"   Wallet: `{addr}`\n")
    
    # Get routes from Li.Fi
    try:
        print("⏳ Finding best routes...\n")
        
        r = httpx.get(f"{LI_FI_API}/quote", params={
            "fromChain": from_id,
            "toChain": to_id,
            "fromToken": token_addr,
            "toToken": token_addr,
            "fromAmount": str(int(amount_wei)),
            "fromAddress": addr,
            "toAddress": addr,
        }, timeout=30)
        
        if r.status_code != 200:
            print(f"❌ Li.Fi error: {r.status_code}")
            print(r.text[:200])
            return
        
        quote = r.json()
        
        tool = quote.get("tool", "Unknown")
        estimate = quote.get("estimate", {})
        
        from_amount = int(estimate.get("fromAmount", 0))
        to_amount = int(estimate.get("toAmount", 0))
        gas_costs = estimate.get("gasCosts", [])
        fee_total = estimate.get("feeCosts", [])
        
        from_human = from_amount / 1e18
        to_human = to_amount / 1e18
        
        # Calculate gas cost in USD
        gas_usd = 0
        for gc in gas_costs:
            gas_usd += float(gc.get("amountUSD", 0))
        
        fee_usd = 0
        for fc in fee_total:
            fee_usd += float(fc.get("amountUSD", 0))
        
        diff = from_human - to_human
        diff_pct = (diff / from_human * 100) if from_human > 0 else 0
        
        # Get explorer link
        to_chain_config = CHAINS.get(to_chain.lower().split("-")[0], {})
        explorer = to_chain_config.get("explorer", "")
        
        print(f"✅ **Best Route: {tool}**\n")
        print(f"   📤 Send:     {from_human:.8f} {token} ({from_chain.upper()})")
        print(f"   📥 Receive:  {to_human:.8f} {token} ({to_chain.upper()})")
        print(f"   📉 Fee:      {diff:.8f} {token} ({diff_pct:.2f}%)")
        print(f"   ⛽ Gas:      ~${gas_usd:.4f}")
        print(f"   💱 Bridge:   ~${fee_usd:.4f}")
        print(f"   ⏱️ Est. time: ~{estimate.get('executionDuration', 'unknown')}s")
        
        # Try to get more routes for comparison
        try:
            r2 = httpx.get(f"{LI_FI_API}/routes", params={
                "fromChain": from_id,
                "toChain": to_id,
                "fromToken": token_addr,
                "toToken": token_addr,
                "fromAmount": str(int(amount_wei)),
                "fromAddress": addr,
                "toAddress": addr,
            }, timeout=30)
            
            if r2.status_code == 200:
                routes = r2.json().get("routes", [])
                if len(routes) > 1:
                    print(f"\n📊 **Alternative Routes:**\n")
                    for i, route in enumerate(routes[1:5], 2):
                        r_tool = route.get("tool", "?")
                        r_to = int(route.get("toAmount", 0)) / 1e18
                        r_diff = from_human - r_to
                        r_pct = (r_diff / from_human * 100) if from_human > 0 else 0
                        r_gas = sum(float(gc.get("amountUSD", 0)) for gc in route.get("gasCosts", []))
                        print(f"   {i}. {r_tool:15} | {r_to:.8f} {token} | fee: {r_pct:.2f}% | gas: ${r_gas:.4f}")
        except:
            pass
        
        # Offer to execute
        tx = quote.get("transactionRequest", {})
        if tx:
            print(f"\n💡 **To execute this bridge:**")
            print(f"   python3 automation.py bridge-execute --from {from_chain} --to {to_chain} --amount {amount}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def cmd_bridge_execute(from_chain: str, to_chain: str, amount: float):
    """Execute a bridge transaction."""
    CHAIN_IDS = {
        "eth": 1, "base": 8453, "arb": 42161, "op": 10,
        "polygon": 137, "zksync": 324, "linea": 59144, "scroll": 534352, "blast": 81457,
    }
    
    from_id = CHAIN_IDS.get(from_chain.lower())
    to_id = CHAIN_IDS.get(to_chain.lower())
    
    if not from_id or not to_id:
        print(f"❌ Unknown chain")
        return
    
    config = CHAINS.get(from_chain.lower().split("-")[0])
    if not config:
        print(f"❌ Chain not in config")
        return
    
    w3 = get_web3(from_chain.lower().split("-")[0])
    if not w3.is_connected():
        print(f"❌ Cannot connect to {config['name']}")
        return
    
    pk, addr = decrypt_pk()
    addr = Web3.to_checksum_address(addr)
    amount_wei = w3.to_wei(amount, 'ether')
    
    # Get quote
    print(f"⏳ Getting quote for {amount} {config['native']} bridge...")
    
    r = httpx.get(f"{LI_FI_API}/quote", params={
        "fromChain": from_id,
        "toChain": to_id,
        "fromToken": "0x0000000000000000000000000000000000000000",
        "toToken": "0x0000000000000000000000000000000000000000",
        "fromAmount": str(int(amount_wei)),
        "fromAddress": addr,
        "toAddress": addr,
    }, timeout=30)
    
    if r.status_code != 200:
        print(f"❌ Quote failed: {r.status_code}")
        return
    
    quote = r.json()
    tx_req = quote.get("transactionRequest", {})
    
    if not tx_req:
        print("❌ No transaction request in quote")
        return
    
    to_amount = int(quote.get("estimate", {}).get("toAmount", 0)) / 1e18
    tool = quote.get("tool", "Unknown")
    
    print(f"\n📋 **Bridge via {tool}**")
    print(f"   Send: {amount:.8f} ({config['name']})")
    print(f"   Receive: ~{to_amount:.8f} ({to_chain.upper()})")
    
    # Build and send
    nonce = w3.eth.get_transaction_count(addr)
    gas_price = w3.eth.gas_price
    
    tx = {
        'from': addr,
        'to': Web3.to_checksum_address(tx_req['to']),
        'value': int(tx_req['value'], 16) if isinstance(tx_req['value'], str) else int(tx_req['value']),
        'data': bytes.fromhex(tx_req['data'][2:] if tx_req['data'].startswith('0x') else tx_req['data']),
        'gas': int(tx_req['gasLimit'], 16) if isinstance(tx_req['gasLimit'], str) else int(tx_req['gasLimit']),
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': config['chain_id'],
    }
    
    try:
        gas_est = w3.eth.estimate_gas(tx)
        tx['gas'] = int(gas_est * 1.2)
    except:
        pass
    
    print(f"\n⏳ Signing and sending...")
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"✅ TX sent!")
    print(f"   Hash: {tx_hash.hex()}")
    print(f"   Explorer: {config.get('explorer', '')}/tx/{tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt.status == 1:
        print(f"\n✅ Bridge successful!")
        print(f"   Gas used: {receipt.gasUsed}")
        print(f"   ⏳ Funds arriving on {to_chain.upper()} in ~1-5 min")
    else:
        print(f"\n❌ Bridge failed!")


# ─── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Roxy Automation")
    sub = parser.add_subparsers(dest="command")
    
    # Portfolio
    sub.add_parser("portfolio", help="Show portfolio")
    
    # Gas
    sub.add_parser("gas", help="Show gas prices")
    
    # Airdrop
    sub.add_parser("airdrop", help="Check airdrop eligibility")
    
    # Approvals
    appr_p = sub.add_parser("approvals", help="Check token approvals")
    appr_p.add_argument("--chain", default="eth", help="Chain key")
    
    # Revoke
    rev_p = sub.add_parser("revoke", help="Revoke token approval")
    rev_p.add_argument("--chain", required=True)
    rev_p.add_argument("--token", required=True, help="Token contract address")
    rev_p.add_argument("--spender", required=True, help="Spender address to revoke")
    
    # Scam check
    scam_p = sub.add_parser("scam", help="Check for scam tokens")
    scam_p.add_argument("--chain", default="eth", help="Chain key")
    
    # Bridge optimizer
    bridge_p = sub.add_parser("bridge", help="Find best bridge route")
    bridge_p.add_argument("--from", dest="from_chain", required=True, help="Source chain")
    bridge_p.add_argument("--to", dest="to_chain", required=True, help="Destination chain")
    bridge_p.add_argument("--amount", type=float, help="Amount (default: 95% balance)")
    bridge_p.add_argument("--token", default="ETH", help="Token (default: ETH)")
    
    # Bridge execute
    bexec_p = sub.add_parser("bridge-execute", help="Execute bridge transaction")
    bexec_p.add_argument("--from", dest="from_chain", required=True)
    bexec_p.add_argument("--to", dest="to_chain", required=True)
    bexec_p.add_argument("--amount", type=float, required=True)
    
    # Send
    send_p = sub.add_parser("send", help="Batch send")
    send_p.add_argument("--chain", required=True)
    send_p.add_argument("--to", help="Comma-separated addresses")
    send_p.add_argument("--amount", type=float, help="Amount per recipient")
    send_p.add_argument("--file", help="CSV file: address,amount")
    send_p.add_argument("--testnet", action="store_true")
    send_p.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.command == "portfolio":
        cmd_portfolio()
    elif args.command == "gas":
        cmd_gas()
    elif args.command == "airdrop":
        cmd_airdrop()
    elif args.command == "approvals":
        cmd_approvals(args.chain)
    elif args.command == "revoke":
        revoke_approval(args.chain, args.token, args.spender)
    elif args.command == "scam":
        cmd_scam_check(args.chain)
    elif args.command == "bridge":
        cmd_bridge(args.from_chain, args.to_chain, args.amount, args.token)
    elif args.command == "bridge-execute":
        confirm = input(f"⚠️ Execute bridge {args.amount} ETH from {args.from_chain} to {args.to_chain}? (y/n): ")
        if confirm.lower() == "y":
            cmd_bridge_execute(args.from_chain, args.to_chain, args.amount)
        else:
            print("❌ Cancelled")
    elif args.command == "send":
        recipients = []
        if args.file:
            with open(args.file) as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        recipients.append((row[0].strip(), float(row[1].strip())))
        elif args.to and args.amount:
            recipients = [(a.strip(), args.amount) for a in args.to.split(",")]
        else:
            print("Use --file CSV or --to ADDRS --amount AMT")
            sys.exit(1)
        cmd_send(args.chain, recipients, dry_run=args.dry_run, testnet=args.testnet)
    else:
        parser.print_help()
