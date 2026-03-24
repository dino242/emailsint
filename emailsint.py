#!/usr/bin/env python3
"""
emailsint v3.0 — Email OSINT Tool
No external API keys needed. Pure scraping + DNS + OSINT enrichment.
"""

import asyncio
import aiohttp
import argparse
import hashlib
import json
import re
import sys
import os
import subprocess
import socket
from urllib.parse import quote
from datetime import datetime
from colorama import Fore, Style, init

# ── Optional imports — no crash if missing ────────────────
try:
    import dns.resolver as dns_resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    import whois as whois_lib
    HAS_WHOIS = True
except ImportError:
    try:
        import python_whois as whois_lib
        HAS_WHOIS = True
    except ImportError:
        HAS_WHOIS = False

init(autoreset=True)

BANNER = r"""
  ___ __  __   _   ___ _    ___ ___ _  _ _____
 | __|  \/  | /_\ |_ _| |  / __| __| \| |_   _|
 | _|| |\/| |/ _ \ | || |__\__ \ _|| .` | | |
 |___|_|  |_/_/ \_\___|____|___/___|_|\_| |_|
  v3.0 — Email OSINT Tool
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────

def md5(s: str) -> str:
    return hashlib.md5(s.strip().lower().encode()).hexdigest()

def sha256(s: str) -> str:
    return hashlib.sha256(s.strip().lower().encode()).hexdigest()

def get_username(email: str) -> str:
    return email.split("@")[0]

def get_domain(email: str) -> str:
    return email.split("@")[-1].lower()

# ─── Provider detection ───────────────────────────────────────────────────────

PROVIDER_MAP = {
    "gmail.com":      "Google Gmail",
    "googlemail.com": "Google Gmail",
    "outlook.com":    "Microsoft Outlook",
    "hotmail.com":    "Microsoft Hotmail",
    "live.com":       "Microsoft Live",
    "msn.com":        "Microsoft MSN",
    "yahoo.com":      "Yahoo Mail",
    "yahoo.de":       "Yahoo Mail",
    "yahoo.co.uk":    "Yahoo Mail",
    "icloud.com":     "Apple iCloud",
    "me.com":         "Apple iCloud",
    "mac.com":        "Apple iCloud",
    "protonmail.com": "ProtonMail",
    "proton.me":      "ProtonMail",
    "tutanota.com":   "Tutanota",
    "tuta.io":        "Tutanota",
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
    "mail.ru":        "Mail.ru",
    "fastmail.com":   "Fastmail",
    "hey.com":        "HEY Email",
    "pm.me":          "ProtonMail",
}

def get_provider(email: str) -> str:
    domain = get_domain(email)
    return PROVIDER_MAP.get(domain, f"Custom / Unknown ({domain})")

# ─── MX Check ────────────────────────────────────────────────────────────────

def check_mx(email: str) -> dict:
    domain = get_domain(email)
    if not HAS_DNS:
        try:
            result = subprocess.run(
                ["nslookup", "-type=MX", domain],
                capture_output=True, text=True, timeout=8
            )
            found = "mail exchanger" in result.stdout.lower()
            return {"valid": found, "mx_records": [], "primary_mx": domain if found else ""}
        except Exception:
            return {"valid": False, "mx_records": [], "primary_mx": ""}
    try:
        records = dns_resolver.resolve(domain, "MX")
        mx_list = sorted(records, key=lambda r: r.preference)
        return {
            "valid": True,
            "mx_records": [str(r.exchange).rstrip(".") for r in mx_list],
            "primary_mx": str(mx_list[0].exchange).rstrip("."),
        }
    except Exception as e:
        return {"valid": False, "mx_records": [], "primary_mx": "", "error": str(e)}

# ─── WHOIS ────────────────────────────────────────────────────────────────────

def check_whois(email: str) -> dict:
    domain = get_domain(email)
    if not HAS_WHOIS:
        try:
            result = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=10)
            text = result.stdout
            created = ""
            registrar = ""
            for line in text.splitlines():
                ll = line.lower()
                if ("creation date" in ll or "created:" in ll) and not created:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        created = parts[1].strip()[:10]
                if "registrar:" in ll and not registrar:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        registrar = parts[1].strip()[:40]
            return {
                "domain": domain,
                "registrar": registrar or "Unknown",
                "created": created or "Unknown",
                "updated": "Unknown",
                "country": "Unknown",
            }
        except Exception as e:
            return {"domain": domain, "error": str(e)}
    try:
        w = whois_lib.whois(domain)
        created = w.creation_date
        if isinstance(created, list): created = created[0]
        updated = w.updated_date
        if isinstance(updated, list): updated = updated[0]
        return {
            "domain":    domain,
            "registrar": str(w.registrar or "Unknown")[:60],
            "created":   str(created)[:10] if created else "Unknown",
            "updated":   str(updated)[:10] if updated else "Unknown",
            "country":   str(w.country  or "Unknown"),
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}

# ─── Gravatar deep OSINT ──────────────────────────────────────────────────────

async def gravatar_osint(session, email: str) -> dict:
    """Fetch full Gravatar profile — name, bio, accounts, avatar, location."""
    result = {"found": False}
    try:
        url = f"https://www.gravatar.com/{md5(email)}.json"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), ssl=False) as r:
            if r.status == 200:
                data = await r.json()
                entry = data.get("entry", [{}])[0]
                result["found"]       = True
                result["username"]    = entry.get("preferredUsername", "")
                result["displayName"] = entry.get("displayName", "")
                result["location"]    = entry.get("currentLocation", "")
                result["bio"]         = entry.get("aboutMe", "")
                result["avatar"]      = f"https://www.gravatar.com/avatar/{md5(email)}"
                result["profile_url"] = f"https://www.gravatar.com/{md5(email)}"
                # Linked accounts
                accounts = entry.get("accounts", [])
                result["linked_accounts"] = [
                    {"domain": a.get("domain",""), "username": a.get("username","")}
                    for a in accounts
                ]
                urls = entry.get("urls", [])
                result["urls"] = [u.get("value","") for u in urls if u.get("value")]
    except Exception:
        pass
    return result

# ─── Auto proxy system ───────────────────────────────────────────────────────

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
]

async def fetch_auto_proxies(limit: int = 80) -> list:
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
    return list(dict.fromkeys(proxies))[:limit]  # deduplicate

async def test_proxy(session, proxy: str) -> bool:
    try:
        async with session.get(
            "http://httpbin.org/ip", proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=5), ssl=False,
        ) as r:
            return r.status == 200
    except Exception:
        return False

async def get_working_proxies(proxies: list, needed: int = 10) -> list:
    working = []
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(30)
        async def guarded(p):
            async with sem:
                return p, await test_proxy(session, p)
        results = await asyncio.gather(*[guarded(p) for p in proxies[:needed * 5]])
        for proxy, ok in results:
            if ok:
                working.append(proxy)
            if len(working) >= needed:
                break
    return working

def load_proxies(path: str) -> list:
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def pick_proxy(proxies: list, i: int):
    return proxies[i % len(proxies)] if proxies else None

# ─── Platform definitions ────────────────────────────────────────────────────
# check types:
#   keyword_found   → response contains keyword       → registered
#   keyword_missing → response does NOT contain kw    → registered
#   status_ok       → HTTP status in ok_status        → registered
#
# username_re → regex to scrape username from response

PLATFORMS = [

    # ══ Tech & Dev ═══════════════════════════════════════════════════════════
    {
        "name": "GitHub",
        "category": "Tech",
        "method": "POST",
        "url_fn": lambda e: "https://github.com/account/password_reset",
        "headers": {"Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://github.com/password_reset"},
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
        "name": "Bitbucket",
        "category": "Tech",
        "method": "GET",
        "url_fn": lambda e: f"https://bitbucket.org/account/signin/?next=/",
        "data": lambda e: f"username={e}",
        "check": "keyword_missing",
        "keyword": "No account found",
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
    {
        "name": "Codecademy",
        "category": "Tech",
        "method": "GET",
        "url_fn": lambda e: f"https://www.codecademy.com/api/v1/registration_validations?user%5Bemail%5D={e}",
        "check": "keyword_found",
        "keyword": '"taken":true',
    },
    {
        "name": "HackerNews",
        "category": "Tech",
        "method": "GET",
        "url_fn": lambda e: f"https://hacker-news.firebaseio.com/v0/user/{get_username(e)}.json",
        "check": "keyword_found",
        "keyword": '"id"',
        "username_re": r'"id"\s*:\s*"([^"]+)"',
    },

    # ══ Social ════════════════════════════════════════════════════════════════
    {
        "name": "Twitter / X",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://x.com/i/flow/password_reset",
        "headers": {"Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://x.com/"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "We couldn't find",
    },
    {
        "name": "Instagram",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://www.instagram.com/accounts/account_recovery_send_ajax/",
        "headers": {"Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://www.instagram.com/"},
        "data": lambda e: f"email_or_username={e}",
        "check": "keyword_found",
        "keyword": "email_found",
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
    {
        "name": "Foursquare",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://foursquare.com/forgot_password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "We couldn't find",
    },
    {
        "name": "Quora",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://www.quora.com/",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "We couldn't find",
    },
    {
        "name": "Meetup",
        "category": "Social",
        "method": "POST",
        "url_fn": lambda e: "https://secure.meetup.com/forgot_password/",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "not found",
    },

    # ══ Professional ══════════════════════════════════════════════════════════
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
    {
        "name": "Upwork",
        "category": "Professional",
        "method": "POST",
        "url_fn": lambda e: "https://www.upwork.com/ab/account-security/forgot-password",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"login": e}),
        "check": "keyword_missing",
        "keyword": "No account",
    },

    # ══ Gaming ════════════════════════════════════════════════════════════════
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
        "headers": {"Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://store.steampowered.com/join/"},
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
    {
        "name": "Ubisoft",
        "category": "Gaming",
        "method": "POST",
        "url_fn": lambda e: "https://account.ubisoft.com/api/users/forgot-password",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"nameOnPlatform": e, "platformType": "uplay"}),
        "check": "keyword_missing",
        "keyword": "accountNotFound",
    },
    {
        "name": "EA / Origin",
        "category": "Gaming",
        "method": "GET",
        "url_fn": lambda e: f"https://signin.ea.com/p/ajax/user/checkEmailStatus?email={e}",
        "check": "keyword_found",
        "keyword": '"status":"EXISTS"',
    },

    # ══ Music / Media ═════════════════════════════════════════════════════════
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
    {
        "name": "Last.fm",
        "category": "Music",
        "method": "POST",
        "url_fn": lambda e: "https://www.last.fm/user/forgotpassword",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"username_or_email={e}",
        "check": "keyword_missing",
        "keyword": "We couldn't find",
    },
    {
        "name": "Deezer",
        "category": "Music",
        "method": "POST",
        "url_fn": lambda e: "https://www.deezer.com/ajax/action.php",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"method=User.checkEmail&mail={e}",
        "check": "keyword_found",
        "keyword": '"ALREADY_USED"',
    },

    # ══ Communication ═════════════════════════════════════════════════════════
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
        "name": "Skype",
        "category": "Communication",
        "method": "POST",
        "url_fn": lambda e: "https://login.live.com/GetCredentialType.srf",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"username": e}),
        "check": "keyword_found",
        "keyword": '"IfExistsResult":0',
    },
    {
        "name": "Zoom",
        "category": "Communication",
        "method": "POST",
        "url_fn": lambda e: "https://zoom.us/forgot_password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "did not find",
    },
    {
        "name": "Slack",
        "category": "Communication",
        "method": "POST",
        "url_fn": lambda e: "https://slack.com/forgot",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "not found",
    },

    # ══ Cloud / Productivity ══════════════════════════════════════════════════
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
    {
        "name": "Trello",
        "category": "Productivity",
        "method": "GET",
        "url_fn": lambda e: f"https://trello.com/1/auth/forgot/?email={e}",
        "check": "keyword_missing",
        "keyword": "not found",
    },

    # ══ Finance ═══════════════════════════════════════════════════════════════
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
    {
        "name": "Coinbase",
        "category": "Finance",
        "method": "POST",
        "url_fn": lambda e: "https://www.coinbase.com/forgot-password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "No account",
    },
    {
        "name": "Binance",
        "category": "Finance",
        "method": "POST",
        "url_fn": lambda e: "https://accounts.binance.com/en/forgot-password",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "User not found",
    },

    # ══ Creative ══════════════════════════════════════════════════════════════
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
    {
        "name": "Canva",
        "category": "Creative",
        "method": "POST",
        "url_fn": lambda e: "https://www.canva.com/_ajax/auth/check-email",
        "headers": {"Content-Type": "application/json"},
        "data": lambda e: json.dumps({"email": e}),
        "check": "keyword_found",
        "keyword": '"exists":true',
    },
    {
        "name": "500px",
        "category": "Creative",
        "method": "GET",
        "url_fn": lambda e: f"https://api.500px.com/v1/users/check_email_uniqueness?email={e}",
        "check": "keyword_found",
        "keyword": '"taken":true',
    },

    # ══ Shopping ══════════════════════════════════════════════════════════════
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
        "url_fn": lambda e: "https://reg.ebay.de/reg/PartialRegistration?siteid=77",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"Email={e}&js_check=1",
        "check": "keyword_missing",
        "keyword": "no account",
    },
    {
        "name": "Amazon",
        "category": "Shopping",
        "method": "POST",
        "url_fn": lambda e: "https://www.amazon.com/ap/forgotpassword/reverification",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda e: f"email={e}",
        "check": "keyword_missing",
        "keyword": "No account found",
    },
]

# ─── Single platform check ───────────────────────────────────────────────────

async def check_platform(session, p: dict, email: str, proxy, timeout: int) -> dict:
    name = p["name"]
    cat  = p.get("category", "Other")
    try:
        url    = p["url_fn"](email)
        method = p.get("method", "GET").lower()
        hdrs   = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
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

            username = None
            if found and p.get("username_re"):
                m = re.search(p["username_re"], text)
                if m:
                    username = m.group(1)

            return {"name": name, "category": cat,
                    "found": found, "username": username, "error": None}

    except asyncio.TimeoutError:
        return {"name": name, "category": cat, "found": False, "username": None, "error": "Timeout"}
    except Exception as ex:
        return {"name": name, "category": cat, "found": False, "username": None, "error": str(ex)[:60]}

# ─── HTML report ─────────────────────────────────────────────────────────────

def save_html(email, found, mx, whois_data, provider, gravatar, path):
    g_section = ""
    if gravatar.get("found"):
        linked = ""
        for acc in gravatar.get("linked_accounts", []):
            linked += f'<span class="tag">{acc["domain"]}</span> '
        urls = " ".join(f'<a href="{u}" target="_blank">{u}</a>' for u in gravatar.get("urls", []))
        g_section = f"""
        <div class="card" style="grid-column:1/-1">
          <div class="label">Gravatar Profile</div>
          <div class="value">
            <img src="{gravatar.get('avatar','')}" style="border-radius:50%;width:60px;float:left;margin-right:12px">
            <strong>{gravatar.get('displayName','')}</strong>
            {'<br><small>' + gravatar.get('location','') + '</small>' if gravatar.get('location') else ''}
            {'<br><small>' + gravatar.get('bio','') + '</small>' if gravatar.get('bio') else ''}
            {'<br>Linked: ' + linked if linked else ''}
            {'<br>' + urls if urls else ''}
          </div>
        </div>"""

    rows = "".join(
        f'<tr><td>{r["name"]}</td><td><span class="tag">{r["category"]}</span></td>'
        f'<td>{"<b>@"+r["username"]+"</b>" if r.get("username") else "—"}</td></tr>'
        for r in sorted(found, key=lambda x: x["category"])
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>emailsint — {email}</title>
<style>
  *{{box-sizing:border-box}} body{{font-family:'Courier New',monospace;background:#0d1117;color:#c9d1d9;margin:0;padding:40px}}
  h1{{color:#58a6ff;margin-bottom:4px}} h2{{color:#79c0ff;border-bottom:1px solid #30363d;padding-bottom:6px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:32px}}
  .card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}}
  .label{{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
  .value{{color:#e6edf3;font-size:14px;font-weight:bold;margin-top:6px}}
  .tag{{background:#21262d;border:1px solid #30363d;border-radius:4px;padding:2px 8px;font-size:11px;color:#8b949e}}
  table{{width:100%;border-collapse:collapse}} th{{background:#161b22;color:#8b949e;text-align:left;padding:10px;font-size:12px}}
  td{{padding:10px;border-bottom:1px solid #21262d;font-size:13px}} tr:hover td{{background:#161b22}}
  a{{color:#58a6ff}} .badge{{color:#3fb950;font-weight:bold}}
</style></head><body>
<h1>📧 emailsint Report</h1>
<p style="color:#8b949e">Email: <strong style="color:#e6edf3">{email}</strong> &nbsp;·&nbsp; Scanned: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

<h2>Email Analysis</h2>
<div class="grid">
  <div class="card"><div class="label">Provider</div><div class="value">{provider}</div></div>
  <div class="card"><div class="label">MX Record</div><div class="value {'badge' if mx.get('valid') else ''}">{('✔ ' + mx.get('primary_mx','')) if mx.get('valid') else '✘ No MX found'}</div></div>
  <div class="card"><div class="label">Domain registered</div><div class="value">{whois_data.get('created','Unknown')}</div></div>
  <div class="card"><div class="label">Registrar</div><div class="value">{whois_data.get('registrar','Unknown')}</div></div>
  {g_section}
</div>

<h2>Found Accounts ({len(found)})</h2>
<table>
  <tr><th>Platform</th><th>Category</th><th>Username</th></tr>
  {rows or '<tr><td colspan="3" style="color:#8b949e">No accounts found.</td></tr>'}
</table>
<p style="color:#8b949e;font-size:11px;margin-top:40px">Generated by emailsint v3.0 — for personal use only.</p>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

# ─── Main scan ───────────────────────────────────────────────────────────────

async def run(email: str, proxy_file=None, timeout: int = 12,
              output_json=None, output_html=None, verbose: bool = False):

    print(Fore.CYAN + BANNER)
    print(Fore.YELLOW + f"  [*] Email       : {email}")
    print(Fore.YELLOW + f"  [*] Username    : {get_username(email)}")
    print(Fore.YELLOW + f"  [*] Domain      : {get_domain(email)}")
    print(Fore.YELLOW + f"  [*] Platforms   : {len(PLATFORMS)}")
    print(Fore.YELLOW + f"  [*] Started     : {datetime.now().strftime('%H:%M:%S')}\n")

    # ── Email analysis ────────────────────────────────────────────────────────
    print(Fore.CYAN + "  ── Email Analysis ─────────────────────────────")
    provider = get_provider(email)
    print(Fore.WHITE + f"  [i] Provider  : {Fore.CYAN}{provider}")

    mx = check_mx(email)
    if mx.get("valid"):
        print(Fore.GREEN + f"  [✔] MX Record : {mx['primary_mx']}")
    else:
        print(Fore.RED   + f"  [✘] MX Record : not reachable")

    whois_data = check_whois(email)
    if "error" not in whois_data:
        print(Fore.WHITE + f"  [i] Domain reg: {Fore.CYAN}{whois_data['created']}")
        print(Fore.WHITE + f"  [i] Registrar : {Fore.CYAN}{whois_data['registrar']}")
    else:
        print(Fore.RED   + f"  [!] WHOIS     : {whois_data.get('error','failed')}")

    print()
    print(Fore.CYAN + "  ── Gravatar OSINT ─────────────────────────────")

    # ── Gravatar deep scan ────────────────────────────────────────────────────
    gravatar = {}
    async with aiohttp.ClientSession() as s:
        gravatar = await gravatar_osint(s, email)

    if gravatar.get("found"):
        print(Fore.GREEN + f"  [✔] Profile found!")
        if gravatar.get("displayName"):
            print(Fore.WHITE + f"  [i] Name      : {Fore.YELLOW}{gravatar['displayName']}")
        if gravatar.get("username"):
            print(Fore.WHITE + f"  [i] Username  : {Fore.YELLOW}@{gravatar['username']}")
        if gravatar.get("location"):
            print(Fore.WHITE + f"  [i] Location  : {Fore.CYAN}{gravatar['location']}")
        if gravatar.get("bio"):
            bio = gravatar["bio"][:80] + ("..." if len(gravatar["bio"]) > 80 else "")
            print(Fore.WHITE + f"  [i] Bio       : {Fore.CYAN}{bio}")
        if gravatar.get("linked_accounts"):
            accs = ", ".join(a["domain"] for a in gravatar["linked_accounts"])
            print(Fore.WHITE + f"  [i] Linked    : {Fore.CYAN}{accs}")
        if gravatar.get("urls"):
            for url in gravatar["urls"][:3]:
                print(Fore.WHITE + f"  [i] URL       : {Fore.CYAN}{url}")
        print(Fore.WHITE + f"  [i] Avatar    : {Fore.CYAN}https://www.gravatar.com/avatar/{md5(email)}")
    else:
        print(Fore.RED + "  [✘] No Gravatar profile found")

    print()
    print(Fore.CYAN + "  ── Platform Scan ──────────────────────────────\n")

    # ── Proxies ───────────────────────────────────────────────────────────────
    proxies = []
    no_proxy = os.environ.get("NO_AUTO_PROXY", "0") == "1"
    if proxy_file:
        proxies = load_proxies(proxy_file)
        print(Fore.BLUE + f"  [*] {len(proxies)} proxies loaded from file\n")
    elif not no_proxy:
        print(Fore.BLUE + "  [*] Fetching automatic proxies...")
        raw = await fetch_auto_proxies(limit=80)
        if raw:
            print(Fore.BLUE + f"  [*] {len(raw)} found — testing...")
            proxies = await get_working_proxies(raw, needed=10)
            if proxies:
                print(Fore.GREEN + f"  [✔] {len(proxies)} working proxies ready\n")
            else:
                print(Fore.YELLOW + "  [!] No working proxies — running without\n")
        else:
            print(Fore.YELLOW + "  [!] Proxy sources unreachable — running without\n")

    # ── Scan ─────────────────────────────────────────────────────────────────
    results = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=30)) as s:
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
                print(Fore.GREEN + f"  [✔] {r['name']:<22} {Fore.CYAN}({r['category']}){uname}")
            elif verbose:
                print(Fore.RED + f"  [✗] {r['name']:<22} → not found")

    # ── Summary ───────────────────────────────────────────────────────────────
    found  = [r for r in results if r["found"]]
    errors = [r for r in results if r["error"]]

    print()
    print(Fore.YELLOW + "  " + "─" * 48)
    print(Fore.GREEN  + f"  Accounts found  : {len(found)}")
    print(Fore.RED    + f"  Errors/Timeouts : {len(errors)}")
    print(Fore.YELLOW + "  " + "─" * 48)

    if found:
        print(Fore.GREEN + "\n  Registered on:")
        for r in sorted(found, key=lambda x: x["category"]):
            uname = f"  (@{r['username']})" if r.get("username") else ""
            print(f"    • {r['name']:<24} [{r['category']}]{uname}")

    # ── Exports ───────────────────────────────────────────────────────────────
    if output_json:
        with open(output_json, "w") as f:
            json.dump({
                "email": email,
                "username": get_username(email),
                "domain": get_domain(email),
                "scanned_at": datetime.now().isoformat(),
                "provider": provider,
                "mx": mx,
                "whois": whois_data,
                "gravatar": gravatar,
                "found": [{"name": r["name"], "category": r["category"],
                           "username": r.get("username")} for r in found],
            }, f, indent=2, ensure_ascii=False)
        print(Fore.YELLOW + f"\n  [*] JSON saved : {output_json}")

    if output_html:
        save_html(email, found, mx, whois_data, provider, gravatar, output_html)
        print(Fore.YELLOW + f"  [*] HTML saved : {output_html}")

    print()

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="emailsint v3.0 — Email OSINT Tool")
    ap.add_argument("email")
    ap.add_argument("-p", "--proxies", default=None, help="Proxy file (one per line)")
    ap.add_argument("-t", "--timeout", type=int, default=12, help="Request timeout in seconds")
    ap.add_argument("-o", "--output",  default=None, help="Save JSON report")
    ap.add_argument("--html",          default=None, help="Save HTML report")
    ap.add_argument("-v", "--verbose", action="store_true", help="Show not found platforms too")
    args = ap.parse_args()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", args.email):
        print(Fore.RED + "[!] Invalid email address.")
        sys.exit(1)

    asyncio.run(run(args.email, args.proxies, args.timeout, args.output, args.html, args.verbose))

if __name__ == "__main__":
    main()
