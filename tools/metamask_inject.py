#!/usr/bin/env python3
"""
MetaMask Injector — Fake window.ethereum for dApp interaction.
Lets us connect to dApps that require MetaMask without the real extension.
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

CRED_DIR = Path.home() / ".agent" / "credentials"
load_dotenv(CRED_DIR / "rescue-config.env")

# Load private key
with open(CRED_DIR / "roxy-evm-wallet.enc.json") as f:
    wallet = json.load(f)

WALLET_ADDR = wallet["address"]

master = os.getenv("ROXY_MASTER_PASSWORD", "")
salt = base64.b64decode(wallet["salt"])
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
key = base64.urlsafe_b64encode(kdf.derive(master.encode()))
PRIVATE_KEY = Fernet(key).decrypt(wallet["encrypted_private_key"].encode()).decode()

# Generate MetaMask injection script
INJECT_JS = f"""
// Fake MetaMask Provider
(function() {{
    if (window.ethereum) return;
    
    const WALLET_ADDRESS = "{WALLET_ADDR.lower()}";
    
    class FakeMetaMaskProvider {{
        constructor() {{
            this.isMetaMask = true;
            this.chainId = "0x1";
            this.networkVersion = "1";
            this.selectedAddress = WALLET_ADDRESS;
            this._listeners = {{}};
        }}
        
        on(event, callback) {{
            if (!this._listeners[event]) this._listeners[event] = [];
            this._listeners[event].push(callback);
        }}
        
        emit(event, ...args) {{
            (this._listeners[event] || []).forEach(cb => cb(...args));
        }}
        
        async request({{ method, params }}) {{
            console.log("[FakeMetaMask] request:", method, params);
            
            switch(method) {{
                case "eth_requestAccounts":
                case "eth_accounts":
                    return [WALLET_ADDRESS];
                    
                case "eth_chainId":
                    return this.chainId;
                    
                case "net_version":
                    return this.networkVersion;
                    
                case "eth_getBalance":
                    // Forward to real RPC
                    const rpcUrl = "https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', '')}";
                    const resp = await fetch(rpcUrl, {{
                        method: "POST",
                        headers: {{"Content-Type": "application/json"}},
                        body: JSON.stringify({{
                            jsonrpc: "2.0", id: 1, method: "eth_getBalance",
                            params: params
                        }})
                    }});
                    const data = await resp.json();
                    return data.result;
                    
                case "eth_sendTransaction":
                    // Transaction will be signed server-side
                    window.__pendingTx = params[0];
                    window.dispatchEvent(new CustomEvent("metamask-tx", {{ detail: params[0] }}));
                    return "0x" + "0".repeat(64); // Placeholder hash
                    
                case "personal_sign":
                case "eth_sign":
                    window.__pendingSign = {{ message: params[0], from: params[1] }};
                    window.dispatchEvent(new CustomEvent("metamask-sign", {{ detail: {{ message: params[0], from: params[1] }} }}));
                    return "0x" + "0".repeat(130); // Placeholder signature
                    
                case "wallet_switchEthereumChain":
                    this.chainId = params[0].chainId;
                    this.emit("chainChanged", this.chainId);
                    return null;
                    
                case "wallet_addEthereumChain":
                    return null;
                    
                case "eth_blockNumber":
                    return "0x1";
                    
                case "eth_estimateGas":
                    return "0x5208"; // 21000
                    
                case "eth_gasPrice":
                    return "0x3B9ACA00"; // 1 gwei
                    
                default:
                    console.warn("[FakeMetaMask] Unhandled:", method);
                    return null;
            }}
        }}
        
        isConnected() {{ return true; }}
    }}
    
    window.ethereum = new FakeMetaMaskProvider();
    console.log("[FakeMetaMask] Injected! Address:", WALLET_ADDRESS);
}})();
"""


def get_inject_js():
    """Get the JavaScript injection code."""
    return INJECT_JS


def inject_page(page):
    """Inject fake MetaMask into a Playwright page."""
    page.add_init_script(INJECT_JS)
    print(f"✅ MetaMask injected! Address: {WALLET_ADDR}")


if __name__ == "__main__":
    print("🦊 MetaMask Injection Script Ready!")
    print(f"   Address: {WALLET_ADDR}")
    print(f"   Inject via: page.add_init_script(INJECT_JS)")
    print(f"\n   Script length: {len(INJECT_JS)} bytes")
