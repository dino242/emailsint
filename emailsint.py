#!/usr/bin/env python3
"""
emailsint — Email OSINT Tool
Prüft 30+ Plattformen, scrapt Benutzernamen, macht MX/WHOIS/Provider-Check.
Kein externer API-Dienst — reines Scraping + DNS.
"""

import asyncio
import aiohttp
import argparse
import hashlib
import json
import re
import sys
import os
import socket
import dns.resolver
import whois
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

BANNER = r"""
  ___ __  __   _   ___ _    ___ ___ _  _ _____ 
 | __|  \/  | /_\ |_ _| |  / __| __| \| |_   _|
 | _|| |\/| |/ _ \ | || |__\__ \ _|| .` | | |  
 |___|_|  |_/_/ \_\___|____|___/___|_|\_| |_|  
  v1.0 // Made by dino242
"""

# ─── Automatische Proxy-Verwaltung ───────────────────────────────────────────
# Lädt kostenlose Proxies von öffentlichen Listen.
# Kein manuelles proxies.txt nötig.

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

async def fetch_auto_proxies(limit: int = 30) -> list:
    """Lädt automatisch kostenlose Proxies von öffentlichen Listen."""
    proxies = []
    try:
        async with aiohttp.ClientSession() as session:
            for source in PROXY_SOURCES:
                try:
                    async with session.get(source, timeout=aiohttp.ClientTimeout(total=8), ssl=False) as r:
                        if r.status == 200:
                            text = await r.text()
                            for line in text.strip().splitlines():
                                line = line.strip()
                                if re.match(r"\d+\.\d+\.\d+\.\d+:\d+", line):
                                    proxies.append(f"http://{line}")
                                elif line.startswith("http"):
                                    proxies.append(line)
                            if len(proxies) >= limit:
                                break
                except Exception:
                    continue
    except Exception:
        pass
    return proxies[:limit]

async def test_proxy(session: aiohttp.ClientSession, proxy: str, timeout: int = 5) -> bool:
    """Testet ob ein Proxy funktioniert."""
    try:
        async with session.get(
            "http://httpbin.org/ip",
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=timeout),
            ssl=False,
        ) as r:
            return r.status == 200
    except Exception:
        return False

