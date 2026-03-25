#!/usr/bin/env python3

import asyncio
import argparse
import re
import sys
import os
from datetime import datetime
from colorama import Fore, init

import aiohttp

from platforms     import PLATFORMS
from osint         import get_provider, get_domain, get_username, check_mx, check_whois, gravatar_osint, md5
from proxy_manager import resolve_proxies, pick, is_ngrok_proxy
from scanner       import run_scan
from report        import save_html, save_json

init(autoreset=True)

BANNER = r"""
  ___ __  __   _   ___ _    ___ ___ _  _ _____
 | __|  \/  | /_\ |_ _| |  / __| __| \| |_   _|
 | _|| |\/| |/ _ \ | || |__\__ \ _|| .` | | |
 |___|_|  |_/_/ \_\___|____|___/___|_|\_| |_|
  v3.0 — Email OSINT Tool
"""

# ─── Dashboard Push ───────────────────────────────────────────────────────────

DASHBOARD_URL  = os.environ.get("PROXY_URL",  "").rstrip("/")
DASHBOARD_AUTH = os.environ.get("PROXY_AUTH", "emailsint2024")


async def push(session: aiohttp.ClientSession, payload: dict):
    """Push status or result to the live dashboard (best-effort)."""
    if not DASHBOARD_URL:
        return
    try:
        async with session.post(
            f"{DASHBOARD_URL}/push",
            json=payload,
            headers={"X-Proxy-Auth": DASHBOARD_AUTH},
            timeout=aiohttp.ClientTimeout(total=5),
            ssl=False,
        ) as _:
            pass
    except Exception:
        pass


# ─── Print helpers ────────────────────────────────────────────────────────────

def print_result(r: dict, verbose: bool):
    if r["error"]:
        if verbose:
            print(Fore.RED + f"  [!] {r['name']:<24} → {r['error']}")
    elif r["found"]:
        uname = f" → {Fore.YELLOW}@{r['username']}" if r.get("username") else ""
        print(Fore.GREEN + f"  [✔] {r['name']:<24} {Fore.CYAN}({r['category']}){uname}")
    elif verbose:
        print(Fore.RED + f"  [✗] {r['name']:<24} → not found")


# ─── Main scan ────────────────────────────────────────────────────────────────

