#!/usr/bin/env python3
"""SuperClaw Hashino (TESTNET) — in-app client.

The team plays provably-fair Hashino against the live Sepolia contract WITHOUT a
terminal, wallet, or faucet. This script holds NO keys and signs nothing — it just
calls the betting sidecar over HTTPS and renders the result. All bets use MOCK USDT
on a testnet: no real money is ever involved.

Bets settle via Chainlink VRF, which takes ~1-2 min. So a bet is TWO quick steps:
  1) `bet`     places it and returns immediately (so the app never looks frozen)
  2) `result`  fetches the outcome; the agent polls this and shows live progress

Commands (the agent maps natural language onto these):
  balance                      show test-wallet + house balances and bet limits
  bet <market> <amount> [n]    place a bet (returns instantly with a request_id)
                               market = even | odd | hi | lo | digit
                               for digit, n = the exact nibble 0-15
  result <request_id>          fetch the outcome (poll until settled)
  faucet [player|house] [amt]  top up mock USDT so QA never stalls
  verify <request_id>          explain a settled bet (provably fair)
  help

Config: env HASHINO_SIDECAR_URL / HASHINO_API_KEY, else
        ~/.superclaw-games/hashino_config.json  {"sidecar_url":..., "api_key":...}
"""
import os
import sys
import time

import requests


def _load_cfg():
    import json
    import pathlib
    p = pathlib.Path.home() / ".superclaw-games" / "hashino_config.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


_CFG = _load_cfg()
# Shipped defaults so the skill works the moment it's installed — no per-user setup.
# TESTNET ONLY: this gates a mock-USDT sidecar, so a shared key here is low-risk.
# Precedence: env vars > ~/.superclaw-games/hashino_config.json > these defaults.
DEFAULT_SIDECAR_URL = "https://superclaw-hashino-sidecar.onrender.com"
DEFAULT_API_KEY = "claw-test-123"
BASE = (os.environ.get("HASHINO_SIDECAR_URL") or _CFG.get("sidecar_url") or DEFAULT_SIDECAR_URL).rstrip("/")
API_KEY = os.environ.get("HASHINO_API_KEY") or _CFG.get("api_key") or DEFAULT_API_KEY
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
TIMEOUT = 30
RESULT_TRIES = int(os.environ.get("HASHINO_RESULT_TRIES", "3"))   # per `result` call
RESULT_EVERY = float(os.environ.get("HASHINO_RESULT_EVERY", "5"))  # ~15s per call

MARKETS = {"even", "odd", "hi", "lo", "digit"}
WIN_RULE = {
    "even": "nibble is even (0,2,4…)", "odd": "nibble is odd (1,3,5…)",
    "hi": "nibble is 8–15", "lo": "nibble is 0–7", "digit": "nibble matches exactly",
}
BANNER = "🧪 **TESTNET** · mock USDT · no real money"


def _die(msg):
    print(f"⚠️ {msg}")
    sys.exit(0)


def _get(path):
    return requests.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT).json()


def _post(path, body):
    return requests.post(f"{BASE}{path}", json=body, headers=HEADERS, timeout=TIMEOUT).json()


def _need_config():
    if not BASE:
        _die("Sidecar not configured. Set HASHINO_SIDECAR_URL + HASHINO_API_KEY, "
             "or write ~/.superclaw-games/hashino_config.json.")


def cmd_balance():
    d = _get("/health")
    if not d.get("ok", True) and "error" in d:
        _die(f"sidecar unreachable: {d['error']}")
    print(f"{BANNER}\n")
    print("### 🎰 Hashino — testnet status")
    print(f"- Test wallet: **{d['player_usdt']:.2f} USDT**  ·  {d['player_eth']:.4f} ETH (gas)")
    print(f"- House bankroll: **{d['house_usdt']:.2f} USDT**  ·  free liquidity {d['free_liquidity']:.2f}")
    print(f"- Bet limits: {d['min_bet']:.0f}–{d['max_bet']:.0f} USDT  ·  house edge {d['edge_pct']:.1f}%")
    print(f"- Contract: `{d['hashino']}` (Sepolia)")
    if d["player_eth"] < 0.005:
        print("\n> ⛽ Test wallet low on Sepolia ETH for gas — top it up from a faucet.")


