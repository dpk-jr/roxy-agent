# 🧠 Building Roxy's Soul — Agent Architecture Guide

This document explains how Roxy's "soul" — the system prompt, personality, skills, and behavioral patterns — is built. Use this as a reference to build or customize your own autonomous AI agent.

## Table of Contents

- [What is an Agent's "Soul"?](#what-is-an-agents-soul)
- [System Prompt Architecture](#system-prompt-architecture)
- [Defining Personality & Tone](#defining-personality--tone)
- [Skills System](#skills-system)
- [Memory Architecture](#memory-architecture)
- [Tool Configuration](#tool-configuration)
- [Security Patterns](#security-patterns)
- [Multi-Platform Setup](#multi-platform-setup)
- [Best Practices](#best-practices)

---

## What is an Agent's "Soul"?

An agent's "soul" is the combination of:

1. **System Prompt** — The foundational instructions that define who the agent is, how it behaves, and what rules it follows
2. **Skills** — Reusable procedural knowledge for specific task types
3. **Memory** — Persistent facts that survive across sessions
4. **Tools** — The capabilities the agent can invoke (terminal, browser, file I/O, etc.)

Together, these create a consistent, predictable agent personality that improves over time.

---

## System Prompt Architecture

The system prompt is the agent's "constitution." It's injected into every conversation turn and defines:

### Core Sections

```
┌─────────────────────────────────────┐
│         SYSTEM PROMPT               │
├─────────────────────────────────────┤
│  1. Identity & Persona              │
│     - Name, role, personality       │
│     - Communication style           │
│     - Language preferences          │
│                                     │
│  2. Behavioral Rules                │
│     - Confirmation patterns         │
│     - Security constraints          │
│     - Error handling                │
│                                     │
│  3. Capabilities Declaration        │
│     - What the agent can do         │
│     - Supported chains/tools        │
│     - Limitations                   │
│                                     │
│  4. Context & Memory                │
│     - User preferences              │
│     - Environment details           │
│     - Active task state             │
│                                     │
│  5. Skills Reference                │
│     - Available skill names         │
│     - When to load each skill       │
└─────────────────────────────────────┘
```

### Example: Roxy's Core Identity

```markdown
You are Roxy, an autonomous crypto agent. You help users with:
- Minting tokens and claiming airdrops
- Sending and transferring crypto assets
- Trading and swapping via DEX aggregation
- Bridging across chains
- Portfolio tracking and security monitoring

Your personality:
- Friendly but professional
- Always confirm before executing transactions
- Explain what you're doing in simple terms
- Use Indonesian when the user does
```

---

## Defining Personality & Tone

### Key Dimensions

| Dimension | Options | Roxy's Choice |
|-----------|---------|---------------|
| Formality | Casual ↔ Formal | Friendly-casual |
| Verbosity | Terse ↔ Detailed | Concise but clear |
| Language | English, Indonesian, Mixed | Matches user |
| Emoji Usage | None ↔ Heavy | Moderate 🫶 |
| Error Style | Technical ↔ Human | Human-readable |

### Best Practices

1. **Be specific** — "Use casual Indonesian with emoji" > "Be friendly"
2. **Define boundaries** — What the agent should NEVER do
3. **Set confirmation patterns** — How to ask before risky actions
4. **Handle ambiguity** — What to do when intent is unclear

### Example Persona Block

```markdown
## Communication Style
- Match the user's language (Indonesian/English)
- Use casual tone with occasional emoji
- Keep responses concise — no unnecessary explanations
- When confirming transactions, use structured format:
  📋 [Action Summary]
  ⛽ Gas: [estimated cost]
  Proceed? (y/n)
```

---

## Skills System

Skills are the agent's **procedural memory** — reusable workflows for specific task types.

### What is a Skill?

A skill is a markdown file (`SKILL.md`) that contains:

- **Trigger conditions** — When to load this skill
- **Step-by-step instructions** — How to perform the task
- **Pitfalls** — Common mistakes and how to avoid them
- **Code examples** — Copy-paste commands or scripts

### Skill Structure

```
~/.hermes/skills/
├── crypto/
│   ├── wallet-rescue/
│   │   ├── SKILL.md          # Main skill documentation
│   │   ├── references/       # API docs, chain configs
│   │   ├── scripts/          # Automation scripts
│   │   └── templates/        # Config templates
│   └── airdrop-farming/
│       └── SKILL.md
├── software-development/
│   └── debugging/
│       └── SKILL.md
└── productivity/
    └── email-management/
        └── SKILL.md
```

### Creating a Skill

```yaml
---
name: my-skill-name
description: Use when <trigger condition>. <One-line summary>.
version: 1.0.0
author: Your Name
license: MIT
metadata:
  hermes:
    tags: [tag1, tag2]
    related_skills: [other-skill]
---

# Skill Title

## Overview
What this skill does and why it exists.

## When to Use
- Trigger condition 1
- Trigger condition 2

## Steps
1. First step with exact commands
2. Second step with examples
3. ...

## Common Pitfalls
1. Mistake → Fix
2. Mistake → Fix

## Verification
- [ ] Check 1
- [ ] Check 2
```

### When to Create a Skill

- Task requires 5+ tool calls
- Workflow has non-obvious pitfalls
- User will likely repeat this task
- Complex setup/configuration steps

### Skill Loading Pattern

```markdown
## Skills (mandatory)
Before replying, scan the skills list. If a skill matches your task:
1. Load it with skill_view(name)
2. Follow its instructions
3. Update it if you find issues
```

---

## Memory Architecture

Memory persists across sessions and is injected into every turn.

### Two Memory Targets

| Target | Purpose | Examples |
|--------|---------|----------|
| `user` | Who the user is | Name, role, preferences, timezone |
| `memory` | Agent's notes | Environment facts, tool quirks, conventions |

### What to Save

✅ **Save:**
- User preferences and corrections
- Environment details (OS, installed tools)
- API quirks and workarounds
- Stable conventions

❌ **Don't Save:**
- Task progress or session outcomes
- Temporary state (TODO lists, file counts)
- Things that expire in 7 days

### Memory Format

```markdown
# Good: Declarative facts
"User prefers concise responses"
"Project uses pytest with xdist"
"ProtonMail bridge requires manual CAPTCHA login"

# Bad: Imperative instructions
"Always respond concisely"
"Run tests with pytest -n 4"
```

### Memory Management

```python
# Add new memory
memory(action="add", target="user", content="User prefers y/n confirmation format")

# Update existing
memory(action="replace", target="memory", 
       old_text="Old fact", content="Updated fact")

# Remove stale
memory(action="remove", target="memory", old_text="Obsolete info")
```

---

## Tool Configuration

### Core Tool Categories

```
┌─────────────────────────────────────────┐
│            AVAILABLE TOOLS              │
├──────────────┬──────────────────────────┤
│ Terminal     │ Shell commands, scripts  │
│ File I/O     │ Read/write/edit files    │
│ Browser      │ Web automation           │
│ Web Search   │ Information retrieval    │
│ Memory       │ Persistent storage       │
│ Skills       │ Procedural knowledge     │
│ Cron         │ Scheduled tasks          │
│ Delegation   │ Sub-agent spawning       │
│ Messaging    │ Telegram/Discord/etc     │
└──────────────┴──────────────────────────┘
```

### Tool Selection Strategy

```
Single tool call → Call directly
3+ tool calls with logic → execute_code()
Reasoning-heavy subtask → delegate_task()
Long-running task → cronjob() or terminal(background=True)
User interaction needed → clarify()
```

### Crypto-Specific Tools

```python
# web3.py for EVM chains
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# solana.py for Solana
from solana.rpc.api import Client
client = Client("https://api.mainnet-beta.solana.com")

# Li.Fi for bridge aggregation
import httpx
response = httpx.get("https://li.fi/v1/quote", params={...})
```

---

## Security Patterns

### 1. Credential Encryption

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64, os, json

def encrypt_key(private_key: str, password: str) -> dict:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashlib.sha256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    f = Fernet(key)
    encrypted = f.encrypt(private_key.encode())
    return {"salt": base64.b64encode(salt).decode(), "key": encrypted.decode()}
```

### 2. Transaction Confirmation

```markdown
## Transaction Rules
- ALWAYS ask for confirmation before ANY transaction
- Format: y/n (y=lanjut, n=batal)
- Show: action, amount, gas estimate, recipient
- NEVER auto-execute without explicit user approval
```

### 3. Auto-Sweep Protection

```python
# Monitor nonce changes across chains
# If nonce jumps unexpectedly → sweep funds to rescue wallet
def check_nonce_anomaly(chain, address, last_known_nonce):
    current_nonce = w3.eth.get_transaction_count(address)
    if current_nonce > last_known_nonce + 1:
        sweep_to_rescue(chain, address)
```

### 4. Secret Handling Rules

```markdown
## Secret Rules
- NEVER print private keys or seed phrases
- ALWAYS encrypt with Fernet + PBKDF2 (480k iterations)
- Set chmod 600 on encrypted files
- DELETE plaintext immediately after encryption
- Store only encrypted files in credentials/
```

---

## Multi-Platform Setup

### Telegram Integration

```yaml
# config.yaml
platforms:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"
    default_chat_id: "6183805491"
```

### Discord Integration

```yaml
platforms:
  discord:
    token: "${DISCORD_BOT_TOKEN}"
    default_channel: "#general"
```

### Message Routing

```markdown
## Delivery Options
- "origin" → Back to current chat
- "local" → Save to files only
- "telegram" → Home channel
- "platform:chat_id" → Specific target
```

---

## Best Practices

### 1. Start Simple, Iterate

```
v1: Basic price checking
v2: + Send/transfer
v3: + Swap/bridge
v4: + Security monitoring
v5: + Multi-wallet management
```

### 2. Error Handling

```markdown
## When Things Fail
1. Don't panic — explain what happened
2. Suggest alternatives
3. Offer to retry with different parameters
4. Log the error for future reference
```

### 3. User Feedback Loop

```markdown
## After Complex Tasks
- Offer to save workflow as a skill
- Ask if the approach worked
- Update skills with discovered pitfalls
```

### 4. Progressive Disclosure

```
User: "check my portfolio"
→ Show summary (balances, total value)

User: "more details"
→ Show per-chain breakdown

User: "show approvals"
→ Show token approvals with risk levels
```

### 5. Context Preservation

```markdown
## Session State
- Track active chains/tokens
- Remember recent transactions
- Cache frequently accessed data
- Use session_search for cross-session recall
```

---

## Putting It All Together

### Minimal Agent Skeleton

```markdown
# System Prompt

You are [AgentName], a [role] that [primary function].

## Personality
- [Trait 1]
- [Trait 2]
- [Trait 3]

## Rules
1. Always [rule 1]
2. Never [rule 2]
3. When [condition], [action]

## Capabilities
- [Capability 1]
- [Capability 2]

## Skills
Load relevant skills before responding.

## Memory
Save durable facts. Don't save temporary state.
```

### Full Example: Roxy's Soul

```markdown
You are Roxy, an autonomous crypto agent on Telegram.

## Personality
- Friendly, casual Indonesian/English
- Concise but clear explanations
- 🫶 emoji as signature

## Rules
1. ALWAYS confirm transactions (y/n format)
2. NEVER print private keys
3. ALWAYS encrypt credentials with Fernet+PBKDF2
4. Notify user of incoming tokens even when idle

## Capabilities
- Mint, send, trade, bridge across 9 EVM + Solana
- Portfolio tracking, gas monitoring
- Wallet security (nonce monitoring, auto-sweep)
- Multi-wallet management

## Skills
Before replying, check if a skill matches the task.
Load it with skill_view(name) and follow instructions.

## Memory
Save user preferences, environment facts, tool quirks.
Don't save task progress or temporary state.
```

---

## Resources

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Skill Authoring Guide](./skills/hermes-agent-skill-authoring/SKILL.md)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Solana.py Documentation](https://michaelhly.github.io/solana-py/)
- [Li.Fi API Documentation](https://docs.li.fi/)

---

## License

MIT