async def get_working_proxies(proxies: list, max_workers: int = 20, needed: int = 10) -> list:
    """Testet Proxies parallel und gibt funktionierende zurück."""
    working = []
    async with aiohttp.ClientSession() as session:
        tasks = [test_proxy(session, p) for p in proxies[:max_workers * 2]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for proxy, ok in zip(proxies, results):
            if ok is True:
                working.append(proxy)
            if len(working) >= needed:
                break
    return working

# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def md5(s: str) -> str:
    return hashlib.md5(s.strip().lower().encode()).hexdigest()

def extract_between(text: str, start: str, end: str) -> str:
    """Extrahiert Text zwischen zwei Strings."""
    try:
        s = text.index(start) + len(start)
        e = text.index(end, s)
        return text[s:e].strip()
    except ValueError:
        return ""

# ─── E-Mail-Analyse (ohne externe APIs) ──────────────────────────────────────

PROVIDER_MAP = {
    "gmail.com":      "Google Gmail",
    "googlemail.com": "Google Gmail",
    "outlook.com":    "Microsoft Outlook",
    "hotmail.com":    "Microsoft Hotmail",
    "live.com":       "Microsoft Live",
    "msn.com":        "Microsoft MSN",
    "yahoo.com":      "Yahoo Mail",
    "yahoo.de":       "Yahoo Mail",
    "icloud.com":     "Apple iCloud",
    "me.com":         "Apple iCloud",
    "mac.com":        "Apple iCloud",
    "protonmail.com": "ProtonMail",
    "proton.me":      "ProtonMail",
    "tutanota.com":   "Tutanota",
    "gmx.de":         "GMX",
    "gmx.net":        "GMX",
    "gmx.at":         "GMX",
    "web.de":         "Web.de",
    "t-online.de":    "Telekom T-Online",
    "freenet.de":     "Freenet",
    "posteo.de":      "Posteo",
    "mailbox.org":    "Mailbox.org",
    "aol.com":        "AOL Mail",
    "zoho.com":       "Zoho Mail",
    "yandex.com":     "Yandex Mail",
    "yandex.ru":      "Yandex Mail",
}

def get_provider(email: str) -> str:
    domain = email.split("@")[-1].lower()
    return PROVIDER_MAP.get(domain, f"Unbekannt ({domain})")

def check_mx(email: str) -> dict:
    domain = email.split("@")[-1]
    try:
        records = dns.resolver.resolve(domain, "MX")
        mx_list = sorted(records, key=lambda r: r.preference)
        return {
            "valid": True,
            "mx_records": [str(r.exchange).rstrip(".") for r in mx_list],
            "primary_mx": str(mx_list[0].exchange).rstrip("."),
        }
    except Exception as e:
        return {"valid": False, "mx_records": [], "primary_mx": "", "error": str(e)}

def check_whois(email: str) -> dict:
    domain = email.split("@")[-1]
    try:
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        updated = w.updated_date
        if isinstance(updated, list):
            updated = updated[0]
        return {
            "domain":    domain,
            "registrar": w.registrar or "Unbekannt",
            "created":   str(created)[:10] if created else "Unbekannt",
            "updated":   str(updated)[:10] if updated else "Unbekannt",
            "country":   w.country or "Unbekannt",
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}

# ─── Plattformen ─────────────────────────────────────────────────────────────
# Felder:
#   url_fn        → Funktion(email) → URL
#   method        → GET / POST
#   headers       → dict
#   data          → Funktion(email) → POST-Body (str)
#   check         → keyword_found | keyword_missing | status_ok | json_eq
#   keyword       → Suchbegriff im Response-Text
#   ok_status     → Liste erlaubter HTTP-Status
#   json_key      → Punkt-Pfad im JSON (z.B. "data.exists")
#   json_val      → Erwarteter Wert
#   username_re   → Regex um Benutzernamen aus Response zu extrahieren

PLATFORMS = [
    # ── Tech ─────────────────────────────────────────────────────────────────
    {
        "name": "GitHub",
        "category": "Tech",
        "method": "POST",
        "url_fn": lambda e: "https://github.com/account/password_reset",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://github.com/password_reset",
        },
        "data": lambda e: f"email={e}",
        "check": "keyword_found",
        "keyword": "If your email address exists in our database",
    },
    {
        "name": "GitLab",
        "category": "Tech",
        "method": "POST",
        "url_fn": lambda e: "https://gitlab.com/users/password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"user[email]={e}",
        "check": "keyword_found",
        "keyword": "If your email address exists",
    },
    {
        "name": "Gravatar",
        "category": "Identity",
        "method": "GET",
        "url_fn": lambda e: f"https://www.gravatar.com/{md5(e)}.json",
        "check": "status_ok",
        "ok_status": [200],
        "username_re": r'"preferredUsername"\s*:\s*"([^"]+)"',
    },
    # ── Social ────────────────────────────────────────────────────────────────
    {
        "name": "Twitter / X",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://x.com/i/flow/password_reset",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://x.com/",
        },
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "We couldn't find",
    },
    {
        "name": "Tumblr",
        "category": "Social",
        "method": "GET",
        "url_fn": lambda e: f"https://www.tumblr.com/api/v2/user/check_email?email={e}",
        "check": "keyword_found",
        "keyword": '"exists":true',
    },
    {
        "name": "Pinterest",
        "category": "Social",
        "method": "GET",
        "url_fn": lambda e: (
            "https://www.pinterest.com/resource/EmailExistsResource/get/"
            f"?source_url=%2F&data=%7B%22options%22%3A%7B%22email%22%3A%22{e}%22%7D%7D"
        ),
        "check": "keyword_found",
        "keyword": '"data": true',
    },
    {
        "name": "Reddit",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://www.reddit.com/api/v1/password_reset",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "USER_DOESNT_EXIST",
    },
    {
        "name": "Instagram",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://www.instagram.com/accounts/account_recovery_send_ajax/",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.instagram.com/",
        },
        "data": lambda e: f"email_or_username={e}",
        "check": "keyword_found",
        "keyword": "email_found",
    },
    {
        "name": "Snapchat",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://accounts.snapchat.com/accounts/password_reset_email",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "No account found",
    },
    {
        "name": "VK",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://vk.com/login",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}&act=forgot_pass",
        "check": "keyword_missing",
        "keyword": "not found",
    },
    {
        "name": "Flickr",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://identity.flickr.com/sign-in",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "No account found",
    },
    # ── Professional ──────────────────────────────────────────────────────────
    {
        "name": "LinkedIn",
        "category": "Professional",
        "method": "POST",
        "url_fn": lambda e: "https://www.linkedin.com/uas/request-password-reset",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "email address is not associated",
    },
    {
        "name": "Xing",
        "category": "Professional",
        "method": "POST",
        "url_fn": lambda e: "https://www.xing.com/app/user?op=forgot_password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "not found",
    },
    {
        "name": "Freelancer",
        "category": "Professional",
        "method": "GET",
        "url_fn": lambda e: f"https://www.freelancer.com/ajax/checkuser.php?email={e}",
        "check": "keyword_found",
        "keyword": '"status":"taken"',
    },
    # ── Gaming ────────────────────────────────────────────────────────────────
    {
        "name": "Twitch",
        "category": "Gaming",
        "method": "GET",
        "url_fn": lambda e: f"https://passport.twitch.tv/register/check_available?email={e}",
        "check": "keyword_found",
        "keyword": '"isAvailable":false',
    },
    {
        "name": "Steam",
        "category": "Gaming",
        "method": "POST",
        "url_fn": lambda e: "https://store.steampowered.com/join/checkavail/",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://store.steampowered.com/join/",
        },
        "data": lambda e: f"accountname=doesnotmatter&email={e}&count=1",
        "check": "keyword_found",
        "keyword": '"bAvail":false',
    },
    {
        "name": "Epic Games",
        "category": "Gaming",
        "method": "POST",
        "url_fn": lambda e: "https://www.epicgames.com/id/api/v2/password/forgot/init",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"email": e}),
        "check": "keyword_missing",
        "keyword": "account_not_found",
    },
    {
        "name": "Roblox",
        "category": "Gaming",
        "method": "POST",
        "url_fn": lambda e: "https://auth.roblox.com/v2/passwords/forgot",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"email": e}),
        "check": "status_ok",
        "ok_status": [200],
    },
    # ── Music ─────────────────────────────────────────────────────────────────
    {
        "name": "Spotify",
        "category": "Music",
        "method": "POST",
        "url_fn": lambda e: "https://spclient.wg.spotify.com/signup/public/v1/account",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"validate=1&email={e}",
        "check": "keyword_found",
        "keyword": '"status":20',
    },
    {
        "name": "SoundCloud",
        "category": "Music",
        "method": "GET",
        "url_fn": lambda e: f"https://soundcloud.com/users/email_available?email={e}",
        "check": "keyword_found",
        "keyword": '"exists":true',
    },
    # ── Communication ─────────────────────────────────────────────────────────
    {
        "name": "Discord",
        "category": "Communication",
        "method": "POST",
        "url_fn": lambda e: "https://discord.com/api/v9/auth/forgot",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"login": e}),
        "check": "status_ok",
        "ok_status": [200],
    },
    {
        "name": "Telegram",
        "category": "Communication",
        "method": "POST",
        "url_fn": lambda e: "https://my.telegram.org/auth/send_password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"phone={e}",
        "check": "keyword_missing",
        "keyword": "error",
    },
    # ── Cloud / Produktivität ─────────────────────────────────────────────────
    {
        "name": "Dropbox",
        "category": "Cloud",
        "method": "POST",
        "url_fn": lambda e: "https://www.dropbox.com/forgot_password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"login_email={e}&t=",
        "check": "keyword_missing",
        "keyword": "There is no Dropbox account",
    },
    {
        "name": "Notion",
        "category": "Productivity",
        "method": "POST",
        "url_fn": lambda e: "https://www.notion.so/api/v3/sendTemporaryPassword",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"email": e}),
        "check": "keyword_missing",
        "keyword": "user not found",
    },
    {
        "name": "Evernote",
        "category": "Productivity",
        "method": "POST",
        "url_fn": lambda e: "https://www.evernote.com/Registration.action",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}&incomplete=true",
        "check": "keyword_found",
        "keyword": "already registered",
    },
    # ── Finance ───────────────────────────────────────────────────────────────
    {
        "name": "PayPal",
        "category": "Finance",
        "method": "POST",
        "url_fn": lambda e: "https://www.paypal.com/auth/validateEmail",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"email": e}),
        "check": "keyword_found",
        "keyword": '"data":true',
    },
    # ── Kreativ ───────────────────────────────────────────────────────────────
    {
        "name": "Adobe",
        "category": "Creative",
        "method": "POST",
        "url_fn": lambda e: "https://ims-na1.adobelogin.com/ims/check/v1/token",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"client_id=adobedotcom2&username={e}",
        "check": "keyword_found",
        "keyword": "account_exists",
    },
    {
        "name": "Behance",
        "category": "Creative",
        "method": "GET",
        "url_fn": lambda e: f"https://www.behance.net/action/emailAvailable?email={e}",
        "check": "keyword_found",
        "keyword": '"available":false',
    },
    {
        "name": "DeviantArt",
        "category": "Creative",
        "method": "GET",
        "url_fn": lambda e: f"https://www.deviantart.com/_puppy/accounts/emailavailable?email={e}",
        "check": "keyword_found",
        "keyword": '"exists":true',
    },
    # ── Shopping ──────────────────────────────────────────────────────────────
    {
        "name": "Etsy",
        "category": "Shopping",
        "method": "GET",
        "url_fn": lambda e: f"https://www.etsy.com/api/v3/ajax/member/email-check?email={e}",
        "check": "keyword_found",
        "keyword": '"member_exists":true',
    },
    {
        "name": "eBay",
        "category": "Shopping",
        "method": "POST",
        "url_fn": lambda e: "https://reg.ebay.de/reg/PartialRegistration?siteid=77&ru=https://www.ebay.de/",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"Email={e}&js_check=1",
        "check": "keyword_missing",
        "keyword": "no account",
    },
]

