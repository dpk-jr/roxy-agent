#!/usr/bin/env python3
"""
Roxy — Autonomous Crypto Agent
Mint, send, and trade across multiple blockchains via natural language.
"""

import os
import json
import httpx
from pathlib import Path
from web3 import Web3
from eth_account import Account

# ─── Chain Config ──────────────────────────────────────────────────────────

CHAINS = {
    "ethereum": {"rpc": "https://eth-mainnet.g.alchemy.com/v2/{key}", "chain_id": 1, "native": "ETH", "explorer": "https://etherscan.io"},
    "base": {"rpc": "https://mainnet.base.org", "chain_id": 8453, "native": "ETH", "explorer": "https://basescan.org"},
    "arbitrum": {"rpc": "https://arb1.arbitrum.io/rpc", "chain_id": 42161, "native": "ETH", "explorer": "https://arbiscan.io"},
    "optimism": {"rpc": "https://mainnet.optimism.io", "chain_id": 10, "native": "ETH", "explorer": "https://optimistic.etherscan.io"},
    "polygon": {"rpc": "https://polygon-bor-rpc.publicnode.com", "chain_id": 137, "native": "POL", "explorer": "https://polygonscan.com"},
    "zksync": {"rpc": "https://mainnet.era.zksync.io", "chain_id": 324, "native": "ETH", "explorer": "https://explorer.zksync.io"},
    "linea": {"rpc": "https://rpc.linea.build", "chain_id": 59144, "native": "ETH", "explorer": "https://lineascan.build"},
    "scroll": {"rpc": "https://rpc.scroll.io", "chain_id": 534352, "native": "ETH", "explorer": "https://scrollscan.com"},
    "blast": {"rpc": "https://rpc.blast.io", "chain_id": 81457, "native": "ETH", "explorer": "https://blastscan.io"},
}


