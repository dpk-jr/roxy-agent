# 🛠️ Roxy Tools

This directory contains the core automation scripts that power Roxy's capabilities.

## Tools Overview

### 🔐 wallet_rescue.py
**Multi-chain wallet rescue and sweep operations**

- Sweep funds from compromised wallets to safe addresses
- Support for 9 EVM chains + Solana
- Batch rescue across multiple chains simultaneously
- Encrypted private key handling

```bash
# Rescue funds from compromised wallet
python wallet_rescue.py --chain ethereum --from 0xCOMPROMISED --to 0xSAFE

# Multi-chain rescue
python wallet_rescue.py --multi-chain --from 0xCOMPROMISED --to 0xSAFE
```

### ⚡ automation.py
**Core automation toolkit with 9 integrated tools**

- Portfolio tracking across all chains
- Gas monitoring and estimation
- Airdrop eligibility checking
- Batch token sending
- Token approval management
- Scam token detection
- Bridge route optimization
- Cross-chain bridge execution

```bash
# Check portfolio
python automation.py portfolio --address 0xYOUR_ADDRESS

# Find best bridge route
python automation.py bridge-optimize --from ethereum --to base --amount 0.1

# Execute bridge
python automation.py bridge-execute --from ethereum --to base --amount 0.1
```

### 🛡️ guardian.py
**Autonomous wallet security monitoring**

- Real-time nonce monitoring across 9 chains
- Automatic exploit detection
- Auto-sweep to rescue wallet on anomaly
- 24/7 background operation

```bash
# Start guardian monitoring
python guardian.py --wallet 0xYOUR_ADDRESS --chains all

# Check guardian status
python guardian.py --status
```

### 👁️ token_watcher.py
**24/7 token deposit monitoring**

- Monitor incoming tokens across all chains
- Instant Telegram notifications
- Track multiple wallets simultaneously
- Historical deposit logging

```bash
# Start watching for deposits
python token_watcher.py --wallets 0xWALLET1,0xWALLET2 --notify telegram

# View deposit history
python token_watcher.py --history --wallet 0xYOUR_ADDRESS
```

### 📊 portfolio.py
**Real-time portfolio tracking**

- Multi-chain balance aggregation
- Token price tracking
- Gas cost estimation
- Historical value tracking

```bash
# View full portfolio
python portfolio.py --address 0xYOUR_ADDRESS

# Track specific tokens
python portfolio.py --address 0xYOUR_ADDRESS --tokens ETH,USDC,ARB
```

### 📤 batch_send.py
**Batch token transfer operations**

- Send to multiple recipients in one transaction
- ERC-20 and native token support
- CSV file input for bulk transfers
- Gas optimization for batch operations

```bash
# Send to multiple addresses
python batch_send.py --token USDC --amount 10 --to 0xADDR1,0xADDR2,0xADDR3

# Batch send from CSV
python batch_send.py --token USDC --csv recipients.csv
```

### 🎯 airdrop_claimer.py
**Automated airdrop claiming**

- Check eligibility across multiple protocols
- Batch claim available airdrops
- Gas optimization for claim transactions
- Claim history tracking

```bash
# Check all available airdrops
python airdrop_claimer.py --check --address 0xYOUR_ADDRESS

# Claim all available
python airdrop_claimer.py --claim-all --address 0xYOUR_ADDRESS
```

### 🦊 metamask_inject.py
**Browser automation with MetaMask injection**

- Inject fake MetaMask provider for dApp interaction
- Enable wallet connection without real extension
- Support for Uniswap, 1inch, and other dApps
- Transaction signing via web3.py

```bash
# Start browser with MetaMask injection
python metamask_inject.py --dapp uniswap

# Connect wallet to dApp
python metamask_inject.py --dapp uniswap --wallet 0xYOUR_ADDRESS
```

## Security Notes

⚠️ **Important Security Practices:**

1. **Never store plaintext private keys** — Always use encrypted storage
2. **Use environment variables** for sensitive configuration
3. **Enable 2FA** on all related accounts
4. **Regularly rotate** API keys and access tokens
5. **Monitor logs** for suspicious activity

## Configuration

Create a `.env` file in the tools directory:

```bash
# RPC Endpoints
ETHEREUM_RPC=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BASE_RPC=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
ARBITRUM_RPC=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Wallet Configuration
RESCUE_WALLET=0xYOUR_RESCUE_WALLET
ENCRYPTION_PASSWORD=your_secure_password
```

## Dependencies

```bash
pip install web3 solana httpx cryptography python-dotenv
```

## Usage with Roxy

These tools are integrated into Roxy's natural language interface. Instead of running scripts directly, you can ask Roxy:

- "cek portfolio" → Runs portfolio.py
- "bridge 0.1 ETH dari base ke eth" → Runs automation.py bridge
- "ada token scam gak?" → Runs automation.py scam detection
- "monitor wallet 24/7" → Starts token_watcher.py
- "sweep semua dana ke rescue wallet" → Runs wallet_rescue.py

## License

MIT