async def main_scan(email: str, proxy_file: str, timeout: int,
                    output_json: str, output_html: str, verbose: bool):

    print(Fore.CYAN + BANNER)
    print(Fore.YELLOW + f"  [*] Email     : {email}")
    print(Fore.YELLOW + f"  [*] Username  : {get_username(email)}")
    print(Fore.YELLOW + f"  [*] Domain    : {get_domain(email)}")
    print(Fore.YELLOW + f"  [*] Platforms : {len(PLATFORMS)}")
    print(Fore.YELLOW + f"  [*] Started   : {datetime.now().strftime('%H:%M:%S')}\n")

    if DASHBOARD_URL:
        print(Fore.CYAN  + f"  [*] Dashboard : {DASHBOARD_URL}")
        print(Fore.GREEN + f"  [✔] Ergebnisse werden live gepusht\n")

    # ── Email Analysis ────────────────────────────────────────────────────────
    print(Fore.CYAN + "  ── Email Analysis ─────────────────────────────")
    provider   = get_provider(email)
    mx         = check_mx(email)
    whois_data = check_whois(email)

    print(Fore.WHITE + f"  [i] Provider  : {Fore.CYAN}{provider}")

    if mx.get("valid"):
        print(Fore.GREEN + f"  [✔] MX Record : {mx['primary_mx']}")
    else:
        print(Fore.RED   + f"  [✘] MX Record : not reachable")

    if "error" not in whois_data:
        print(Fore.WHITE + f"  [i] Domain reg: {Fore.CYAN}{whois_data['created']}")
        print(Fore.WHITE + f"  [i] Registrar : {Fore.CYAN}{whois_data['registrar']}")
    else:
        print(Fore.RED   + f"  [!] WHOIS     : {whois_data.get('error','failed')}")

    # ── Gravatar OSINT ────────────────────────────────────────────────────────
    print()
    print(Fore.CYAN + "  ── Gravatar OSINT ─────────────────────────────")

    gravatar = {}
    async with aiohttp.ClientSession() as s:
        gravatar = await gravatar_osint(s, email)

        # Push initial scan info + gravatar to dashboard
        await push(s, {
            "reset":    True,
            "email":    email,
            "running":  True,
            "meta": {
                "provider":  provider,
                "mx":        mx,
                "whois":     whois_data,
                "gravatar":  gravatar,
                "platforms": len(PLATFORMS),
                "started":   datetime.now().isoformat(),
            }
        })

    if gravatar.get("found"):
        print(Fore.GREEN + f"  [✔] Profile found!")
        if gravatar.get("displayName"):
            print(Fore.WHITE + f"  [i] Name      : {Fore.YELLOW}{gravatar['displayName']}")
        if gravatar.get("username"):
            print(Fore.WHITE + f"  [i] Username  : {Fore.YELLOW}@{gravatar['username']}")
        if gravatar.get("location"):
            print(Fore.WHITE + f"  [i] Location  : {Fore.CYAN}{gravatar['location']}")
        if gravatar.get("bio"):
            bio = gravatar["bio"][:80] + ("…" if len(gravatar["bio"]) > 80 else "")
            print(Fore.WHITE + f"  [i] Bio       : {Fore.CYAN}{bio}")
        if gravatar.get("linked_accounts"):
            accs = ", ".join(a["domain"] for a in gravatar["linked_accounts"])
            print(Fore.WHITE + f"  [i] Linked    : {Fore.CYAN}{accs}")
        for url in gravatar.get("urls", [])[:3]:
            print(Fore.WHITE + f"  [i] URL       : {Fore.CYAN}{url}")
        print(Fore.WHITE + f"  [i] Avatar    : {Fore.CYAN}https://www.gravatar.com/avatar/{md5(email)}")
    else:
        print(Fore.RED + "  [✘] No Gravatar profile found")

    # ── Proxy Setup ───────────────────────────────────────────────────────────
    print()
    print(Fore.CYAN + "  ── Proxy Setup ────────────────────────────────")

    proxies = await resolve_proxies(proxy_file=proxy_file)

    if not proxies:
        print(Fore.YELLOW + "  [!] No proxies — running direct\n")
    elif is_ngrok_proxy(proxies[0]):
        print(Fore.GREEN + f"  [✔] Using own ngrok proxy server\n")
    else:
        print(Fore.GREEN + f"  [✔] {len(proxies)} working proxies ready\n")

    # ── Platform Scan ─────────────────────────────────────────────────────────
    print(Fore.CYAN + "  ── Platform Scan ──────────────────────────────\n")

    results = await run_scan(
        PLATFORMS, email, proxies, timeout,
        on_result=lambda r: print_result(r, verbose),
        dashboard_url=DASHBOARD_URL,
        dashboard_auth=DASHBOARD_AUTH,
    )

    found  = [r for r in results if r["found"]]
    errors = [r for r in results if r["error"]]

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print(Fore.YELLOW + "  " + "─" * 48)
    print(Fore.GREEN  + f"  Accounts found  : {len(found)}")
    print(Fore.RED    + f"  Errors/Timeouts : {len(errors)}")
    print(Fore.YELLOW + "  " + "─" * 48)

    if found:
        print(Fore.GREEN + "\n  Registered on:")
        for r in sorted(found, key=lambda x: x["category"]):
            uname = f"  (@{r['username']})" if r.get("username") else ""
            print(f"    • {r['name']:<26} [{r['category']}]{uname}")

    if output_json:
        save_json(email, found, mx, whois_data, provider, gravatar, output_json)
        print(Fore.YELLOW + f"\n  [*] JSON saved : {output_json}")

    if output_html:
        save_html(email, found, mx, whois_data, provider, gravatar, output_html)
        print(Fore.YELLOW + f"  [*] HTML saved : {output_html}")

    # Dashboard: show completion + ngrok link
    if DASHBOARD_URL:
        print()
        print(Fore.GREEN + f"  ╔══════════════════════════════════════════════╗")
        print(Fore.GREEN + f"  ║  ✔  Scan abgeschlossen!                      ║")
        print(Fore.GREEN + f"  ║                                              ║")
        print(Fore.GREEN + f"  ║  📊 Ergebnisse:                              ║")
        print(Fore.GREEN + f"  ║  {DASHBOARD_URL:<44}  ║")
        print(Fore.GREEN + f"  ╚══════════════════════════════════════════════╝")

    print()


def main():
    ap = argparse.ArgumentParser(description="emailsint v3.0 — Email OSINT Tool")
    ap.add_argument("email")
    ap.add_argument("-p", "--proxies", default=None)
    ap.add_argument("-t", "--timeout", type=int, default=12)
    ap.add_argument("-o", "--output",  default=None)
    ap.add_argument("--html",          default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", args.email):
        print(Fore.RED + "[!] Invalid email address.")
        sys.exit(1)

    asyncio.run(main_scan(
        args.email, args.proxies, args.timeout,
        args.output, args.html, args.verbose,
    ))


if __name__ == "__main__":
    main()
