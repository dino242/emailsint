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
import urllib.request

# ─── Config ───────────────────────────────────────────────────────────────────
PROXY_PORT  = int(os.environ.get("PROXY_PORT", "8888"))
AUTH_TOKEN  = os.environ.get("PROXY_AUTH", "emailsint2024")

PUBLIC_URL    = ""
START_TIME    = time.time()
REQUEST_COUNT = 0

# Scan results stored in memory for the dashboard
SCAN_RESULTS  = []
SCAN_EMAIL    = ""
SCAN_RUNNING  = False
SCAN_META     = {}   # provider, mx, whois, gravatar, started

# ─── HTML Dashboard ───────────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EmailSint — Scanner Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #0a0a0f;
    --surface:  #111118;
    --border:   #1e1e2e;
    --accent:   #7c6af7;
    --accent2:  #a78bfa;
    --found:    #22c55e;
    --notfound: #ef4444;
    --warn:     #f59e0b;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --mono:     'JetBrains Mono', monospace;
    --display:  'Syne', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--mono);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Animated grid background */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(124,106,247,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(124,106,247,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  .wrapper {
    position: relative;
    z-index: 1;
    max-width: 1100px;
    margin: 0 auto;
    padding: 32px 24px;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 36px;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .logo-icon {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    box-shadow: 0 0 24px rgba(124,106,247,0.4);
  }

  .logo-text {
    font-family: var(--display);
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
  }

  .logo-text span { color: var(--accent2); }

  .status-pill {
    display: flex; align-items: center; gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 8px 16px;
    font-size: 12px;
    color: var(--muted);
  }

  .pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--found);
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(34,197,94,0.5); }
    50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(34,197,94,0); }
  }

  /* ── Stats Row ── */
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
  }

  .stat-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    opacity: 0;
    transition: opacity 0.3s;
  }

  .stat-card:hover::after { opacity: 1; }

  .stat-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
  }

  .stat-value {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 800;
    line-height: 1;
  }

  .stat-value.green { color: var(--found); }
  .stat-value.red   { color: var(--notfound); }
  .stat-value.purple{ color: var(--accent2); }

  /* ── Email Banner ── */
  .email-banner {
    background: linear-gradient(135deg, rgba(124,106,247,0.12), rgba(167,139,250,0.06));
    border: 1px solid rgba(124,106,247,0.25);
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }

  .email-banner .label {
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    min-width: 60px;
  }

  .email-banner .address {
    color: var(--accent2);
    font-weight: 600;
    font-size: 15px;
  }

  .scanning-badge {
    margin-left: auto;
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.3);
    color: var(--warn);
    border-radius: 100px;
    padding: 4px 12px;
    font-size: 11px;
    display: flex; align-items: center; gap: 6px;
  }

  .spin {
    display: inline-block;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Results Table ── */
  .section-title {
    font-family: var(--display);
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--muted);
    margin-bottom: 16px;
  }

  .results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
  }

  .result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: transform 0.15s, border-color 0.15s;
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .result-card:hover {
    transform: translateY(-2px);
    border-color: rgba(124,106,247,0.3);
  }

  .result-card.found {
    border-left: 3px solid var(--found);
    background: linear-gradient(90deg, rgba(34,197,94,0.06), var(--surface));
  }

  .result-card.notfound {
    border-left: 3px solid rgba(239,68,68,0.4);
    opacity: 0.65;
  }

  .result-card.error {
    border-left: 3px solid rgba(245,158,11,0.4);
    opacity: 0.55;
  }

  .result-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .found .result-dot    { background: var(--found); box-shadow: 0 0 8px rgba(34,197,94,0.6); }
  .notfound .result-dot { background: var(--notfound); }
  .error .result-dot    { background: var(--warn); }

  .result-info { flex: 1; min-width: 0; }

  .result-name {
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-meta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 3px;
  }

  .result-badge {
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 100px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    flex-shrink: 0;
  }

  .found .result-badge {
    background: rgba(34,197,94,0.15);
    color: var(--found);
    border: 1px solid rgba(34,197,94,0.25);
  }

  .notfound .result-badge {
    background: rgba(239,68,68,0.1);
    color: var(--notfound);
    border: 1px solid rgba(239,68,68,0.2);
  }

  .error .result-badge {
    background: rgba(245,158,11,0.1);
    color: var(--warn);
    border: 1px solid rgba(245,158,11,0.2);
  }

  /* ── Empty State ── */
  .empty {
    text-align: center;
    padding: 80px 20px;
    color: var(--muted);
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.4;
  }

  .empty-text {
    font-family: var(--display);
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
    color: var(--text);
    opacity: 0.4;
  }

  .empty-sub { font-size: 13px; opacity: 0.5; }

  /* ── Footer ── */
  footer {
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--muted);
  }

  /* ── Refresh indicator ── */
  .refresh-bar {
    position: fixed;
    top: 0; left: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    animation: refreshProgress 5s linear infinite;
    z-index: 100;
  }

  @keyframes refreshProgress {
    from { width: 0%; opacity: 1; }
    90%  { width: 100%; opacity: 1; }
    to   { width: 100%; opacity: 0; }
  }