class RoxyAgent:
    """Autonomous crypto agent for mint, send, and trade operations."""

    def __init__(self, private_key: str):
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address

    def get_web3(self, chain: str) -> Web3:
        config = CHAINS.get(chain)
        if not config:
            raise ValueError(f"Unknown chain: {chain}")
        rpc = config["rpc"].format(key=os.getenv("ALCHEMY_API_KEY", ""))
        return Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))

    # ─── Send ──────────────────────────────────────────────────────────────

    def send(self, chain: str, to: str, amount: float) -> dict:
        """Send native token to an address."""
        w3 = self.get_web3(chain)
        config = CHAINS[chain]

        tx = {
            'from': self.address,
            'to': Web3.to_checksum_address(to),
            'value': w3.to_wei(amount, 'ether'),
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(self.address),
            'chainId': config['chain_id'],
        }

        signed = w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "explorer": f"{config['explorer']}/tx/{tx_hash.hex()}",
            "gas_used": receipt.gasUsed,
        }

    # ─── Swap ──────────────────────────────────────────────────────────────

    def get_swap_quote(self, chain: str, token_in: str, token_out: str, amount: float) -> dict:
        """Get swap quote via 1inch API."""
        config = CHAINS[chain]
        w3 = self.get_web3(chain)
        amount_wei = w3.to_wei(amount, 'ether')

        try:
            r = httpx.get(f"https://api.1inch.dev/swap/v6.0/{config['chain_id']}/quote", params={
                "src": token_in,
                "dst": token_out,
                "amount": str(int(amount_wei)),
            }, headers={"Authorization": f"Bearer {os.getenv('ONEINCH_API_KEY', '')}"}, timeout=15)

            if r.status_code == 200:
                data = r.json()
                return {
                    "to_amount": int(data.get("dstAmount", 0)),
                    "gas": int(data.get("gas", 0)),
                    "protocols": data.get("protocols", []),
                }
        except:
            pass

        # Fallback to Li.Fi
        return self._lifi_quote(chain, chain, token_in, token_out, int(amount_wei))

    def swap(self, chain: str, token_in: str, token_out: str, amount: float) -> dict:
        """Execute a token swap."""
        w3 = self.get_web3(chain)
        config = CHAINS[chain]

        quote = self.get_swap_quote(chain, token_in, token_out, amount)

        # Build swap transaction via 1inch
        amount_wei = w3.to_wei(amount, 'ether')
        r = httpx.get(f"https://api.1inch.dev/swap/v6.0/{config['chain_id']}/swap", params={
            "src": token_in,
            "dst": token_out,
            "amount": str(int(amount_wei)),
            "from": self.address,
            "slippage": 1,
        }, headers={"Authorization": f"Bearer {os.getenv('ONEINCH_API_KEY', '')}"}, timeout=15)

        if r.status_code != 200:
            return {"status": "error", "message": f"Swap failed: {r.status_code}"}

        data = r.json()
        tx_data = data.get("tx", {})

        tx = {
            'from': self.address,
            'to': Web3.to_checksum_address(tx_data.get("to")),
            'data': tx_data.get("data"),
            'value': int(tx_data.get("value", 0)),
            'gas': int(tx_data.get("gas", 300000)),
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(self.address),
            'chainId': config['chain_id'],
        }

        signed = w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "explorer": f"{config['explorer']}/tx/{tx_hash.hex()}",
        }

    # ─── Bridge ────────────────────────────────────────────────────────────

    def _lifi_quote(self, from_chain: str, to_chain: str, token_in: str, token_out: str, amount_wei: int) -> dict:
        """Get quote from Li.Fi (Jumper)."""
        CHAIN_IDS = {"ethereum": 1, "base": 8453, "arbitrum": 42161, "optimism": 10,
                     "polygon": 137, "zksync": 324, "linea": 59144, "scroll": 534352, "blast": 81457}

        r = httpx.get("https://li.quest/v1/quote", params={
            "fromChain": CHAIN_IDS.get(from_chain, 1),
            "toChain": CHAIN_IDS.get(to_chain, 1),
            "fromToken": token_in,
            "toToken": token_out,
            "fromAmount": str(amount_wei),
            "fromAddress": self.address,
            "toAddress": self.address,
        }, timeout=30)

        if r.status_code == 200:
            data = r.json()
            return {
                "to_amount": int(data.get("estimate", {}).get("toAmount", 0)),
                "gas": int(data.get("estimate", {}).get("gasCosts", [{}])[0].get("estimate", 0)),
                "tool": data.get("tool", "unknown"),
                "tx_request": data.get("transactionRequest", {}),
            }
        return {"error": r.text[:200]}

    def bridge(self, from_chain: str, to_chain: str, amount: float) -> dict:
        """Bridge native token between chains via Li.Fi."""
        w3 = self.get_web3(from_chain)
        config = CHAINS[from_chain]
        amount_wei = w3.to_wei(amount, 'ether')

        quote = self._lifi_quote(from_chain, to_chain,
                                 "0x0000000000000000000000000000000000000000",
                                 "0x0000000000000000000000000000000000000000",
                                 amount_wei)

        if "error" in quote:
            return {"status": "error", "message": quote["error"]}

        tx_req = quote.get("tx_request", {})
        if not tx_req:
            return {"status": "error", "message": "No transaction request"}

        tx = {
            'from': self.address,
            'to': Web3.to_checksum_address(tx_req['to']),
            'value': int(tx_req['value'], 16) if isinstance(tx_req['value'], str) else int(tx_req['value']),
            'data': bytes.fromhex(tx_req['data'][2:]) if tx_req['data'].startswith('0x') else bytes.fromhex(tx_req['data']),
            'gas': int(tx_req.get('gasLimit', 300000)),
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(self.address),
            'chainId': config['chain_id'],
        }

        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)
        except:
            pass

        signed = w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "explorer": f"{config['explorer']}/tx/{tx_hash.hex()}",
            "tool": quote.get("tool", "unknown"),
        }

    # ─── Mint / Claim ──────────────────────────────────────────────────────

    def call_contract(self, chain: str, contract: str, abi: list, function: str, args: list = None, value: float = 0) -> dict:
        """Call any smart contract function."""
        w3 = self.get_web3(chain)
        config = CHAINS[chain]

        contract_obj = w3.eth.contract(
            address=Web3.to_checksum_address(contract),
            abi=abi
        )

        func = getattr(contract_obj.functions, function)
        func_call = func(*(args or []))

        tx = func_call.build_transaction({
            'from': self.address,
            'value': w3.to_wei(value, 'ether') if value else 0,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(self.address),
            'chainId': config['chain_id'],
        })

        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)
        except:
            pass

        signed = w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "explorer": f"{config['explorer']}/tx/{tx_hash.hex()}",
        }

    # ─── Portfolio ─────────────────────────────────────────────────────────

    def portfolio(self) -> dict:
        """Get balance across all chains."""
        balances = {}
        total_usd = 0

        eth_price = self._get_price("ethereum")

        for chain_name, config in CHAINS.items():
            try:
                w3 = self.get_web3(chain_name)
                bal = float(w3.from_wei(w3.eth.get_balance(self.address), 'ether'))
                usd = bal * eth_price
                total_usd += usd
                balances[chain_name] = {"balance": bal, "usd": usd, "native": config["native"]}
            except:
                balances[chain_name] = {"balance": 0, "usd": 0, "native": config["native"]}

        return {"address": self.address, "chains": balances, "total_usd": total_usd}

    def _get_price(self, coin: str) -> float:
        try:
            r = httpx.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd", timeout=10)
            return r.json().get(coin, {}).get("usd", 0)
        except:
            return 0


if __name__ == "__main__":
    print("Roxy Agent — Autonomous Crypto Assistant")
    print("Import and use: agent = RoxyAgent(private_key)")
