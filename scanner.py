import asyncio
import aiohttp
import re
from proxy_manager import pick, is_ngrok_proxy, get_ngrok_headers


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def _request_via_ngrok(session: aiohttp.ClientSession,
                              ngrok_entry: str,
                              method: str,
                              target_url: str,
                              headers: dict,
                              body,
                              timeout: int) -> tuple:
    proxy_url, auth_token = get_ngrok_headers(ngrok_entry)
    req_headers = dict(headers)
    req_headers["X-Proxy-Auth"]   = auth_token
    req_headers["X-Target-URL"]   = target_url
    req_headers["User-Agent"]     = UA

    endpoint = f"{proxy_url}/proxy"
    kw = dict(
        headers=req_headers,
        timeout=aiohttp.ClientTimeout(total=timeout + 5),
        ssl=False,
        allow_redirects=True,
    )
    if body:
        kw["data"] = body

    async with getattr(session, method)(endpoint, **kw) as resp:
        return resp.status, await resp.text(errors="ignore")


async def _request_direct(session: aiohttp.ClientSession,
                           proxy: str,
                           method: str,
                           url: str,
                           headers: dict,
                           body,
                           timeout: int) -> tuple:
    kw = dict(
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=timeout),
        ssl=False,
        allow_redirects=True,
    )
    if proxy:
        kw["proxy"] = proxy
    if body:
        kw["data"] = body

    async with getattr(session, method)(url, **kw) as resp:
        return resp.status, await resp.text(errors="ignore")


async def check_platform(session: aiohttp.ClientSession,
                         platform: dict,
                         email: str,
                         proxy,
                         timeout: int) -> dict:
    name = platform["name"]
    cat  = platform.get("category", "Other")
    try:
        url     = platform["url_fn"](email)
        method  = platform.get("method", "GET").lower()
        headers = {
            "User-Agent":      UA,
            "Accept-Language": "en-US,en;q=0.9",
            **platform.get("headers", {}),
        }
        data_fn = platform.get("data")
        body    = data_fn(email) if data_fn else None

        if proxy and is_ngrok_proxy(proxy):
            status, text = await _request_via_ngrok(
                session, proxy, method, url, headers, body, timeout
            )
        else:
            status, text = await _request_direct(
                session, proxy, method, url, headers, body, timeout
            )

        check = platform.get("check", "status_ok")
        found = False

        if check == "status_ok":
            found = status in platform.get("ok_status", [200])
        elif check == "keyword_found":
            found = platform["keyword"] in text
        elif check == "keyword_missing":
            found = platform["keyword"] not in text and status < 500

        username = None
        if found and platform.get("username_re"):
            m = re.search(platform["username_re"], text)
            if m:
                username = m.group(1)

        return {
            "name": name, "category": cat,
            "found": found, "username": username, "error": None,
        }

    except asyncio.TimeoutError:
        return {"name": name, "category": cat,
                "found": False, "username": None, "error": "Timeout"}
    except Exception as ex:
        return {"name": name, "category": cat,
                "found": False, "username": None, "error": str(ex)[:70]}


async def run_scan(platforms: list, email: str,
                   proxies: list, timeout: int,
                   on_result=None) -> list:
    results = []
    connector = aiohttp.TCPConnector(ssl=False, limit=35)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            check_platform(session, p, email, pick(proxies, i), timeout)
            for i, p in enumerate(platforms)
        ]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            if on_result:
                on_result(r)
    return results
