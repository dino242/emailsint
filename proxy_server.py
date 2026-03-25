#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import web
import subprocess
import sys
import os
import json
import re
import time
import threading

NGROK_TOKEN = os.environ.get("NGROK_TOKEN", "")
PROXY_PORT  = int(os.environ.get("PROXY_PORT", "8888"))
AUTH_TOKEN  = os.environ.get("PROXY_AUTH", "emailsint2024")

PUBLIC_URL  = ""
START_TIME  = time.time()
REQUEST_COUNT = 0

async def handle_proxy(request: web.Request) -> web.Response:
    global REQUEST_COUNT

    auth = request.headers.get("X-Proxy-Auth", "")
    if auth != AUTH_TOKEN:
        return web.Response(status=403, text="Forbidden")

    target_url = request.headers.get("X-Target-URL", "")
    if not target_url:
        target_url = str(request.url).replace(
            str(request.url.origin()), ""
        ).lstrip("/")

    if not target_url.startswith("http"):
        return web.Response(status=400, text="Bad target URL")

    method  = request.method
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ("host", "x-proxy-auth", "x-target-url",
                              "x-forwarded-for", "x-real-ip"):
            headers[k] = v

    headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    body = await request.read()

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, target_url,
                headers=headers,
                data=body if body else None,
                timeout=timeout,
                ssl=False,
                allow_redirects=True,
            ) as resp:
                REQUEST_COUNT += 1
                response_body    = await resp.read()
                response_headers = dict(resp.headers)
                for h in ("Transfer-Encoding", "Content-Encoding",
                          "Connection", "Keep-Alive"):
                    response_headers.pop(h, None)

                return web.Response(
                    status=resp.status,
                    body=response_body,
                    headers=response_headers,
                )
    except asyncio.TimeoutError:
        return web.Response(status=504, text="Upstream timeout")
    except Exception as e:
        return web.Response(status=502, text=f"Proxy error: {e}")


async def handle_status(request: web.Request) -> web.Response:
    uptime = int(time.time() - START_TIME)
    data = {
        "status":        "online",
        "public_url":    PUBLIC_URL,
        "uptime_seconds": uptime,
        "requests":      REQUEST_COUNT,
        "auth_required": True,
    }
    return web.json_response(data)


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


def install_ngrok():
    if subprocess.run(["which", "ngrok"], capture_output=True).returncode == 0:
        return True
    print("  [*] Installing ngrok...")
    try:
        subprocess.run([
            "curl", "-sSL",
            "https://ngrok-agent.s3.amazonaws.com/ngrok.asc",
            "-o", "/tmp/ngrok.asc"
        ], check=True)
        subprocess.run([
            "sudo", "tee", "/etc/apt/trusted.gpg.d/ngrok.asc"
        ], stdin=open("/tmp/ngrok.asc", "rb"), check=True,
           capture_output=True)
        subprocess.run([
            "echo", "deb https://ngrok-agent.s3.amazonaws.com buster main"
        ], check=True, capture_output=True)

        result = subprocess.run([
            "curl", "-sSL",
            "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz",
            "-o", "/tmp/ngrok.tgz"
        ], capture_output=True)
        subprocess.run(["tar", "-xzf", "/tmp/ngrok.tgz", "-C", "/usr/local/bin/"],
                       check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"  [!] Could not install ngrok: {e}")
        return False


def start_ngrok(token: str, port: int) -> str:
    global PUBLIC_URL

    if not install_ngrok():
        return ""

    subprocess.run(["ngrok", "config", "add-authtoken", token],
                   capture_output=True)

    subprocess.Popen(
        ["ngrok", "http", str(port), "--log=stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("  [*] Waiting for ngrok tunnel...")
    for _ in range(20):
        time.sleep(1)
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=3)
            data = json.loads(resp.read())
            tunnels = data.get("tunnels", [])
            if tunnels:
                PUBLIC_URL = tunnels[0]["public_url"]
                return PUBLIC_URL
        except Exception:
            continue

    return ""


def main():
    global NGROK_TOKEN

    if not NGROK_TOKEN:
        print("\n  emailsint — Proxy Server\n")
        NGROK_TOKEN = input("  Enter your ngrok authtoken: ").strip()
        if not NGROK_TOKEN:
            print("  [!] No token provided. Exiting.")
            sys.exit(1)

    print(f"\n  [*] Starting proxy server on port {PROXY_PORT}...")

    url = start_ngrok(NGROK_TOKEN, PROXY_PORT)
    if url:
        print(f"  [✔] Ngrok tunnel active: {url}")
        print(f"  [✔] Proxy URL for emailsint: {url}")
        print(f"  [✔] Auth token: {AUTH_TOKEN}")
        print(f"\n  Set in emailsint:")
        print(f"    PROXY_URL={url}")
        print(f"    PROXY_AUTH={AUTH_TOKEN}\n")
    else:
        print("  [!] Ngrok failed — running locally only")
        print(f"  [*] Local proxy: http://localhost:{PROXY_PORT}\n")

    app = web.Application()
    app.router.add_route("*",  "/proxy",   handle_proxy)
    app.router.add_get(        "/status",  handle_status)
    app.router.add_get(        "/health",  handle_health)
    app.router.add_route("*",  "/{path_info:.*}", handle_proxy)

    print(f"  [*] Proxy listening on port {PROXY_PORT}")
    print(f"  [*] Press Ctrl+C to stop\n")

    web.run_app(app, host="0.0.0.0", port=PROXY_PORT, print=lambda _: None)


if __name__ == "__main__":
    main()
