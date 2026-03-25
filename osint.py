import hashlib
import subprocess
import asyncio
import aiohttp
import re

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


def md5(s: str) -> str:
    return hashlib.md5(s.strip().lower().encode()).hexdigest()


def get_domain(email: str) -> str:
    return email.split("@")[-1].lower()


def get_username(email: str) -> str:
    return email.split("@")[0]


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
    "pm.me":          "ProtonMail",
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
}


def get_provider(email: str) -> str:
    domain = get_domain(email)
    return PROVIDER_MAP.get(domain, f"Custom / Unknown ({domain})")


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


def check_whois(email: str) -> dict:
    domain = get_domain(email)
    if not HAS_WHOIS:
        try:
            result = subprocess.run(
                ["whois", domain], capture_output=True, text=True, timeout=10
            )
            text = result.stdout
            created   = ""
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
                        registrar = parts[1].strip()[:60]
            return {
                "domain":    domain,
                "registrar": registrar or "Unknown",
                "created":   created   or "Unknown",
                "updated":   "Unknown",
                "country":   "Unknown",
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


async def gravatar_osint(session: aiohttp.ClientSession, email: str) -> dict:
    result = {"found": False}
    try:
        url = f"https://www.gravatar.com/{md5(email)}.json"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), ssl=False) as r:
            if r.status == 200:
                data  = await r.json()
                entry = data.get("entry", [{}])[0]
                result["found"]       = True
                result["username"]    = entry.get("preferredUsername", "")
                result["displayName"] = entry.get("displayName", "")
                result["location"]    = entry.get("currentLocation", "")
                result["bio"]         = entry.get("aboutMe", "")
                result["avatar"]      = f"https://www.gravatar.com/avatar/{md5(email)}"
                result["profile_url"] = f"https://www.gravatar.com/{md5(email)}"
                result["linked_accounts"] = [
                    {"domain": a.get("domain", ""), "username": a.get("username", "")}
                    for a in entry.get("accounts", [])
                ]
                result["urls"] = [
                    u.get("value", "") for u in entry.get("urls", []) if u.get("value")
                ]
    except Exception:
        pass
    return result
