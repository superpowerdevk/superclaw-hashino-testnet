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
| "bet 10 on even", "put 5 on hi", "wager 20 odd" | `bet even 10` |
| "bet 10 that the digit is 7", "exact digit 3 for 5" | `bet digit 10 7` |
| "top me up", "I'm out of test USDT", "give me more" | `faucet` |
| "refill the house", "bankroll is low" | `faucet house 2000` |
| "did my bet win", "check bet <id>", "verify that bet" | `verify <request_id>` |
| "how do I play", "what can I do" | `help` |

**Markets:** `even`, `odd`, `hi` (nibble 8–15), `lo` (nibble 0–7) all pay ~1.98×.
`digit` (guess the exact nibble 0–15) pays ~15.84×. The 1% house edge is shown openly.

## What to expect when a bet is placed

`bet` places the wager on-chain, then **waits for Chainlink VRF to settle** (usually
1–2 minutes on Sepolia). The client polls automatically and prints the final
win/loss with the rolled nibble. If VRF is slow and it times out, it returns a
`request_id`; tell the user you'll check again, and run `verify <request_id>` shortly
after.

If a bet is rejected:
- **"house liquidity too low"** → run `faucet house 2000` to refill the bankroll, then retry.
- **"out of USDT"** → run `faucet` to top up the test wallet, then retry.
- **"bet must be 1–100 USDT"** → the amount is outside the configured limits.

## Configuration (set once by the installer)

The skill reads two environment variables:

- `HASHINO_SIDECAR_URL` — the deployed sidecar URL (e.g. `https://superclaw-hashino-sidecar.onrender.com`)
- `HASHINO_API_KEY` — the shared secret (must match the sidecar's `API_KEY`)

If `HASHINO_SIDECAR_URL` is unset, the client says so — that means the sidecar
hasn't been wired up yet (see the project README for deploy steps).

## Hard line (do not cross)

This skill is for **testnet QA only**. Do not adapt it, or describe how to adapt it,
to take real money or run on mainnet. Real-money operation requires a completed
professional audit, an enforced jurisdiction/age gating layer, responsible-gambling
guardrails, and the appropriate licensing — all explicitly out of scope here.
