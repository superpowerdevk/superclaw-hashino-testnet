---
name: superclaw-hashino-testnet
description: Let a team member play provably-fair Hashino against the live on-chain escrow contract on the Sepolia TESTNET, from inside the SuperClaw app — no terminal, wallet, or faucet needed. Use this skill whenever someone wants to test the Hashino betting game: check their test balance, place a bet (even/odd, hi/lo, or an exact digit), watch it settle via real Chainlink VRF, top up mock USDT, or verify a past bet. All bets use MOCK USDT on a testnet — no real money is ever involved. Trigger on phrases like "play hashino", "test the game", "place a bet", "bet 10 on even", "check my hashino balance", "did my bet win", "top up test usdt". This is the testnet QA tool; it is NOT a real-money product.
---

# SuperClaw Hashino — Testnet QA Skill

A way for the team to exercise the **real, deployed Hashino escrow contract** on the
Sepolia testnet from inside the app. Every bet is a genuine on-chain transaction
settled by **live Chainlink VRF** — the same flow that will run on mainnet later —
but it uses **mock USDT** and a shared throwaway test wallet, so there is **no real
money and no risk**.

> 🧪 **This is testnet QA, not a product.** Always make clear to the user that bets
> use mock USDT on a testnet. Never imply real money, real winnings, or that this is
> a live gambling product. The mainnet/real-money path is gated on a professional
> audit, jurisdiction/age gating, and licensing — none of which are in place.

## How it works

The skill is a thin client. It holds **no keys** and signs **nothing**. It calls a
betting **sidecar** (a small service that holds a throwaway testnet key and talks to
the contract) over HTTPS, then renders the result. This mirrors how the Kronos and
gmgn sidecars work.

Run the client with a single command:

```
python3 hashino_testnet.py <command> [args]
```

It prints clean Markdown. **Restyle that output in your voice** before showing it —
keep it compact and mobile-friendly, keep the 🧪 testnet note, and keep the numbers
and tx references exact.

## Commands → natural language

| User says (examples) | Run |
| --- | --- |
| "check my balance", "how much test USDT do I have", "game status" | `balance` |
| "bet 10 on even", "put 5 on hi", "wager 20 lower" | `bet even 10` |
| "bet 10 that the digit is 7", "exact digit 3 for 5" | `bet digit 10 7` |
| "did my bet win", "what's the result", "check bet <id>" | `result <request_id>` |
| "top me up", "I'm out of test USDT", "give me more" | `faucet` |
| "refill the house", "bankroll is low" | `faucet house 2000` |
| "verify that bet", "prove it was fair" | `verify <request_id>` |
| "how do I play", "what can I do" | `help` |

Note: "lower"/"low" → `lo`, "higher"/"high" → `hi`.

**Markets:** `even`, `odd`, `hi` (nibble 8–15), `lo` (nibble 0–7) all pay ~1.98×.
`digit` (guess the exact nibble 0–15) pays ~15.84×. The 1% house edge is shown openly.

## What to expect when a bet is placed (IMPORTANT for UX)

Settlement runs through Chainlink VRF, which takes ~1–2 minutes. So a bet is **two
steps**, and you should keep the user informed the whole time so it never looks
frozen:

1. Run `bet …`. It returns **immediately** with a `request_id` and "Settling… ~1–2
   min." **Show that to the user right away** so they see the bet landed.
2. Then run `result <request_id>` to fetch the outcome. Each call waits ~15s and
   returns either the win/loss card or "Still settling." If it's still settling,
   **post a short update** ("⏳ still waiting on Chainlink…") and call `result` again.
   Repeat until it settles (usually 1–4 calls). Then show the final card.

Never place a bet and then go silent — always confirm the placement first, then
narrate the wait via repeated `result` checks.

If a bet is rejected:
- **"house liquidity too low"** → run `faucet house 2000`, then retry.
- **"out of USDT"** → run `faucet`, then retry.
- **"bet must be 1–100 USDT"** → amount is outside the configured limits.

## Configuration (set once by the installer)

The skill resolves the sidecar from environment variables first, then a config file:

- `HASHINO_SIDECAR_URL` / `HASHINO_API_KEY` env vars, **or**
- `~/.superclaw-games/hashino_config.json` → `{"sidecar_url": "...", "api_key": "..."}`

If neither is present, the client says the sidecar isn't configured — that means it
hasn't been wired up yet (see the project README).

## Hard line (do not cross)

This skill is for **testnet QA only**. Do not adapt it, or describe how to adapt it,
to take real money or run on mainnet. Real-money operation requires a completed
professional audit, an enforced jurisdiction/age gating layer, responsible-gambling
guardrails, and the appropriate licensing — all explicitly out of scope here.