# ─── Proxy-Loader ────────────────────────────────────────────────────────────

def load_proxies(path: str) -> list:
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def pick_proxy(proxies: list, i: int):
    return proxies[i % len(proxies)] if proxies else None

# ─── Einzelner Plattform-Check ───────────────────────────────────────────────

async def check_platform(session: aiohttp.ClientSession,
                         p: dict, email: str,
                         proxy, timeout: int) -> dict:
    name = p["name"]
    cat  = p.get("category", "Other")
    try:
        url    = p["url_fn"](email)
        method = p.get("method", "GET").lower()
        hdrs   = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            **p.get("headers", {}),
        }
        data_fn = p.get("data")
        body    = data_fn(email) if data_fn else None

        kw = dict(
            headers=hdrs,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
            ssl=False,
        )
        if proxy: kw["proxy"] = proxy
        if body:  kw["data"]  = body

        async with getattr(session, method)(url, **kw) as resp:
            status = resp.status
            text   = await resp.text(errors="ignore")
            check  = p.get("check", "status_ok")
            found  = False

            if check == "status_ok":
                found = status in p.get("ok_status", [200])
            elif check == "keyword_found":
                found = p["keyword"] in text
            elif check == "keyword_missing":
                found = p["keyword"] not in text and status < 500
            elif check == "json_eq":
                try:
                    obj = json.loads(text)
                    for k in p["json_key"].split("."):
                        obj = obj.get(k, {}) if isinstance(obj, dict) else None
                    found = obj == p["json_val"]
                except Exception:
                    found = False

            # Benutzername scrapen
            username = None
            if found and p.get("username_re"):
                m = re.search(p["username_re"], text)
                if m:
                    username = m.group(1)

            return {
                "name": name, "category": cat,
                "found": found, "username": username, "error": None,
            }

    except asyncio.TimeoutError:
        return {"name": name, "category": cat, "found": False, "username": None, "error": "Timeout"}
    except Exception as ex:
        return {"name": name, "category": cat, "found": False, "username": None, "error": str(ex)[:70]}