</style>
<meta http-equiv="refresh" content="5">
</head>
<body>
<div class="refresh-bar"></div>
<div class="wrapper">

  <header>
    <div class="logo">
      <div class="logo-icon">🔍</div>
      <div>
        <div class="logo-text">Email<span>Sint</span></div>
      </div>
    </div>
    <div class="status-pill">
      <div class="pulse"></div>
      Live Dashboard
    </div>
  </header>

  <div class="stats">
    <div class="stat-card">
      <div class="stat-label">Gesamt</div>
      <div class="stat-value purple">{{TOTAL}}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Gefunden</div>
      <div class="stat-value green">{{FOUND}}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Nicht gefunden</div>
      <div class="stat-value red">{{NOTFOUND}}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Fehler</div>
      <div class="stat-value" style="color:var(--warn)">{{ERRORS}}</div>
    </div>
  </div>

  {{EMAIL_BANNER}}

  <div class="section-title">Scan-Ergebnisse</div>

  {{RESULTS_BLOCK}}

</div>

<footer>
  <div>EmailSint Scanner Dashboard</div>
  <div>Auto-Refresh alle 5s · {{UPTIME}}s Laufzeit</div>
</footer>
</body>
</html>
"""

def build_dashboard() -> str:
    total    = len(SCAN_RESULTS)
    found    = sum(1 for r in SCAN_RESULTS if r.get("found"))
    errors   = sum(1 for r in SCAN_RESULTS if r.get("error"))
    notfound = total - found - errors
    uptime   = int(time.time() - START_TIME)

    # Email banner + meta info
    if SCAN_EMAIL:
        status_part = ""
        if SCAN_RUNNING:
            status_part = '<span class="scanning-badge"><span class="spin">⟳</span> Scanning…</span>'

        meta_rows = ""
        if SCAN_META:
            provider = SCAN_META.get("provider", "")
            mx       = SCAN_META.get("mx", {})
            whois    = SCAN_META.get("whois", {})
            gravatar = SCAN_META.get("gravatar", {})
            total_p  = SCAN_META.get("platforms", "")

            mx_val  = mx.get("primary_mx", "—") if mx.get("valid") else "✘ Nicht erreichbar"
            mx_col  = "#22c55e" if mx.get("valid") else "#ef4444"
            reg     = whois.get("created", "—") if "error" not in whois else "—"
            registrar = whois.get("registrar", "—") if "error" not in whois else "—"

            grav_block = ""
            if gravatar.get("found"):
                gname      = gravatar.get("displayName") or gravatar.get("username") or ""
                gloc       = gravatar.get("location", "")
                avatar_url = gravatar.get("avatar", "")
                loc_html   = ('<div style="font-size:12px;color:#64748b">📍 ' + gloc + '</div>') if gloc else ""
                grav_block = (
                    '<div style="display:flex;align-items:center;gap:10px;margin-top:12px;'
                    'padding:12px;background:rgba(124,106,247,0.08);'
                    'border:1px solid rgba(124,106,247,0.2);border-radius:8px">'
                    '<img src="' + avatar_url + '?s=48" '
                    'style="width:48px;height:48px;border-radius:50%;flex-shrink:0">'
                    '<div>'
                    '<div style="font-weight:600;color:#a78bfa">' + gname + '</div>'
                    + loc_html +
                    '<div style="font-size:11px;color:#64748b;margin-top:2px">Gravatar Profil gefunden ✔</div>'
                    '</div></div>'
                )

            meta_rows = (
                '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));'
                'gap:10px;margin-top:12px">'
                '<div style="background:rgba(255,255,255,0.03);border:1px solid #1e1e2e;'
                'border-radius:8px;padding:10px">'
                '<div style="font-size:10px;color:#64748b;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:4px">Provider</div>'
                '<div style="font-size:13px;font-weight:600">' + provider + '</div>'
                '</div>'
                '<div style="background:rgba(255,255,255,0.03);border:1px solid #1e1e2e;'
                'border-radius:8px;padding:10px">'
                '<div style="font-size:10px;color:#64748b;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:4px">MX Record</div>'
                '<div style="font-size:13px;font-weight:600;color:' + mx_col + '">' + mx_val + '</div>'
                '</div>'
                '<div style="background:rgba(255,255,255,0.03);border:1px solid #1e1e2e;'
                'border-radius:8px;padding:10px">'
                '<div style="font-size:10px;color:#64748b;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:4px">Domain seit</div>'
                '<div style="font-size:13px;font-weight:600">' + reg + '</div>'
                '</div>'
                '<div style="background:rgba(255,255,255,0.03);border:1px solid #1e1e2e;'
                'border-radius:8px;padding:10px">'
                '<div style="font-size:10px;color:#64748b;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:4px">Registrar</div>'
                '<div style="font-size:12px;font-weight:600">' + registrar[:28] + '</div>'
                '</div>'
                '</div>'
                + grav_block
            )

        email_banner = (
            '<div class="email-banner" style="flex-direction:column;align-items:stretch">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<span class="label">E-Mail</span>'
            '<span class="address">' + SCAN_EMAIL + '</span>'
            + status_part +
            '</div>'
            + meta_rows +
            '</div>'
        )
    else:
        email_banner = ""

    # Results
    if not SCAN_RESULTS:
        results_block = """
        <div class="empty">
          <div class="empty-icon">📡</div>
          <div class="empty-text">Warte auf Scan-Daten…</div>
          <div class="empty-sub">Starte einen Scan um Ergebnisse zu sehen</div>
        </div>"""
    else:
        # Sort: found first, then notfound, then errors
        sorted_results = sorted(SCAN_RESULTS,
            key=lambda r: (0 if r.get("found") else (2 if r.get("error") else 1)))

        cards = []
        for r in sorted_results:
            if r.get("found"):
                cls, badge, badge_text = "found", "found", "GEFUNDEN"
            elif r.get("error"):
                cls, badge, badge_text = "error", "error", "FEHLER"
            else:
                cls, badge, badge_text = "notfound", "notfound", "NICHT GEFUNDEN"

            cat      = r.get("category", "Other")
            username = r.get("username", "")
            meta     = username if username else (r.get("error", "") or cat)

            cards.append(f"""
            <div class="result-card {cls}">
              <div class="result-dot"></div>
              <div class="result-info">
                <div class="result-name">{r['name']}</div>
                <div class="result-meta">{meta}</div>
              </div>
              <span class="result-badge {badge}">{badge_text}</span>
            </div>""")

        results_block = f'<div class="results-grid">{"".join(cards)}</div>'

    html = DASHBOARD_HTML \
        .replace("{{TOTAL}}", str(total)) \
        .replace("{{FOUND}}", str(found)) \
        .replace("{{NOTFOUND}}", str(notfound)) \
        .replace("{{ERRORS}}", str(errors)) \
        .replace("{{UPTIME}}", str(uptime)) \
        .replace("{{EMAIL_BANNER}}", email_banner) \
        .replace("{{RESULTS_BLOCK}}", results_block)

    return html


# ─── Routes ───────────────────────────────────────────────────────────────────

async def handle_dashboard(request: web.Request) -> web.Response:
    return web.Response(
        text=build_dashboard(),
        content_type="text/html",
        charset="utf-8",
    )


async def handle_results_api(request: web.Request) -> web.Response:
    """JSON API so the scanner can push results here."""
    return web.json_response({
        "email":   SCAN_EMAIL,
        "running": SCAN_RUNNING,
        "results": SCAN_RESULTS,
    })


async def handle_push_result(request: web.Request) -> web.Response:
    """Scanner pushes individual results via POST /push."""
    global SCAN_EMAIL, SCAN_RUNNING, SCAN_META
    auth = request.headers.get("X-Proxy-Auth", "")
    if auth != AUTH_TOKEN:
        return web.Response(status=403, text="Forbidden")
    try:
        data = await request.json()
        if "email" in data:
            SCAN_EMAIL = data["email"]
        if "running" in data:
            SCAN_RUNNING = data["running"]
        if "result" in data:
            SCAN_RESULTS.append(data["result"])
        if "meta" in data:
            SCAN_META = data["meta"]
        if "reset" in data and data["reset"]:
            SCAN_RESULTS.clear()
            SCAN_META = {}
        return web.json_response({"ok": True})
    except Exception as e:
        return web.Response(status=400, text=str(e))


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
    return web.json_response({
        "status":         "online",
        "public_url":     PUBLIC_URL,
        "uptime_seconds": uptime,
        "requests":       REQUEST_COUNT,
        "scan_results":   len(SCAN_RESULTS),
    })


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


# ─── ngrok ────────────────────────────────────────────────────────────────────

def install_ngrok() -> bool:
    if subprocess.run(["which", "ngrok"], capture_output=True).returncode == 0:
        return True
    print("  [*] Installiere ngrok …")
    try:
        result = subprocess.run([
            "curl", "-sSL",
            "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz",
            "-o", "/tmp/ngrok.tgz"
        ], capture_output=True)
        subprocess.run(
            ["tar", "-xzf", "/tmp/ngrok.tgz", "-C", "/usr/local/bin/"],
            check=True, capture_output=True
        )
        return True
    except Exception as e:
        print(f"  [!] ngrok Installation fehlgeschlagen: {e}")
        return False


def start_ngrok(token: str, port: int) -> str:
    global PUBLIC_URL

    if not install_ngrok():
        return ""

    # Kill any existing ngrok
    subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
    time.sleep(1)

    subprocess.run(
        ["ngrok", "config", "add-authtoken", token],
        capture_output=True
    )

    subprocess.Popen(
        ["ngrok", "http", str(port), "--log=stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("  [*] Warte auf ngrok-Tunnel …", end="", flush=True)
    for i in range(25):
        time.sleep(1)
        print(".", end="", flush=True)
        try:
            resp = urllib.request.urlopen(
                "http://localhost:4040/api/tunnels", timeout=3
            )
            data    = json.loads(resp.read())
            tunnels = data.get("tunnels", [])
            if tunnels:
                PUBLIC_URL = tunnels[0]["public_url"]
                print(" ✔")
                # Write URL to file so run.sh can read it
                url_file = os.environ.get("PROXY_URL_FILE", "/tmp/emailsint_proxy_url")
                try:
                    with open(url_file, "w") as f:
                        f.write(PUBLIC_URL)
                except Exception:
                    pass
                return PUBLIC_URL
        except Exception:
            continue

    print(" ✗")
    return ""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 55)
    print("  EmailSint — Proxy & Dashboard Server")
    print("═" * 55 + "\n")

    # Token from env (set by run.sh) or ask interactively
    ngrok_token = os.environ.get("NGROK_TOKEN", "").strip()
    if not ngrok_token:
        print("  Gib deinen ngrok Authtoken ein.")
        print("  (Holen unter: https://dashboard.ngrok.com/get-started/your-authtoken)\n")
        ngrok_token = input("  ngrok Authtoken: ").strip()

    if not ngrok_token:
        print("\n  [!] Kein Token eingegeben — Abbruch.")
        sys.exit(1)

    print(f"\n  [*] Starte Server auf Port {PROXY_PORT} …")
    url = start_ngrok(ngrok_token, PROXY_PORT)

    print()
    if url:
        print(f"  ┌─────────────────────────────────────────────────┐")
        print(f"  │  ✔  ngrok-Tunnel aktiv!                         │")
        print(f"  │                                                 │")
        print(f"  │  📊 Dashboard:  {url:<32} │")
        print(f"  │  🔌 Proxy URL:  {url:<32} │")
        print(f"  │  🔑 Auth Token: {AUTH_TOKEN:<32} │")
        print(f"  └─────────────────────────────────────────────────┘")
        print()
        print(f"  Setze in emailsint:")
        print(f"    PROXY_URL={url}")
        print(f"    PROXY_AUTH={AUTH_TOKEN}")
    else:
        print(f"  [!] ngrok fehlgeschlagen — nur lokal erreichbar")
        print(f"  [*] Lokaler Server: http://localhost:{PROXY_PORT}")

    print(f"\n  [*] Drücke Ctrl+C zum Beenden\n")
    print("─" * 55)

    app = web.Application()
    # Dashboard & API routes
    app.router.add_get( "/",         handle_dashboard)
    app.router.add_get( "/dashboard",handle_dashboard)
    app.router.add_get( "/results",  handle_results_api)
    app.router.add_post("/push",     handle_push_result)
    app.router.add_get( "/status",   handle_status)
    app.router.add_get( "/health",   handle_health)
    # Proxy catch-all
    app.router.add_route("*", "/proxy",            handle_proxy)
    app.router.add_route("*", "/{path_info:.*}",   handle_proxy)

    web.run_app(app, host="0.0.0.0", port=PROXY_PORT, print=lambda _: None)


if __name__ == "__main__":
    main()
