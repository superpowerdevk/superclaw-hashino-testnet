#!/usr/bin/env python3
"""SuperClaw Hashino (TESTNET) — in-app client.

The team plays provably-fair Hashino against the live Sepolia contract WITHOUT a
terminal, wallet, or faucet. This script holds NO keys and signs nothing — it
just calls the betting sidecar over HTTPS and renders the result. All bets use
MOCK USDT on a testnet: no real money is ever involved.

Commands (the agent maps natural language onto these):
  balance                      show test-wallet + house balances and bet limits
  bet <market> <amount> [n]    place a bet and wait for the on-chain result
                               market = even | odd | hi | lo | digit
                               for digit, n = the exact nibble 0-15
  faucet [player|house] [amt]  top up mock USDT so QA never stalls
  verify <request_id>          re-check / explain a settled bet (provably fair)
  help

Config (env): HASHINO_SIDECAR_URL  (e.g. https://superclaw-hashino-sidecar.onrender.com)
              HASHINO_API_KEY      (same secret set on the sidecar)
"""
import os
import sys
import time

import requests

def _load_cfg():
    import json, pathlib
    p = pathlib.Path.home() / ".superclaw-games" / "hashino_config.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}
_CFG = _load_cfg()
BASE = (os.environ.get("HASHINO_SIDECAR_URL") or _CFG.get("sidecar_url", "")).rstrip("/")
API_KEY = os.environ.get("HASHINO_API_KEY") or _CFG.get("api_key", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
TIMEOUT = 30
POLL_TRIES = int(os.environ.get("HASHINO_POLL_TRIES", "30"))
POLL_EVERY = float(os.environ.get("HASHINO_POLL_EVERY", "5"))   # ~150s total wait for VRF

MARKETS = {"even", "odd", "hi", "lo", "digit"}
WIN_RULE = {
    "even": "nibble is even (0,2,4…)", "odd": "nibble is odd (1,3,5…)",
    "hi": "nibble is 8–15", "lo": "nibble is 0–7", "digit": "nibble exactly matches",
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
        _die("HASHINO_SIDECAR_URL is not set. Point it at the deployed sidecar URL.")


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
        print("\n> ⛽ Test wallet is low on Sepolia ETH for gas — top it up from a faucet.")


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

    body = {"market": market, "amount": amount, "choice": choice}
    res = _post("/bet", body)
    if not res.get("ok"):
        _die(f"bet rejected: {res.get('error', 'unknown error')}")

    rid = res["request_id"]
    pick = f"digit {choice}" if market == "digit" else market
    print(f"{BANNER}\n")
    print(f"### 🎲 Bet placed — {amount:.0f} USDT on **{pick}**")
    print(f"- Potential payout: **{res['potential_payout']:.2f} USDT**")
    print(f"- Win if: {WIN_RULE[market]}")
    print(f"- VRF request: `{rid[:10]}…`  ·  tx `{res['tx_hash'][:12]}…`")
    print("\n_Waiting for Chainlink VRF to settle on-chain…_")

    for _ in range(POLL_TRIES):
        time.sleep(POLL_EVERY)
        r = _get(f"/result/{rid}")
        if r.get("settled"):
            return _render_result(r, amount, pick)
    print(f"\n> ⏳ Still settling (VRF can take a couple minutes). "
          f"Check again with: `verify {rid}`")


def _render_result(r, amount, pick):
    won, nib, payout = r["won"], r["nibble"], r["payout"]
    print()
    if won:
        print(f"### ✅ WON — rolled nibble **{nib}**")
        print(f"- Bet **{pick}** → paid out **{payout:.2f} USDT** (net +{payout - amount:.2f})")
    else:
        print(f"### ❌ Lost — rolled nibble **{nib}**")
        print(f"- Bet **{pick}** → stake of {amount:.0f} USDT goes to the house")
    print(f"- Settled on-chain · tx `{r['tx_hash'][:12]}…`")
    print(f"\n{BANNER} · result came from live Chainlink VRF — nobody could predict it.")


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
    print("\nThe nibble is derived from a Chainlink VRF random number that only the "
          "VRF coordinator can produce — provably fair and impossible to predict.")


def cmd_help():
    print(f"{BANNER}\n")
    print("### 🎰 Hashino testnet — commands")
    print("- `balance` — wallet, house bankroll, limits")
    print("- `bet even 10` / `bet hi 5` / `bet digit 10 7` — place a bet, get the result")
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