# ─── HTML-Report ─────────────────────────────────────────────────────────────

def save_html(email: str, found: list, mx: dict, whois_data: dict, provider: str, path: str):
    rows = ""
    for r in sorted(found, key=lambda x: x["category"]):
        uname = f'<span class="username">@{r["username"]}</span>' if r.get("username") else ""
        rows += f'<tr><td>{r["name"]}</td><td>{r["category"]}</td><td>{uname}</td></tr>\n'

    mx_html = "<br>".join(mx.get("mx_records", [])) or "—"
    w_created  = whois_data.get("created",   "—")
    w_registrar= whois_data.get("registrar", "—")
    w_country  = whois_data.get("country",   "—")

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>emailsint — {email}</title>
<style>
  body {{ font-family: 'Courier New', monospace; background: #0d1117; color: #c9d1d9; margin: 40px; }}
  h1   {{ color: #58a6ff; }}
  h2   {{ color: #79c0ff; border-bottom: 1px solid #30363d; padding-bottom: 6px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .label {{ color: #8b949e; font-size: 12px; }}
  .value {{ color: #e6edf3; font-size: 15px; font-weight: bold; margin-top: 4px; }}
  .valid   {{ color: #3fb950; }}
  .invalid {{ color: #f85149; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th    {{ background: #21262d; color: #8b949e; text-align: left; padding: 10px; }}
  td    {{ padding: 10px; border-bottom: 1px solid #21262d; }}
  tr:hover td {{ background: #161b22; }}
  .username {{ color: #58a6ff; }}
  .footer {{ color: #8b949e; font-size: 12px; margin-top: 40px; }}
</style>
</head>
<body>
<h1>📧 emailsint Report</h1>
<p>E-Mail: <strong>{email}</strong> &nbsp;|&nbsp; Erstellt: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>

<h2>E-Mail Analyse</h2>
<div class="info-grid">
  <div class="card">
    <div class="label">Anbieter</div>
    <div class="value">{provider}</div>
  </div>
  <div class="card">
    <div class="label">MX-Record (erreichbar)</div>
    <div class="value {'valid' if mx.get('valid') else 'invalid'}">
      {'✔ Ja' if mx.get('valid') else '✘ Nein'}<br>
      <small>{mx_html}</small>
    </div>
  </div>
  <div class="card">
    <div class="label">Domain registriert seit</div>
    <div class="value">{w_created}</div>
  </div>
  <div class="card">
    <div class="label">Registrar / Land</div>
    <div class="value">{w_registrar}<br><small>{w_country}</small></div>
  </div>
</div>

<h2>Gefundene Accounts ({len(found)})</h2>
<table>
  <tr><th>Plattform</th><th>Kategorie</th><th>Benutzername</th></tr>
  {rows if rows else '<tr><td colspan="3">Keine Accounts gefunden.</td></tr>'}
</table>

<div class="footer">Erstellt mit emailsint — nur für eigene E-Mail-Adressen verwenden.</div>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

# ─── Runner ──────────────────────────────────────────────────────────────────

async def run(email: str, proxy_file, timeout: int, output_json, output_html, verbose: bool):
    print(Fore.CYAN + BANNER)
    print(Fore.YELLOW + f"  [*] E-Mail      : {email}")
    print(Fore.YELLOW + f"  [*] Plattformen : {len(PLATFORMS)}")
    print(Fore.YELLOW + f"  [*] Gestartet   : {datetime.now().strftime('%H:%M:%S')}\n")

    # ── E-Mail-Analyse ────────────────────────────────────────────────────────
    print(Fore.CYAN + "  ── E-Mail Analyse ──────────────────────────────")
    provider = get_provider(email)
    print(Fore.WHITE + f"  [i] Anbieter    : {Fore.CYAN}{provider}")

    mx = check_mx(email)
    if mx["valid"]:
        print(Fore.GREEN + f"  [✔] MX-Record   : {mx['primary_mx']}")
    else:
        print(Fore.RED + f"  [✘] MX-Record   : nicht erreichbar")

    print(Fore.WHITE + "  [i] WHOIS       : wird abgerufen...")
    whois_data = check_whois(email)
    if "error" not in whois_data:
        print(Fore.WHITE + f"  [i] Domain seit : {Fore.CYAN}{whois_data['created']}")
        print(Fore.WHITE + f"  [i] Registrar   : {Fore.CYAN}{whois_data['registrar']}")
    else:
        print(Fore.RED + f"  [!] WHOIS       : {whois_data['error']}")

    print()
    print(Fore.CYAN + "  ── Plattform-Scan ──────────────────────────────\n")

    # ── Proxy-Verwaltung (automatisch oder manuell) ───────────────────────────
    proxies = []
    no_proxy = os.environ.get("NO_AUTO_PROXY", "0") == "1"

    if proxy_file:
        proxies = load_proxies(proxy_file)
        print(Fore.BLUE + f"  [*] {len(proxies)} Proxies aus Datei geladen\n")
    elif no_proxy:
        print(Fore.YELLOW + "  [*] Scan ohne Proxies\n")
    else:
        print(Fore.BLUE + "  [*] Lade automatische Proxies...")
        raw = await fetch_auto_proxies(limit=60)
        if raw:
            print(Fore.BLUE + f"  [*] {len(raw)} Proxies gefunden — teste auf Funktion...")
            proxies = await get_working_proxies(raw, needed=10)
            if proxies:
                print(Fore.GREEN + f"  [✔] {len(proxies)} funktionierende Proxies bereit\n")
            else:
                print(Fore.YELLOW + "  [!] Keine Proxies funktionieren — scan läuft ohne Proxies\n")
        else:
            print(Fore.YELLOW + "  [!] Proxies nicht erreichbar — scan läuft ohne Proxies\n")

    results = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=25)) as s:
        tasks = [
            check_platform(s, p, email, pick_proxy(proxies, i), timeout)
            for i, p in enumerate(PLATFORMS)
        ]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            if r["error"]:
                if verbose:
                    print(Fore.RED + f"  [!] {r['name']:<22} → {r['error']}")
            elif r["found"]:
                uname = f" → {Fore.YELLOW}@{r['username']}" if r.get("username") else ""
                print(Fore.GREEN + f"  [✔] {r['name']:<22} " +
                      Fore.CYAN  + f"({r['category']}){uname}")
            elif verbose:
                print(Fore.RED + f"  [✗] {r['name']:<22} → nicht registriert")

    # ── Zusammenfassung ───────────────────────────────────────────────────────
    found  = [r for r in results if r["found"]]
    errors = [r for r in results if r["error"]]

    print()
    print(Fore.YELLOW + "  " + "─" * 46)
    print(Fore.GREEN  + f"  Accounts gefunden : {len(found)}")
    print(Fore.RED    + f"  Fehler/Timeouts   : {len(errors)}")
    print(Fore.YELLOW + "  " + "─" * 46)

    if found:
        print(Fore.GREEN + "\n  Registriert auf:")
        for r in sorted(found, key=lambda x: x["category"]):
            uname = f"  (@{r['username']})" if r.get("username") else ""
            print(f"    • {r['name']:<22} [{r['category']}]{uname}")

    # ── Exports ───────────────────────────────────────────────────────────────
    if output_json:
        with open(output_json, "w") as f:
            json.dump({
                "email": email,
                "scanned_at": datetime.now().isoformat(),
                "provider": provider,
                "mx": mx,
                "whois": whois_data,
                "found": [{"name": r["name"], "category": r["category"],
                           "username": r.get("username")} for r in found],
            }, f, indent=2, ensure_ascii=False)
        print(Fore.YELLOW + f"\n  [*] JSON gespeichert : {output_json}")

    if output_html:
        save_html(email, found, mx, whois_data, provider, output_html)
        print(Fore.YELLOW + f"  [*] HTML gespeichert : {output_html}")

    print()

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="emailsint — Plattformen + MX + WHOIS + Provider"
    )
    ap.add_argument("email",              help="Zu prüfende E-Mail-Adresse")
    ap.add_argument("-p", "--proxies",    help="Proxy-Datei (eine pro Zeile)", default=None)
    ap.add_argument("-t", "--timeout",    help="Timeout in Sekunden (Standard: 12)", type=int, default=12)
    ap.add_argument("-o", "--output",     help="JSON-Report speichern", default=None)
    ap.add_argument("--html",             help="HTML-Report speichern", default=None)
    ap.add_argument("-v", "--verbose",    help="Auch nicht gefundene zeigen", action="store_true")
    args = ap.parse_args()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", args.email):
        print(Fore.RED + "[!] Ungültige E-Mail-Adresse.")
        sys.exit(1)

    asyncio.run(run(args.email, args.proxies, args.timeout, args.output, args.html, args.verbose))

if __name__ == "__main__":
    main()