def cmd_bet(args):
    if not args:
        _die("usage: bet <even|odd|hi|lo|digit> <amount> [nibble 0-15]")
    market = args[0].lower()
    if market not in MARKETS:
        _die(f"market must be one of: {', '.join(sorted(MARKETS))}")
    try:
        amount = float(args[1])
    except (IndexError, ValueError):
        _die("amount (USDT) required, e.g. `bet even 10`")
    choice = 0
    if market == "digit":
        try:
            choice = int(args[2])
        except (IndexError, ValueError):
            _die("digit bets need a target nibble 0-15, e.g. `bet digit 5 7`")

    res = _post("/bet", {"market": market, "amount": amount, "choice": choice})
    if not res.get("ok"):
        _die(f"bet rejected: {res.get('error', 'unknown error')}")

    rid = res["request_id"]
    pick = f"digit {choice}" if market == "digit" else market
    print(f"{BANNER}\n")
    print(f"### 🎲 Bet placed — {amount:.0f} USDT on **{pick}**")
    print(f"- Potential payout: **{res['potential_payout']:.2f} USDT**")
    print(f"- Win if: {WIN_RULE[market]}")
    print(f"- VRF request `{rid[:12]}…`  ·  tx `{res['tx_hash'][:12]}…`")
    print("\n⏳ Settling on-chain via Chainlink VRF — usually 1–2 min.")
    print(f"NEXT: fetch the outcome with `result {rid}`")


def _render_result(r):
    won, nib, payout = r["won"], r["nibble"], r["payout"]
    amount = r.get("amount", 0.0)
    market = r.get("market", "")
    pick = f"digit {r.get('choice')}" if market == "digit" else market
    print(f"{BANNER}\n")
    if won:
        print(f"### ✅ WON — rolled nibble **{nib}**")
        print(f"- Bet **{pick}** ({amount:.0f} USDT) → paid out **{payout:.2f} USDT** (net +{payout - amount:.2f})")
    else:
        print(f"### ❌ Lost — rolled nibble **{nib}**")
        print(f"- Bet **{pick}** → {amount:.0f} USDT stake goes to the house")
    print(f"- Settled on-chain · tx `{r['tx_hash'][:12]}…`")
    print(f"\n{BANNER} · outcome from live Chainlink VRF — nobody could predict it.")


def cmd_result(args):
    if not args:
        _die("usage: result <request_id>")
    rid = args[0]
    for _ in range(RESULT_TRIES):
        r = _get(f"/result/{rid}")
        if "error" in r:
            _die(r["error"])
        if r.get("settled"):
            return _render_result(r)
        time.sleep(RESULT_EVERY)
    print(f"{BANNER}\n")
    print(f"⏳ Still settling — Chainlink VRF hasn't returned yet. "
          f"Check again with `result {rid}` in a few seconds.")


def cmd_faucet(args):
    target = "player"
    amount = 1000.0
    for a in args:
        if a.lower() in ("player", "house"):
            target = a.lower()
        else:
            try:
                amount = float(a)
            except ValueError:
                pass
    res = _post("/faucet", {"target": target, "amount": amount})
    if not res.get("ok"):
        _die(f"faucet failed: {res.get('error', 'unknown')}")
    b = res["balances"]
    print(f"{BANNER}\n")
    print(f"### ⛽ Minted {res['minted']:.0f} mock USDT → {target}")
    print(f"- Test wallet: **{b['player_usdt']:.2f} USDT**  ·  House: **{b['house_usdt']:.2f} USDT**")


def cmd_verify(args):
    if not args:
        _die("usage: verify <request_id>")
    r = _get(f"/result/{args[0]}")
    if "error" in r:
        _die(r["error"])
    if not r.get("settled"):
        print(f"{BANNER}\n\n⏳ That bet hasn't settled yet — VRF is still pending.")
        return
    print(f"{BANNER}\n")
    print("### 🔍 Bet verification")
    print(f"- Rolled nibble: **{r['nibble']}** (= VRF random word mod 16)")
    print(f"- Outcome: **{'WON' if r['won'] else 'LOST'}**  ·  payout field {r['payout']:.2f} USDT")
    print(f"- Settlement tx: `{r['tx_hash']}`")
    print("\nThe nibble comes from a Chainlink VRF random number only the VRF "
          "coordinator can produce — provably fair and impossible to predict.")


def cmd_help():
    print(f"{BANNER}\n")
    print("### 🎰 Hashino testnet — commands")
    print("- `balance` — wallet, house bankroll, limits")
    print("- `bet even 10` / `bet lo 5` / `bet digit 10 7` — place a bet (returns instantly)")
    print("- `result <request_id>` — fetch the outcome once VRF settles")
    print("- `faucet` — top up mock USDT  (`faucet house 2000` to refill the bankroll)")
    print("- `verify <request_id>` — re-check a settled bet")


def main():
    _need_config()
    argv = sys.argv[1:]
    cmd = (argv[0].lower() if argv else "help")
    rest = argv[1:]
    try:
        if cmd == "balance":
            cmd_balance()
        elif cmd == "bet":
            cmd_bet(rest)
        elif cmd == "result":
            cmd_result(rest)
        elif cmd == "faucet":
            cmd_faucet(rest)
        elif cmd == "verify":
            cmd_verify(rest)
        else:
            cmd_help()
    except requests.RequestException as e:
        _die(f"could not reach the sidecar: {e}")


if __name__ == "__main__":
    main()
