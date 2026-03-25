import asyncio
import aiohttp
import re
import os
import json
import time
import subprocess

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
]

NGROK_PROXY_URL  = os.environ.get("PROXY_URL",  "")
NGROK_PROXY_AUTH = os.environ.get("PROXY_AUTH", "emailsint2024")


def load_from_file(path: str) -> list:
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def pick(proxies: list, index: int):
    return proxies[index % len(proxies)] if proxies else None


async def fetch_public_proxies(limit: int = 100) -> list:
    proxies = []
    try:
        async with aiohttp.ClientSession() as session:
            for source in PROXY_SOURCES:
                try:
                    async with session.get(
                        source,
                        timeout=aiohttp.ClientTimeout(total=8),
                        ssl=False,
                    ) as r:
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
    return list(dict.fromkeys(proxies))[:limit]


async def _test_one(session: aiohttp.ClientSession, proxy: str) -> tuple:
    try:
        async with session.get(
            "http://httpbin.org/ip",
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=5),
            ssl=False,
        ) as r:
            return proxy, r.status == 200
    except Exception:
        return proxy, False


async def test_proxies(proxies: list, needed: int = 10) -> list:
    working = []
    sem = asyncio.Semaphore(40)

    async def guarded(p):
        async with sem:
            async with aiohttp.ClientSession() as s:
                return await _test_one(s, p)

    results = await asyncio.gather(*[guarded(p) for p in proxies[:needed * 6]])
    for proxy, ok in results:
        if ok:
            working.append(proxy)
        if len(working) >= needed:
            break
    return working


def build_ngrok_proxy_list(ngrok_url: str, auth: str) -> list:
    if not ngrok_url:
        return []
    url = ngrok_url.rstrip("/")
    return [f"{url}|{auth}"]


def is_ngrok_proxy(proxy_entry: str) -> bool:
    return "|" in proxy_entry


def get_ngrok_headers(proxy_entry: str) -> tuple:
    parts = proxy_entry.split("|", 1)
    url   = parts[0]
    auth  = parts[1] if len(parts) > 1 else ""
    return url, auth


async def resolve_proxies(proxy_file: str = None, use_ngrok: bool = True,
                          auto: bool = True) -> list:
    if proxy_file:
        proxies = load_from_file(proxy_file)
        return proxies

    if use_ngrok and NGROK_PROXY_URL:
        return build_ngrok_proxy_list(NGROK_PROXY_URL, NGROK_PROXY_AUTH)

    if auto:
        raw = await fetch_public_proxies(limit=100)
        if raw:
            working = await test_proxies(raw, needed=12)
            return working

    return []
