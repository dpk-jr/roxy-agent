# 🤖 Roxy — Autonomous Crypto Agent

An autonomous AI agent that helps you **mint, send, and trade** crypto across multiple blockchains through simple natural language commands.

## What is Roxy?

Roxy is an AI-powered crypto assistant that lives in your chat app. Instead of navigating complex DeFi interfaces, connecting wallets, and signing transactions manually — you just tell Roxy what you want to do.

> "send 0.01 ETH to 0xABC on Base"
> "swap all my OP ETH to USDC"
> "bridge 0.1 ETH from Arbitrum to Ethereum"

Roxy understands your intent, finds the best route, estimates costs, asks for confirmation, and executes — all in one conversation.

## Features

- **Mint** — Interact with smart contracts, claim airdrops, mint NFTs
- **Send** — Transfer native tokens and ERC-20s across 9+ chains
- **Trade** — Swap tokens via DEX aggregation with optimal routing
- **Bridge** — Cross-chain transfers via Li.Fi (Jumper) aggregation
- **Monitor** — Real-time wallet tracking, gas alerts, token notifications
- **Security** — Scam token detection, approval management, auto-sweep protection

## Supported Chains

Ethereum • Base • Arbitrum • Optimism • Polygon • zkSync Era • Linea • Scroll • Blast • Solana

## How It Works

```
User: "swap 0.1 ETH to USDC on Base"

Roxy:
  1. Parses intent (swap, amount, token pair, chain)
  2. Fetches best route via DEX aggregator
  3. Estimates gas and slippage
  4. Shows confirmation:
     📋 Swap 0.1 ETH → ~225 USDC
     ⛽ Gas: $0.003
     Proceed? (y/n)
  5. User confirms → Roxy executes
  6. Returns tx hash + explorer link
```

## Architecture

```
┌──────────────────────────────┐
│      Chat Interface          │
│   (Telegram / Discord)       │
├──────────────────────────────┤
│      AI Agent Core           │
│   Intent parsing + Planning  │
├──────┬───────┬───────┬───────┤
│ Send │ Swap  │ Bridge│ Mint  │
│      │       │       │       │
├──────┴───────┴───────┴───────┤
│    Blockchain Layer           │
│  web3.py + solana.py         │
│  Direct contract execution   │
├──────────────────────────────┤
│    Multi-Chain RPCs          │
│  9 EVM chains + Solana       │
└──────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/dpk-jr/roxy-agent.git
cd roxy-agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python agent.py
```

## Security

- Private keys encrypted with Fernet + PBKDF2-SHA256 (480k iterations)
- All transactions require explicit y/n confirmation
- No plaintext credentials stored anywhere
- Auto-sweep protection for compromised wallets

## Tools & Scripts

Roxy comes with a comprehensive toolkit for crypto automation:

📁 **[tools/](./tools/)** — Core automation scripts

- **wallet_rescue.py** — Multi-chain wallet rescue and sweep operations
- **automation.py** — Core toolkit (portfolio, gas, bridge, scam detection)
- **guardian.py** — Autonomous wallet security monitoring
- **token_watcher.py** — 24/7 token deposit monitoring
- **portfolio.py** — Real-time portfolio tracking
- **batch_send.py** — Batch token transfers
- **airdrop_claimer.py** — Automated airdrop claiming
- **metamask_inject.py** — Browser automation with MetaMask injection

See [tools/README.md](./tools/README.md) for detailed usage.

## Building Your Own Agent

Want to build your own autonomous crypto agent? Check out the [Building Roxy's Soul](./docs/BUILDING_SOUL.md) guide — it covers:

- System prompt architecture
- Personality & tone design
- Skills system (procedural memory)
- Memory architecture (persistent facts)
- Security patterns (encryption, confirmation, auto-sweep)
- Multi-platform setup (Telegram, Discord)
- Best practices and common pitfalls

## License

MIT
